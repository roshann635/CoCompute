"""
CoCompute Transparent Demo Mode Cluster Launcher.

Launches multiple isolated local Worker Agents to augment physical lab machines
during demonstrations and stress testing. Transparently labels instances as 'LOCAL'
so operators can clearly distinguish them from physical lab PCs.
"""

import sys
import os
import argparse
import asyncio
import signal
import uuid
import logging
from typing import List

# Ensure parent path is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
for path in (CURRENT_DIR, PARENT_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from worker.app.core_config import parse_master_code

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("DemoCluster")


async def launch_worker_process(
    index: int,
    master_ip: str = None,
    master_port: int = None,
    master_code: str = None
) -> asyncio.subprocess.Process:
    """Spawns an independent headless worker agent process."""
    uid = f"local-worker-{index:02d}-{uuid.uuid4().hex[:6]}"
    hostname = f"LOCAL-AGENT-{index:02d}"

    env = os.environ.copy()
    env["WORKER_UID"] = uid
    env["IS_LOCAL"] = "true"
    env["WORKER_HOSTNAME"] = hostname

    if master_ip:
        env["MASTER_IP"] = str(master_ip)
    if master_port:
        env["MASTER_PORT"] = str(master_port)
    if master_code:
        env["MASTER_CODE"] = str(master_code)

    cmd = [
        sys.executable,
        os.path.join(CURRENT_DIR, "start_worker.py"),
        "--cli",
        "--local",
        "--worker-uid", uid
    ]
    if master_ip:
        cmd.extend(["--master-ip", str(master_ip)])
    if master_port:
        cmd.extend(["--master-port", str(master_port)])
    if master_code:
        cmd.extend(["--code", str(master_code)])

    logger.info(f"Starting Local Worker Agent #{index:02d} ({uid})...")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    return proc


async def stream_output(prefix: str, proc: asyncio.subprocess.Process):
    """Pumps log output from child worker process with prefix."""
    try:
        while not proc.stdout.at_eof():
            line = await proc.stdout.readline()
            if line:
                sys.stdout.write(f"[{prefix}] {line.decode('utf-8', errors='replace')}")
                sys.stdout.flush()
    except Exception:
        pass


async def main():
    parser = argparse.ArgumentParser(description="CoCompute Transparent Demo Mode Cluster Launcher")
    parser.add_argument("--count", "-n", type=int, default=3, help="Number of local workers to spawn (default: 3)")
    parser.add_argument("--master", type=str, help="Master IP:Port or URL (e.g. 127.0.0.1:8000)")
    parser.add_argument("--master-ip", type=str, help="Master IP address")
    parser.add_argument("--master-port", type=int, help="Master port")
    parser.add_argument("--code", type=str, help="Master Connect Code (e.g. CC-4827)")
    args = parser.parse_args()

    target_ip = args.master_ip
    target_port = args.master_port

    if args.master:
        val = args.master.replace("http://", "").replace("https://", "").replace("ws://", "").replace("wss://", "")
        if ":" in val:
            parts = val.split(":")
            target_ip = parts[0]
            target_port = int(parts[1])
        else:
            target_ip = val
            target_port = 8000

    if args.code:
        code_res = parse_master_code(args.code)
        if code_res:
            target_ip, target_port = code_res

    print("============================================================")
    print("           CoCompute Demo Mode Cluster Manager              ")
    print("============================================================")
    print(f"Launching {args.count} local worker agent instances...")
    print("Tag: worker_type = 'LOCAL' (transparently separated on Dashboard)")
    if target_ip and target_port:
        print(f"Target Master: {target_ip}:{target_port}")
    elif args.code:
        print(f"Target Master Code: {args.code}")
    else:
        print("Target Master: Auto-Discovery (UDP 9999 / localhost fallback)")
    print("Press Ctrl+C to terminate all local workers gracefully.")
    print("============================================================\n")

    processes: List[asyncio.subprocess.Process] = []
    tasks = []

    for i in range(1, args.count + 1):
        proc = await launch_worker_process(
            index=i,
            master_ip=target_ip,
            master_port=target_port,
            master_code=args.code
        )
        processes.append(proc)
        tasks.append(asyncio.create_task(stream_output(f"WORKER-{i:02d}", proc)))
        await asyncio.sleep(0.5)

    try:
        # Run until interrupted
        await asyncio.gather(*[proc.wait() for proc in processes])
    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\n[*] Terminating local demo worker cluster...")
    finally:
        for p in processes:
            if p.returncode is None:
                try:
                    p.terminate()
                except Exception:
                    pass
        await asyncio.sleep(1.0)
        for p in processes:
            if p.returncode is None:
                try:
                    p.kill()
                except Exception:
                    pass
        print("[✓] All local demo workers shut down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
