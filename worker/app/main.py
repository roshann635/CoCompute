import asyncio
import logging
import uuid
import os
try:
    import httpx
except ImportError:
    httpx = None
import urllib.request
import urllib.error
import websockets
import json
import threading
from datetime import datetime, timezone
import argparse
import sys

from .network.discovery import discover_master
from .monitor.metrics import get_hardware_info, get_current_metrics, increment_running_tasks, decrement_running_tasks
from .monitor.capabilities import detect_worker_capabilities, AGENT_VERSION, PROTOCOL_VERSION
from .core_config import load_config, save_config, parse_master_code, get_log_path
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
IS_LOCAL = os.getenv("IS_LOCAL", "false").lower() == "true"

gui_signals = None
connection_task = None
background_loop = None
async_thread = None


async def register_with_master(master_ip: str, http_port: int) -> bool:
    """Register this worker with the master node via HTTP."""
    scheme = "https" if USE_TLS else "http"
    url = f"{scheme}://{master_ip}:{http_port}/api/v1/workers/register"
    hw_info = get_hardware_info()
    caps = detect_worker_capabilities(WORKER_UID, is_local=IS_LOCAL)

    hw_info["worker_uid"] = WORKER_UID
    hw_info["api_key"] = WORKER_API_KEY
    token = generate_worker_token(WORKER_UID)
    hw_info["token"] = token
    hw_info["worker_type"] = caps["worker_type"]
    hw_info["agent_version"] = caps["agent_version"]
    hw_info["protocol_version"] = caps["protocol_version"]
    hw_info["docker"] = caps["docker"]
    hw_info["supported_task_versions"] = caps["supported_task_versions"]
    hw_info["capabilities"] = caps

    if httpx:
        try:
            async with httpx.AsyncClient(timeout=10.0, verify=TLS_VERIFY if USE_TLS else True) as client:
                response = await client.post(url, json=hw_info)
                response.raise_for_status()
                logger.info(f"Successfully registered with Master ({caps['worker_type']}). Worker UID: {WORKER_UID}")
                return True
        except Exception as e:
            logger.error(f"Failed to register with master: {e}")
            return False
    else:
        try:
            data = json.dumps(hw_info).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=10.0))
            logger.info(f"Successfully registered with Master (via urllib). Worker UID: {WORKER_UID}")
            return True
        except Exception as e:
            logger.error(f"Failed to register with master: {e}")
            return False



async def heartbeat_loop(websocket):
    """Send periodic heartbeat with system & GPU metrics and capability state."""
    while True:
        try:
            metrics = get_current_metrics()
            caps = detect_worker_capabilities(WORKER_UID, is_local=IS_LOCAL)
            lifecycle = "healthy" if (caps["gpu"] and caps["docker"]) else "degraded"
            payload = {
                "type": "METRICS",
                "data": metrics,
                "capabilities": caps,
                "lifecycle_state": lifecycle
            }
            await websocket.send(json.dumps(payload))
            logger.debug(f"Heartbeat sent. CPU={metrics.get('cpu_usage')}% RAM={metrics.get('ram_usage')}% Tasks={metrics.get('running_tasks')} Lifecycle={lifecycle}")

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
            msg_action = data.get("action") or data.get("type")
            if msg_action == "EXECUTE":
                chunk_id = data.get("chunk_id")
                chunk_uid = data.get("chunk_uid", f"CHUNK-{chunk_id}")
                attempt_id = data.get("attempt_id")
                task_type = data.get("task_type", "generic_python")
                task_payload = data.get("payload") if "payload" in data else data.get("task_payload", {})
                logger.info(f"Received task chunk: {chunk_id} ({chunk_uid}, attempt={attempt_id}, type={task_type})")

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


def load_worker_config() -> dict:
    """Load cached master configuration from platform standard user directory."""
    return load_config()


def save_worker_config(master_ip: str, master_port: int, master_code: str = None):
    """Save working master IP, port, and code to platform standard user directory."""
    data = {"master_ip": master_ip, "master_port": int(master_port)}
    if master_code:
        data["master_code"] = master_code
    save_config(data)


async def probe_master_endpoint(ip: str, port: int) -> bool:
    """Check if Master API is actively responding on HTTP(S)."""
    scheme = "https" if USE_TLS else "http"
    url = f"{scheme}://{ip}:{port}/"
    if httpx:
        try:
            async with httpx.AsyncClient(timeout=2.0, verify=TLS_VERIFY if USE_TLS else True) as client:
                resp = await client.get(url)
                if resp.status_code in (200, 404):
                    return True
        except Exception:
            pass
    else:
        try:
            req = urllib.request.Request(url, method="HEAD")
            loop = asyncio.get_running_loop()
            def _probe():
                try:
                    with urllib.request.urlopen(req, timeout=2.0):
                        return True
                except urllib.error.HTTPError as e:
                    return e.code in (200, 404, 405)
                except Exception:
                    return False
            return await loop.run_in_executor(None, _probe)
        except Exception:
            pass
    return False


async def run_worker():
    """Main worker lifecycle: discover master, register, connect WebSocket."""
    retry_delay = 5

    while True:
        master_ip = os.getenv("MASTER_IP")
        master_port = os.getenv("MASTER_PORT")
        discovered_code = os.getenv("MASTER_CODE")

        # 1. Resolve Master Code if supplied in env
        if not master_ip and discovered_code:
            code_res = parse_master_code(discovered_code)
            if code_res and await probe_master_endpoint(code_res[0], code_res[1]):
                master_ip, master_port = code_res[0], code_res[1]
                logger.info(f"Connected to Master via Master Code {discovered_code} ({master_ip}:{master_port})")

        # 2. Check saved config if not in environment
        if not master_ip or not master_port:
            saved_cfg = load_worker_config()
            candidate_ip = saved_cfg.get("master_ip")
            candidate_port = saved_cfg.get("master_port", 8000)
            if candidate_ip and await probe_master_endpoint(candidate_ip, candidate_port):
                master_ip = candidate_ip
                master_port = candidate_port
                discovered_code = saved_cfg.get("master_code")
                logger.info(f"Connected to Master via cached config ({master_ip}:{master_port})")

        # 3. Try UDP auto-discovery if still not resolved
        if not master_ip or not master_port:
            if gui_signals:
                gui_signals.status_changed.emit("discovering")
            logger.info("Discovering master node via UDP...")
            try:
                disc = await discover_master(timeout=5.0)
                master_ip, master_port = disc[0], disc[1]
                discovered_code = getattr(disc, "code", None)
                logger.info(f"Discovered master at {master_ip}:{master_port} (Code: {discovered_code or 'N/A'})")
            except Exception:
                # 4. Fallback: probe localhost / 127.0.0.1
                if await probe_master_endpoint("127.0.0.1", 8000):
                    master_ip, master_port = "127.0.0.1", 8000
                    logger.info(f"Discovered local Master on 127.0.0.1:8000")
                elif await probe_master_endpoint("localhost", 8000):
                    master_ip, master_port = "localhost", 8000
                    logger.info(f"Discovered local Master on localhost:8000")

        # 5. If still not resolved, log helpful guide and retry gracefully
        if not master_ip or not master_port:
            logger.warning(
                f"[Auto-Discovery] Master node not found on local network (UDP broadcast might be restricted).\n"
                f"                 Retrying discovery in {retry_delay}s...\n"
                f"                 Tip: Specify master directly: python start_worker.py --master-ip <IP> --master-port 8000\n"
                f"                 Or run diagnostics:          python start_worker.py --doctor"
            )
            if gui_signals:
                gui_signals.status_changed.emit("disconnected")
            await asyncio.sleep(retry_delay)
            continue

        master_port = int(master_port)
        if gui_signals:
            gui_signals.master_info.emit(master_ip, master_port)
            gui_signals.status_changed.emit("registering")

        # 6. Register with Master via HTTP
        registered = False
        while not registered:
            registered = await register_with_master(master_ip, master_port)
            if not registered:
                logger.warning(f"Registration with Master ({master_ip}:{master_port}) failed. Retrying in {retry_delay}s...")
                if gui_signals:
                    gui_signals.status_changed.emit("disconnected")
                await asyncio.sleep(retry_delay)
                # If master_ip was altered in env or GUI while waiting, break to rediscover
                if os.getenv("MASTER_IP") and os.getenv("MASTER_IP") != master_ip:
                    break
            else:
                save_worker_config(master_ip, master_port, master_code=discovered_code)

        if not registered:
            continue

        # 7. WebSocket Connection with HMAC Token Auth (GAP 7)
        ws_scheme = "wss" if USE_TLS else "ws"
        token = generate_worker_token(WORKER_UID)
        ws_url = f"{ws_scheme}://{master_ip}:{master_port}/ws/worker/{WORKER_UID}?token={token}"

        logger.info(f"Connecting to Master WebSocket at {ws_url}...")

        while True:
            try:
                if gui_signals:
                    gui_signals.status_changed.emit("connecting")

                async with websockets.connect(ws_url) as websocket:
                    logger.info(f"Connected to Master Node ({master_ip}:{master_port}) via WebSocket.")
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
                return
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}. Retrying in {retry_delay}s...")
                if gui_signals:
                    gui_signals.status_changed.emit("disconnected")
                await asyncio.sleep(retry_delay)
                # Re-check registration on reconnect
                break


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


def parse_master_url(master_val: str) -> tuple[str, int]:
    """Parse various master formats: ws://192.168.1.1:8000, http://192.168.1.1:8000, 192.168.1.1:8000, 192.168.1.1"""
    clean = master_val.strip()
    for prefix in ("ws://", "wss://", "http://", "https://"):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
    if "/" in clean:
        clean = clean.split("/")[0]
    if ":" in clean:
        parts = clean.split(":")
        return parts[0], int(parts[1])
    return clean, 8000


def main():
    parser = argparse.ArgumentParser(description="CoCompute Worker Node")
    parser.add_argument("--gui", action="store_true", help="Launch Worker with PySide6 GUI")
    parser.add_argument("--cli", "--headless", action="store_true", help="Launch Worker in Headless CLI mode")
    parser.add_argument("--master", type=str, help="Master URL or host:port (e.g. 192.168.1.100:8000)")
    parser.add_argument("--master-ip", "--master_ip", type=str, help="Master node IP address")
    parser.add_argument("--master-port", "--master_port", type=int, help="Master node port")
    parser.add_argument("--code", "--master-code", type=str, help="Master Connect Code (e.g. CC-4827)")
    parser.add_argument("--worker-uid", "--worker_uid", type=str, help="Custom Worker UID")
    parser.add_argument("--api-key", "--worker-api-key", type=str, help="Worker API Key")
    parser.add_argument("--doctor", action="store_true", help="Run system diagnostics and connectivity checks")
    parser.add_argument("--local", action="store_true", help="Mark this worker as a LOCAL demo agent")
    parser.add_argument("--version", action="store_true", help="Print worker and protocol version")
    args, _ = parser.parse_known_args()

    if args.version:
        print(f"CoCompute Worker Agent v{AGENT_VERSION} (Protocol v{PROTOCOL_VERSION})")
        sys.exit(0)

    # Configure platform-safe persistent file logging
    try:
        log_file = get_log_path()
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
        logging.getLogger().addHandler(file_handler)
    except Exception:
        pass

    if args.doctor:
        from .diagnostics.doctor import run_diagnostics, format_doctor_report
        cand_ip = args.master_ip
        cand_port = args.master_port
        if args.master:
            cand_ip, cand_port = parse_master_url(args.master)
        diag = asyncio.run(run_diagnostics(master_ip=cand_ip, master_port=cand_port, master_code=args.code))
        print(format_doctor_report(diag))
        sys.exit(0 if diag["status"] in ("READY", "DEGRADED") else 1)

    global WORKER_UID, WORKER_API_KEY, IS_LOCAL
    if args.local:
        IS_LOCAL = True
        os.environ["IS_LOCAL"] = "true"

    if args.worker_uid:
        WORKER_UID = args.worker_uid
        os.environ["WORKER_UID"] = args.worker_uid
    if args.api_key:
        WORKER_API_KEY = args.api_key
        os.environ["WORKER_API_KEY"] = args.api_key

    if args.code:
        os.environ["MASTER_CODE"] = args.code
        code_res = parse_master_code(args.code)
        if code_res:
            os.environ["MASTER_IP"] = code_res[0]
            os.environ["MASTER_PORT"] = str(code_res[1])

    if args.master:
        ip, port = parse_master_url(args.master)
        os.environ["MASTER_IP"] = ip
        os.environ["MASTER_PORT"] = str(port)
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

