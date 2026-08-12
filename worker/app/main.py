import asyncio
import logging
import uuid
import os
import httpx
import websockets
import json
import threading
from datetime import datetime, timezone
import argparse
import sys

from .network.discovery import discover_master
from .monitor.metrics import get_hardware_info, get_current_metrics, increment_running_tasks, decrement_running_tasks
from .execution.docker_engine import execute_task
from .history.task_history import save_task_record

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

WORKER_UID = os.getenv("WORKER_UID", str(uuid.uuid4()))
WORKER_API_KEY = os.getenv("WORKER_API_KEY", "cocompute-worker-key")
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "5"))
USE_TLS = os.getenv("USE_TLS", "false").lower() == "true"
TLS_VERIFY = os.getenv("TLS_VERIFY", "false").lower() == "true"

# GUI Signal reference and loop hooks
gui_signals = None
connection_task = None
background_loop = None
async_thread = None


async def register_with_master(master_ip: str, http_port: int) -> bool:
    """Register this worker with the master node via HTTP."""
    scheme = "https" if USE_TLS else "http"
    url = f"{scheme}://{master_ip}:{http_port}/api/v1/workers/register"
    hw_info = get_hardware_info()
    hw_info["worker_uid"] = WORKER_UID
    hw_info["api_key"] = WORKER_API_KEY

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=TLS_VERIFY if USE_TLS else True) as client:
            response = await client.post(url, json=hw_info)
            response.raise_for_status()
            logger.info(f"Successfully registered with Master. Worker UID: {WORKER_UID}")
            return True
    except Exception as e:
        logger.error(f"Failed to register with master: {e}")
        return False


async def heartbeat_loop(websocket):
    """Send periodic heartbeat with system metrics."""
    while True:
        try:
            metrics = get_current_metrics()
            payload = {
                "type": "METRICS",
                "data": metrics
            }
            await websocket.send(json.dumps(payload))
            logger.debug(f"Heartbeat sent. CPU={metrics['cpu_usage']}% RAM={metrics['ram_usage']}% Tasks={metrics['running_tasks']}")
            
            # Update GUI metrics if signals are connected
            if gui_signals:
                gui_signals.metrics_updated.emit(metrics)
                
            await asyncio.sleep(HEARTBEAT_INTERVAL)
        except websockets.exceptions.ConnectionClosed:
            logger.error("WebSocket connection closed. Stopping heartbeats.")
            if gui_signals:
                gui_signals.status_changed.emit("disconnected")
            break
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")
            break


async def task_listener_loop(websocket):
    """Listen for task assignments from the master."""
    while True:
        try:
            message = await websocket.recv()
            data = json.loads(message)
            if data.get("type") == "EXECUTE":
                chunk_id = data.get("chunk_id")
                task_payload = data.get("task_payload")
                logger.info(f"Received task chunk: {chunk_id}")

                # Execute asynchronously
                asyncio.create_task(handle_task_execution(websocket, chunk_id, task_payload))

        except websockets.exceptions.ConnectionClosed:
            if gui_signals:
                gui_signals.status_changed.emit("disconnected")
            break
        except Exception as e:
            logger.error(f"Error receiving WS message: {e}")
            break


async def handle_task_execution(websocket, chunk_id: int, task_payload: dict):
    """Execute a task and submit the result back to master."""
    increment_running_tasks()
    start_time = datetime.now(timezone.utc)
    
    if gui_signals:
        gui_signals.task_started.emit({"chunk_id": chunk_id, "type": task_payload.get("type", "python")})
        gui_signals.status_changed.emit("busy")

    try:
        logger.info(f"Starting execution of chunk {chunk_id}")
        result = await execute_task(task_payload, chunk_id)
        end_time = datetime.now(timezone.utc)
        exec_seconds = (end_time - start_time).total_seconds()

        payload = {
            "type": "RESULT",
            "chunk_id": chunk_id,
            "result_data": result
        }
        await websocket.send(json.dumps(payload))
        logger.info(f"Submitted result for chunk {chunk_id}: {result.get('status')}")

        # Persist to local task history (FR-11)
        save_task_record(
            chunk_id=chunk_id,
            status=result.get("status", "unknown"),
            result=result.get("result"),
            error=result.get("error"),
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            execution_time=exec_seconds,
        )
    except Exception as e:
        end_time = datetime.now(timezone.utc)
        exec_seconds = (end_time - start_time).total_seconds()
        logger.error(f"Error executing chunk {chunk_id}: {e}")
        try:
            await websocket.send(json.dumps({
                "type": "RESULT",
                "chunk_id": chunk_id,
                "result_data": {"status": "error", "result": None, "error": str(e)}
            }))
        except Exception:
            pass
        # Persist failure to local history
        save_task_record(
            chunk_id=chunk_id,
            status="error",
            error=str(e),
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            execution_time=exec_seconds,
        )
    finally:
        decrement_running_tasks()
        if gui_signals:
            gui_signals.task_completed.emit({"chunk_id": chunk_id})
            gui_signals.status_changed.emit("connected")


async def connect_websocket(master_ip: str, ws_port: int):
    """Maintain persistent WebSocket connection with auto-reconnect."""
    ws_scheme = "wss" if USE_TLS else "ws"
    ws_url = f"{ws_scheme}://{master_ip}:{ws_port}/ws/worker/{WORKER_UID}"

    ssl_context = None
    if USE_TLS:
        import ssl as ssl_module
        ssl_context = ssl_module.create_default_context()
        if not TLS_VERIFY:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl_module.CERT_NONE

    while True:
        try:
            logger.info(f"Connecting to Master WebSocket at {ws_url}...")
            if gui_signals:
                gui_signals.status_changed.emit("connecting")

            async with websockets.connect(
                ws_url, ping_interval=20, ping_timeout=10, ssl=ssl_context
            ) as websocket:
                logger.info("WebSocket connected successfully.")
                if gui_signals:
                    gui_signals.status_changed.emit("connected")

                # Run heartbeat and listener concurrently
                await asyncio.gather(
                    heartbeat_loop(websocket),
                    task_listener_loop(websocket)
                )
        except asyncio.CancelledError:
            logger.info("WebSocket connection cancelled by host request.")
            if gui_signals:
                gui_signals.status_changed.emit("disconnected")
            break
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}. Retrying in 5 seconds...")
            if gui_signals:
                gui_signals.status_changed.emit("disconnected")
            await asyncio.sleep(5)


async def agent_main_loop(master_ip: str, master_port: int):
    """Core loops runner for GUI threads."""
    global connection_task
    try:
        if gui_signals:
            gui_signals.status_changed.emit("registering")
        success = await register_with_master(master_ip, master_port)
        if not success:
            logger.error("Registration failed.")
            if gui_signals:
                gui_signals.status_changed.emit("error")
            return

        if gui_signals:
            gui_signals.status_changed.emit("registered")

        connection_task = asyncio.create_task(connect_websocket(master_ip, master_port))
        await connection_task
    except asyncio.CancelledError:
        logger.info("Agent loop cancelled by user.")
    except Exception as e:
        logger.error(f"Error in background loops: {e}")
        if gui_signals:
            gui_signals.status_changed.emit("error")


def start_agent_thread():
    """Start the background loops runner in a thread."""
    global async_thread
    stop_agent_thread()

    def run():
        global background_loop
        background_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(background_loop)

        master_ip = os.getenv("MASTER_IP")
        master_port = os.getenv("MASTER_PORT")

        async def run_discovery():
            nonlocal master_ip, master_port
            if not master_ip or not master_port:
                if gui_signals:
                    gui_signals.status_changed.emit("discovering")
                try:
                    master_info = await discover_master(udp_port=9999)
                    master_ip = master_info['master_ip']
                    master_port = master_info['master_ws_port']
                    if gui_signals:
                        gui_signals.master_info.emit(master_ip, master_port)
                except Exception as e:
                    logger.error(f"Discovery error: {e}")
                    if gui_signals:
                        gui_signals.status_changed.emit("error")
                    return
            
            if master_ip and master_port:
                os.environ["MASTER_IP"] = master_ip
                os.environ["MASTER_PORT"] = str(master_port)
                await agent_main_loop(master_ip, int(master_port))

        background_loop.run_until_complete(run_discovery())

    async_thread = threading.Thread(target=run, daemon=True)
    async_thread.start()


def stop_agent_thread():
    """Cancel connection tasks and stop background threads."""
    global async_thread, background_loop, connection_task
    
    if background_loop:
        if connection_task and not connection_task.done():
            background_loop.call_soon_threadsafe(connection_task.cancel)
        background_loop.call_soon_threadsafe(background_loop.stop)
        
    if async_thread:
        async_thread.join(timeout=2.0)
        async_thread = None
    background_loop = None
    connection_task = None


async def main_cli():
    """CLI mode execution flow."""
    logger.info("=" * 60)
    logger.info(f"  CoCompute CLI Worker Starting... UID={WORKER_UID}")
    logger.info("=" * 60)

    env_master_ip = os.getenv("MASTER_IP")
    env_master_port = os.getenv("MASTER_PORT")

    if env_master_ip and env_master_port:
        master_ip = env_master_ip
        master_port = int(env_master_port)
        logger.info(f"Using Master configured via environment: {master_ip}:{master_port}")
    else:
        logger.info("Master IP/Port not configured in environment. Starting discovery...")
        master_info = await discover_master(udp_port=9999)
        master_ip = master_info['master_ip']
        master_port = master_info['master_ws_port']
        logger.info(f"Discovered Master at {master_ip}:{master_port}")

    success = await register_with_master(master_ip, master_port)
    if not success:
        logger.error("Registration failed. Exiting.")
        return

    await connect_websocket(master_ip, master_port)


def main():
    parser = argparse.ArgumentParser(description="CoCompute Worker Agent")
    parser.add_argument("--headless", action="store_true", help="Run without PySide6 graphical dashboard")
    args, unknown = parser.parse_known_args()

    # Determine if GUI is available and requested
    run_gui = not args.headless
    if run_gui:
        try:
            from PySide6.QtCore import QObject
            from .ui.gui import run_qt_app, WorkerSignals
            global gui_signals
            gui_signals = WorkerSignals()
        except ImportError:
            logger.warning("PySide6 is not installed or GUI not supported. Falling back to CLI mode.")
            run_gui = False

    if run_gui:
        logger.info("Starting PySide6 Worker Dashboard UI...")
        # Start backend threads
        start_agent_thread()
        # Start Qt Application loop in the main thread (blocking)
        run_qt_app(gui_signals, stop_agent_thread, start_agent_thread)
    else:
        # Run standard CLI asyncio loop
        asyncio.run(main_cli())


if __name__ == "__main__":
    main()
