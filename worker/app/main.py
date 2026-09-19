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

try:
    from master.app.services.integrity import compute_sha256
    from master.app.services.auth_service import generate_worker_token
except ImportError:
    import hashlib
    import hmac

    def compute_sha256(data) -> str:
        if isinstance(data, bytes):
            raw_bytes = data
        elif isinstance(data, str):
            raw_bytes = data.encode("utf-8")
        else:
            raw_bytes = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(raw_bytes).hexdigest()

    def generate_worker_token(worker_id: str) -> str:
        secret = os.getenv("COCOMPUTE_WORKER_SECRET", "cocompute-default-cluster-secret-2026")
        return hmac.new(secret.encode("utf-8"), worker_id.encode("utf-8"), hashlib.sha256).hexdigest()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

WORKER_UID = os.getenv("WORKER_UID", str(uuid.uuid4()))
WORKER_API_KEY = os.getenv("WORKER_API_KEY", "cocompute-worker-key")
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "5"))
USE_TLS = os.getenv("USE_TLS", "false").lower() == "true"
TLS_VERIFY = os.getenv("TLS_VERIFY", "false").lower() == "true"

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
    token = generate_worker_token(WORKER_UID)
    hw_info["token"] = token

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
    """Send periodic heartbeat with system & GPU metrics."""
    while True:
        try:
            metrics = get_current_metrics()
            payload = {
                "type": "METRICS",
                "data": metrics
            }
            await websocket.send(json.dumps(payload))
            logger.debug(f"Heartbeat sent. CPU={metrics.get('cpu_usage')}% RAM={metrics.get('ram_usage')}% Tasks={metrics.get('running_tasks')}")

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
                chunk_uid = data.get("chunk_uid", f"CHUNK-{chunk_id}")
                attempt_id = data.get("attempt_id")
                task_type = data.get("task_type", "generic_python")
                task_payload = data.get("task_payload")
                logger.info(f"Received task chunk: {chunk_id} ({chunk_uid}, attempt={attempt_id})")

                asyncio.create_task(
                    handle_task_execution(
                        websocket, chunk_id, task_payload, chunk_uid, attempt_id, task_type
                    )
                )

        except websockets.exceptions.ConnectionClosed:
            if gui_signals:
                gui_signals.status_changed.emit("disconnected")
            break
        except Exception as e:
            logger.error(f"Error receiving WS message: {e}")
            break


async def handle_task_execution(
    websocket,
    chunk_id: int,
    task_payload: dict,
    chunk_uid: str = None,
    attempt_id: str = None,
    task_type: str = "generic_python"
):
    """Execute a task and submit the result back to master with checksum."""
    increment_running_tasks()
    start_time = datetime.now(timezone.utc)

    if gui_signals:
        gui_signals.task_started.emit({
            "chunk_id": chunk_id,
            "chunk_uid": chunk_uid or f"CHUNK-{chunk_id}",
            "type": task_type
        })
        gui_signals.status_changed.emit("busy")

    try:
        logger.info(f"Starting execution of chunk {chunk_id} ({chunk_uid})")
        result = await execute_task(task_payload, chunk_id, task_type=task_type)
        end_time = datetime.now(timezone.utc)
        exec_seconds = (end_time - start_time).total_seconds()

        # Compute SHA-256 Checksum (GAP 6)
        raw_res = result.get("result")
        checksum = compute_sha256(raw_res)

        payload = {
            "type": "RESULT",
            "chunk_id": chunk_id,
            "attempt_id": attempt_id,
            "worker_uid": WORKER_UID,
            "result_data": result,
            "checksum": checksum
        }
        await websocket.send(json.dumps(payload))
        logger.info(f"Submitted result for chunk {chunk_id}: {result.get('status')} (checksum: {checksum})")

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

        if gui_signals:
            gui_signals.task_completed.emit({
                "chunk_id": chunk_id,
                "status": result.get("status", "unknown"),
                "execution_time_seconds": exec_seconds
            })
            gui_signals.status_changed.emit("connected")

    except Exception as e:
        logger.error(f"Execution error on chunk {chunk_id}: {e}")
        end_time = datetime.now(timezone.utc)
        exec_seconds = (end_time - start_time).total_seconds()

        err_result = {"status": "error", "result": None, "error": str(e)}
        checksum = compute_sha256(err_result)
        payload = {
            "type": "RESULT",
            "chunk_id": chunk_id,
            "attempt_id": attempt_id,
            "worker_uid": WORKER_UID,
            "result_data": err_result,
            "checksum": checksum
        }
        try:
            await websocket.send(json.dumps(payload))
        except Exception:
            pass

        save_task_record(
            chunk_id=chunk_id,
            status="error",
            result=None,
            error=str(e),
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            execution_time=exec_seconds,
        )

        if gui_signals:
            gui_signals.task_completed.emit({
                "chunk_id": chunk_id,
                "status": "error",
                "execution_time_seconds": exec_seconds
            })
            gui_signals.status_changed.emit("connected")
    finally:
        decrement_running_tasks()


async def run_worker():
    """Main worker lifecycle: discover master, register, connect WebSocket."""
    master_ip = os.getenv("MASTER_IP")
    master_port = os.getenv("MASTER_PORT")

    if not master_ip or not master_port:
        if gui_signals:
            gui_signals.status_changed.emit("discovering")
        logger.info("Discovering master node via UDP...")
        try:
            master_ip, master_port = await discover_master(timeout=10.0)
            logger.info(f"Discovered master at {master_ip}:{master_port}")
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            if gui_signals:
                gui_signals.status_changed.emit("disconnected")
            return
    else:
        master_port = int(master_port)

    if gui_signals:
        gui_signals.master_info.emit(master_ip, master_port)
        gui_signals.status_changed.emit("registering")

    # Register via HTTP
    registered = await register_with_master(master_ip, master_port)
    if not registered:
        if gui_signals:
            gui_signals.status_changed.emit("disconnected")
        return

    # WebSocket with HMAC Token Auth (GAP 7)
    ws_scheme = "wss" if USE_TLS else "ws"
    token = generate_worker_token(WORKER_UID)
    ws_url = f"{ws_scheme}://{master_ip}:{master_port}/ws/worker/{WORKER_UID}?token={token}"

    logger.info(f"Connecting to Master WebSocket at {ws_url}...")

    retry_delay = 3
    while True:
        try:
            if gui_signals:
                gui_signals.status_changed.emit("connecting")

            async with websockets.connect(ws_url) as websocket:
                logger.info("Connected to Master Node via WebSocket.")
                if gui_signals:
                    gui_signals.status_changed.emit("connected")

                heartbeat_task = asyncio.create_task(heartbeat_loop(websocket))
                listener_task = asyncio.create_task(task_listener_loop(websocket))

                done, pending = await asyncio.wait(
                    [heartbeat_task, listener_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                for t in pending:
                    t.cancel()

        except asyncio.CancelledError:
            logger.info("Worker stopped by user.")
            if gui_signals:
                gui_signals.status_changed.emit("disconnected")
            break
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}. Retrying in {retry_delay}s...")
            if gui_signals:
                gui_signals.status_changed.emit("disconnected")
            await asyncio.sleep(retry_delay)


def start_worker_thread():
    global background_loop, connection_task, async_thread
    background_loop = asyncio.new_event_loop()

    def run_loop():
        asyncio.set_event_loop(background_loop)
        background_loop.run_until_complete(run_worker())

    async_thread = threading.Thread(target=run_loop, daemon=True)
    async_thread.start()


def stop_worker():
    global background_loop
    if background_loop and background_loop.is_running():
        background_loop.call_soon_threadsafe(background_loop.stop)


def main():
    parser = argparse.ArgumentParser(description="CoCompute Worker Node")
    parser.add_argument("--gui", action="store_true", help="Launch Worker with PySide6 GUI")
    parser.add_argument("--master-ip", type=str, help="Master node IP address")
    parser.add_argument("--master-port", type=int, help="Master node port")
    args = parser.parse_args()

    if args.master_ip:
        os.environ["MASTER_IP"] = args.master_ip
    if args.master_port:
        os.environ["MASTER_PORT"] = str(args.master_port)

    if args.gui:
        global gui_signals
        from .ui.gui import WorkerSignals, run_qt_app
        gui_signals = WorkerSignals()
        start_worker_thread()
        run_qt_app(gui_signals, stop_cb=stop_worker, start_cb=start_worker_thread)
    else:
        asyncio.run(run_worker())


if __name__ == "__main__":
    main()
