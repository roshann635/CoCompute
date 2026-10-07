"""
Execution Engine.

Runs task payloads in isolated environments:
  1. Docker container (GAP 1) — full sandboxing with resource limits, --network=none, CPU/RAM caps.
  2. Subprocess fallback / SDK Sandbox — used when Docker daemon is not active.
"""

import asyncio
import os
import sys
import tempfile
import logging
import json
import shutil
import hashlib
from typing import Dict, Any

try:
    from shared.sdk.registry import TaskRegistry
except ImportError:
    # Try adding parent directories or fallback
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    try:
        from shared.sdk.registry import TaskRegistry
    except ImportError:
        class TaskRegistryFallback:
            @staticmethod
            def get(task_type: str):
                return None
        TaskRegistry = TaskRegistryFallback()

logger = logging.getLogger(__name__)


def is_docker_available() -> bool:
    """Check if Docker CLI is available and daemon is running."""
    if shutil.which("docker") is None:
        return False
    try:
        import subprocess
        res = subprocess.run(["docker", "info"], capture_output=True, timeout=2)
        return res.returncode == 0
    except Exception:
        return False


async def execute_task(task_payload: dict, chunk_id: int, task_type: str = "generic_python") -> dict:
    """
    Executes a task chunk payload via Task SDK runner or isolated subprocess / container.
    """
    if not task_payload:
        return {"status": "error", "result": None, "error": "Empty task payload"}

    # 1. Check if payload directly targets a registered SDK task
    task_def = TaskRegistry.get(task_type)
    if task_def:
        try:
            loop = asyncio.get_event_loop()
            result_data = await loop.run_in_executor(None, task_def.execute, task_payload)
            valid, err = task_def.validate_partial(result_data)
            if not valid:
                return {"status": "failed", "result": None, "error": f"Partial validation failed: {err}"}
            return {"status": "success", "result": result_data, "error": None}
        except Exception as e:
            logger.warning(f"TaskRegistry execution failed for {task_type}: {e}, trying script fallback...")

    # 2. Check for script-based payload (e.g. from built-in job generators or custom user scripts)
    script = task_payload.get("script")
    args = task_payload.get("args", [])
    if script:
        if is_docker_available():
            return await execute_in_docker(script, args, chunk_id, task_type)
        else:
            return await execute_in_subprocess(script, args, chunk_id)

    # 3. Direct pass-through if no script and no SDK task
    return {"status": "success", "result": task_payload, "error": None}


async def execute_in_docker(script: str, args: list, chunk_id: int, task_type: str = "generic_python") -> dict:
    """Execute a Python script inside an isolated Docker container with strict CPU, RAM, and network isolation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "task.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)

        container_name = f"cocompute_task_{chunk_id}_{os.getpid()}"
        image_name = f"cocompute/task-{task_type}:latest"

        processed_args = []
        for i, a in enumerate(args):
            str_a = str(a)
            if len(str_a) > 2048:
                arg_file_name = f"arg_{i}.json"
                with open(os.path.join(tmpdir, arg_file_name), "w", encoding="utf-8") as f:
                    f.write(str_a)
                processed_args.append(f"/workspace/{arg_file_name}")
            else:
                processed_args.append(str_a)

        cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            "--memory=1024m",
            "--cpus=2.0",
            "--network=none",
            "-v", f"{tmpdir}:/workspace:rw",
            "-w", "/workspace",
            "python:3.11-slim",
            "python", "task.py"
        ] + processed_args

        logger.info(f"[Docker] Executing chunk {chunk_id} in container {container_name}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300.0)

            if process.returncode == 0:
                try:
                    result_data = json.loads(stdout.decode().strip())
                    return {"status": "success", "result": result_data, "error": None}
                except json.JSONDecodeError:
                    return {"status": "success", "result": stdout.decode().strip(), "error": None}
            else:
                return {"status": "failed", "result": None, "error": stderr.decode().strip()}

        except asyncio.TimeoutError:
            kill_proc = await asyncio.create_subprocess_exec("docker", "rm", "-f", container_name)
            await kill_proc.wait()
            return {"status": "timeout", "result": None, "error": "Task execution timed out (300s)."}
        except Exception as e:
            return {"status": "error", "result": None, "error": str(e)}


async def execute_in_subprocess(script: str, args: list, chunk_id: int) -> dict:
    """Fallback: execute a Python script as a subprocess."""
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "task.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)

        processed_args = []
        for i, a in enumerate(args):
            str_a = str(a)
            if len(str_a) > 2048:
                arg_file = os.path.join(tmpdir, f"arg_{i}.json")
                with open(arg_file, "w", encoding="utf-8") as f:
                    f.write(str_a)
                processed_args.append(arg_file)
            else:
                processed_args.append(str_a)

        cmd = [sys.executable, script_path] + processed_args
        logger.info(f"[Subprocess] Executing chunk {chunk_id}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300.0)

            if process.returncode == 0:
                try:
                    result_data = json.loads(stdout.decode().strip())
                    return {"status": "success", "result": result_data, "error": None}
                except json.JSONDecodeError:
                    return {"status": "success", "result": stdout.decode().strip(), "error": None}
            else:
                return {"status": "failed", "result": None, "error": stderr.decode().strip()}

        except asyncio.TimeoutError:
            return {"status": "timeout", "result": None, "error": "Task execution timed out (300s)."}
        except Exception as e:
            return {"status": "error", "result": None, "error": str(e)}
