"""
Execution Engine.

Runs task payloads in isolated environments:
  1. Docker container (preferred) — full sandboxing with resource limits
  2. Subprocess fallback — used when Docker is unavailable

Security measures:
  - Docker: --network=none, --memory=512m, --cpus=1.0, read-only workspace
  - Subprocess: 120s timeout, captured stdout/stderr
"""
import asyncio
import os
import sys
import tempfile
import logging
import json
import shutil

logger = logging.getLogger(__name__)


def is_docker_available() -> bool:
    """Check if Docker CLI is available."""
    return shutil.which("docker") is not None


async def execute_in_docker(script: str, args: list, chunk_id: int) -> dict:
    """Execute a Python script inside an isolated Docker container."""
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "task.py")
        with open(script_path, "w") as f:
            f.write(script)

        container_name = f"cocompute_task_{chunk_id}"
        cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            "--memory=512m",
            "--cpus=1.0",
            "--network=none",
            "-v", f"{tmpdir}:/workspace:ro",
            "-w", "/workspace",
            "python:3.10-alpine",
            "python", "task.py"
        ] + args

        logger.info(f"[Docker] Executing chunk {chunk_id}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120.0)

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
            return {"status": "timeout", "result": None, "error": "Task execution timed out (120s)."}
        except Exception as e:
            return {"status": "error", "result": None, "error": str(e)}


async def execute_in_subprocess(script: str, args: list, chunk_id: int) -> dict:
    """Fallback: execute a Python script as a subprocess (no Docker)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "task.py")
        with open(script_path, "w") as f:
            f.write(script)

        cmd = [sys.executable, script_path] + args

        logger.info(f"[Subprocess] Executing chunk {chunk_id}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120.0)

            if process.returncode == 0:
                try:
                    result_data = json.loads(stdout.decode().strip())
                    return {"status": "success", "result": result_data, "error": None}
                except json.JSONDecodeError:
                    return {"status": "success", "result": stdout.decode().strip(), "error": None}
            else:
                return {"status": "failed", "result": None, "error": stderr.decode().strip()}

        except asyncio.TimeoutError:
            process.kill()
            return {"status": "timeout", "result": None, "error": "Task execution timed out (120s)."}
        except Exception as e:
            return {"status": "error", "result": None, "error": str(e)}


async def execute_task(task_payload: dict, chunk_id: int) -> dict:
    """
    Execute a task payload. Tries Docker first, falls back to subprocess.
    """
    script = task_payload.get("script", "")
    args = task_payload.get("args", [])

    if not script:
        return {"status": "error", "result": None, "error": "Empty script payload"}

    if is_docker_available():
        return await execute_in_docker(script, args, chunk_id)
    else:
        logger.warning(f"Docker not available. Using subprocess fallback for chunk {chunk_id}.")
        return await execute_in_subprocess(script, args, chunk_id)
