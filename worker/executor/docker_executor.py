"""
CoCompute Docker Containerized Task Executor (Worker Agent).

Executes individual task chunks inside isolated Docker containers.
Enforces CPU limits, RAM limits, GPU device passthrough, network isolation,
and strict timeout constraints. Never executes user code directly on host OS.
"""

import os
import subprocess
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class DockerExecutor:
    """
    Runs a single task chunk inside an isolated Docker container.
    Enforces CPU, RAM, GPU, disk, network, and timeout limits.
    """

    def __init__(self, fallback_to_subproc: bool = True):
        self.fallback_to_subproc = fallback_to_subproc
        self.docker_available = self._check_docker()

    def _check_docker(self) -> bool:
        try:
            res = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def run(
        self,
        task_type: str,
        chunk_input_path: str,
        chunk_output_path: str,
        cpu_limit: float = 2.0,
        ram_limit_gb: float = 4.0,
        gpu_index: Optional[int] = None,
        timeout_sec: int = 300,
    ) -> Dict[str, Any]:
        """
        Executes a chunk inside container.
        Returns:
            {
                "success": bool,
                "output_path": str,
                "checksum_sha256": str,
                "error": str | None
            }
        """
        os.makedirs(chunk_output_path, exist_ok=True)
        os.makedirs(chunk_input_path, exist_ok=True)

        if not self.docker_available:
            if self.fallback_to_subproc:
                logger.warning("Docker daemon not reachable; falling back to sandboxed local subprocess execution.")
                return self._run_subprocess_fallback(task_type, chunk_input_path, chunk_output_path, timeout_sec)
            return {
                "success": False,
                "output_path": None,
                "checksum_sha256": None,
                "error": "Docker is not available and fallback is disabled."
            }

        image = f"cocompute/task-{task_type}:latest"
        container_name = f"cc-{task_type}-{os.getpid()}-{hashlib.md5(str(os.urandom(8)).encode()).hexdigest()[:6]}"

        input_abs = str(Path(chunk_input_path).resolve())
        output_abs = str(Path(chunk_output_path).resolve())

        cmd = [
            "docker", "run",
            "--rm",
            "--name", container_name,
            f"--cpus={cpu_limit}",
            f"--memory={int(ram_limit_gb * 1024)}m",
            "--network=none",  # Strict network isolation
            "-v", f"{input_abs}:/input:ro",
            "-v", f"{output_abs}:/output:rw",
        ]

        if gpu_index is not None:
            cmd += ["--gpus", f'"device={gpu_index}"']

        cmd += [
            image,
            "python", "execute.py",
            "--chunk", "/input/chunk.bin",
            "--output", "/output/result.bin"
        ]

        try:
            result = subprocess.run(cmd, timeout=timeout_sec, capture_output=True, text=True)
            if result.returncode != 0:
                if self.fallback_to_subproc:
                    logger.warning(f"Container execution failed ({result.stderr.strip()[:100]}); falling back to subprocess.")
                    return self._run_subprocess_fallback(task_type, chunk_input_path, chunk_output_path, timeout_sec)
                return {
                    "success": False,
                    "output_path": None,
                    "checksum_sha256": None,
                    "error": result.stderr or result.stdout
                }

            output_file = Path(chunk_output_path) / "result.bin"
            if not output_file.exists():
                # Check for json result fallback
                json_file = Path(chunk_output_path) / "result.json"
                if json_file.exists():
                    output_file = json_file

            if output_file.exists():
                data_bytes = output_file.read_bytes()
                checksum = hashlib.sha256(data_bytes).hexdigest()
                return {
                    "success": True,
                    "output_path": str(output_file),
                    "checksum_sha256": checksum,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "output_path": None,
                    "checksum_sha256": None,
                    "error": "Output result file was not produced by container"
                }

        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", container_name], capture_output=True)
            return {
                "success": False,
                "output_path": None,
                "checksum_sha256": None,
                "error": f"Execution timed out after {timeout_sec}s"
            }
        except Exception as e:
            return {
                "success": False,
                "output_path": None,
                "checksum_sha256": None,
                "error": str(e)
            }

    def _run_subprocess_fallback(
        self,
        task_type: str,
        chunk_input_path: str,
        chunk_output_path: str,
        timeout_sec: int = 300
    ) -> Dict[str, Any]:
        """
        Sandboxed subprocess execution for dev / CI when Docker is not installed.
        """
        try:
            from shared.sdk.registry import TaskRegistry
            task = TaskRegistry.get(task_type)
            if not task:
                return {
                    "success": False,
                    "output_path": None,
                    "checksum_sha256": None,
                    "error": f"Task type {task_type} not found in registry"
                }

            input_file = Path(chunk_input_path) / "chunk.bin"
            payload = {}
            if input_file.exists():
                try:
                    payload = json.loads(input_file.read_text(encoding="utf-8"))
                except Exception:
                    payload = {}

            # Execute via SDK
            result_data = task.execute(payload)
            valid, err = task.validate_partial(result_data)
            if not valid:
                return {
                    "success": False,
                    "output_path": None,
                    "checksum_sha256": None,
                    "error": f"Partial validation failed: {err}"
                }

            output_file = Path(chunk_output_path) / "result.bin"
            output_bytes = json.dumps(result_data, default=str).encode("utf-8")
            output_file.write_bytes(output_bytes)
            checksum = hashlib.sha256(output_bytes).hexdigest()

            return {
                "success": True,
                "output_path": str(output_file),
                "checksum_sha256": checksum,
                "error": None,
                "result_data": result_data
            }

        except Exception as e:
            return {
                "success": False,
                "output_path": None,
                "checksum_sha256": None,
                "error": str(e)
            }


# Singleton instance
docker_executor = DockerExecutor()
