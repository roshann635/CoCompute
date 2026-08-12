import asyncio
import argparse
import random
import uuid
import sys
import os
import json
import httpx
import websockets
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from master.app.db.database import Base, SQLALCHEMY_DATABASE_URL
from master.app.db import models

NODE_PRESETS = [
    {"hostname": "node-alpha-1", "platform": "Linux-5.15-x86_64", "cpu_cores": 16, "ram_total": 64.0, "disk_total": 512.0, "cpu_model": "AMD EPYC 7763 64-Core Processor"},
    {"hostname": "node-beta-2", "platform": "Linux-6.2-x86_64", "cpu_cores": 8, "ram_total": 32.0, "disk_total": 256.0, "cpu_model": "Intel(R) Xeon(R) Platinum 8375C CPU @ 2.90GHz"},
    {"hostname": "node-gpu-rig", "platform": "Linux-5.15-x86_64", "cpu_cores": 32, "ram_total": 128.0, "disk_total": 1024.0, "cpu_model": "AMD Ryzen Threadripper PRO 5995WX"},
    {"hostname": "worker-mac-m2", "platform": "macOS-14.2-arm64", "cpu_cores": 8, "ram_total": 16.0, "disk_total": 512.0, "cpu_model": "Apple M2 Pro"},
    {"hostname": "worker-win-desktop", "platform": "Windows-11-AMD64", "cpu_cores": 12, "ram_total": 32.0, "disk_total": 1000.0, "cpu_model": "13th Gen Intel(R) Core(TM) i7-13700K"},
    {"hostname": "edge-pi-node", "platform": "Linux-6.1-aarch64", "cpu_cores": 4, "ram_total": 8.0, "disk_total": 128.0, "cpu_model": "ARM Cortex-A72 @ 1.5GHz"},
]


def populate_db_nodes(count: int, db_url: str):
    """Seed or update N simulated nodes directly into the SQLite database."""
    print(f"Populating DB at {db_url} with {count} simulated worker nodes...")
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    created_nodes = []
    for i in range(count):
        preset = NODE_PRESETS[i % len(NODE_PRESETS)]
        uid = f"worker-sim-{i+1:02d}-{uuid.uuid4().hex[:6]}"
        ip = f"192.168.1.{10 + i}"
        
        status = random.choice(["online", "online", "online", "busy", "offline"])
        cpu_util = round(random.uniform(5.0, 95.0), 1) if status != "offline" else 0.0
        ram_usage = round(random.uniform(10.0, 85.0), 1) if status != "offline" else 0.0
        disk_usage = round(random.uniform(20.0, 60.0), 1)
        reliability = round(random.uniform(0.85, 1.0), 2)
        tasks_completed = random.randint(10, 250)
        tasks_failed = random.randint(0, 5)

        worker = models.Worker(
            worker_uid=uid,
            ip_address=ip,
            hostname=f"{preset['hostname']}-{i+1}",
            cpu_cores=preset['cpu_cores'],
            ram_total=preset['ram_total'],
            disk_total=preset['disk_total'],
            platform=preset['platform'],
            cpu_model=preset['cpu_model'],
            cpu_frequency=3200.0,
            mac_address=f"02:00:00:%02x:%02x:%02x" % (random.randint(0,255), random.randint(0,255), random.randint(0,255)),
            agent_version="1.0.0",
            python_version="3.12.0",
            status=status,
            cpu_utilization=cpu_util,
            ram_usage=ram_usage,
            disk_usage=disk_usage,
            network_speed=round(random.uniform(100.0, 1000.0), 1),
            reliability_score=reliability,
            total_tasks_completed=tasks_completed,
            total_tasks_failed=tasks_failed,
            running_tasks=1 if status == "busy" else 0,
            last_seen=datetime.now(timezone.utc)
        )
        db.add(worker)
        created_nodes.append(worker)

    db.commit()
    print(f"[SUCCESS] Created {len(created_nodes)} simulated nodes in DB!")
    for w in created_nodes:
        print(f"  - [{w.status.upper():7s}] {w.worker_uid} ({w.hostname}) | Cores: {w.cpu_cores} | RAM: {w.ram_total}GB | Reliability: {w.reliability_score}")
    db.close()


async def simulate_live_worker(node_id: int, master_url: str, ws_url: str):
    """Simulate a single live worker connected via WebSocket."""
    preset = NODE_PRESETS[(node_id - 1) % len(NODE_PRESETS)]
    uid = f"worker-live-{node_id:02d}-{uuid.uuid4().hex[:6]}"
    
    register_payload = {
        "worker_uid": uid,
        "ip_address": f"127.0.0.{10 + node_id}",
        "hostname": f"{preset['hostname']}-live",
        "cpu_cores": preset['cpu_cores'],
        "ram_total": preset['ram_total'],
        "disk_total": preset['disk_total'],
        "platform": preset['platform'],
        "cpu_model": preset['cpu_model'],
        "cpu_frequency": 3000.0,
        "api_key": "cocompute-worker-key"
    }

    print(f"[{uid}] Registering worker with Master at {master_url}...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{master_url}/api/v1/workers/register", json=register_payload)
            resp.raise_for_status()
    except Exception as e:
        print(f"[{uid}] Registration failed: {e}")
        return

    full_ws_url = f"{ws_url}/ws/worker/{uid}"
    print(f"[{uid}] Connecting WebSocket to {full_ws_url}...")

    try:
        async with websockets.connect(full_ws_url) as ws:
            print(f"[{uid}] ✅ Connected and active!")
            while True:
                cpu = round(random.uniform(10.0, 90.0), 1)
                ram = round(random.uniform(20.0, 80.0), 1)
                metrics = {
                    "type": "METRICS",
                    "data": {
                        "cpu_usage": cpu,
                        "ram_usage": ram,
                        "disk_usage": round(random.uniform(30.0, 60.0), 1),
                        "network_speed": round(random.uniform(500.0, 1000.0), 1),
                        "running_tasks": random.choice([0, 0, 1]),
                        "temperature": round(random.uniform(40.0, 65.0), 1)
                    }
                }
                await ws.send(json.dumps(metrics))
                await asyncio.sleep(5)
    except asyncio.CancelledError:
        print(f"[{uid}] Stopped.")
    except Exception as e:
        print(f"[{uid}] Error: {e}")


async def run_live_simulation(count: int, master_http: str, master_ws: str):
    print(f"🚀 Starting {count} live simulated workers connecting to Master...")
    tasks = [simulate_live_worker(i + 1, master_http, master_ws) for i in range(count)]
    await asyncio.gather(*tasks)


def main():
    parser = argparse.ArgumentParser(description="CoCompute Node Simulator")
    parser.add_argument("--count", type=int, default=5, help="Number of nodes to simulate")
    parser.add_argument("--live", action="store_true", help="Connect live via WebSocket to running Master API")
    parser.add_argument("--master-http", type=str, default="http://127.0.0.1:8000", help="Master HTTP URL")
    parser.add_argument("--master-ws", type=str, default="ws://127.0.0.1:8000", help="Master WebSocket URL")
    parser.add_argument("--db-url", type=str, default=None, help="Database URL for direct DB seeding")
    args = parser.parse_args()

    db_url = args.db_url or os.getenv("DATABASE_URL", "sqlite:///d:/CoCompute/cocompute.db")

    if args.live:
        try:
            asyncio.run(run_live_simulation(args.count, args.master_http, args.master_ws))
        except KeyboardInterrupt:
            print("\nStopped live simulation.")
    else:
        populate_db_nodes(args.count, db_url)


if __name__ == "__main__":
    main()
