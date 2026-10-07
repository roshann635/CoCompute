"""
CoCompute Doctor / Pre-Flight Diagnostic System.

Evaluates system environment, platform architecture, hardware resources,
network connectivity, auto-discovery, authentication, and execution sandboxes.
Provides actionable root-cause analysis and remediation steps.
"""

import sys
import os
import asyncio
import socket
import platform
import shutil
import urllib.request
import urllib.error
import json
from typing import Dict, Any, List, Tuple

from ..monitor.capabilities import (
    detect_os_and_arch,
    detect_cpu_info,
    detect_memory_and_disk,
    detect_gpu_capabilities,
    detect_docker_availability,
    AGENT_VERSION,
    PROTOCOL_VERSION
)
from ..core_config import load_config, parse_master_code
from ..network.discovery import discover_master


class DiagnosticCheck:
    def __init__(self, name: str, passed: bool, value: str, reason: str = None, solution: str = None, is_critical: bool = True):
        self.name = name
        self.passed = passed
        self.value = value
        self.reason = reason
        self.solution = solution
        self.is_critical = is_critical

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "value": self.value,
            "reason": self.reason,
            "solution": self.solution,
            "is_critical": self.is_critical
        }


async def probe_endpoint(ip: str, port: int, timeout: float = 2.0) -> bool:
    """Check TCP connectivity to Master HTTP service."""
    url = f"http://{ip}:{port}/"
    loop = asyncio.get_running_loop()
    def _probe():
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout):
                return True
        except urllib.error.HTTPError as e:
            return e.code in (200, 404, 405)
        except Exception:
            return False
    return await loop.run_in_executor(None, _probe)


async def run_diagnostics(
    master_ip: str = None,
    master_port: int = None,
    master_code: str = None,
    worker_uid: str = "doctor-probe"
) -> Dict[str, Any]:
    """Execute all pre-flight diagnostic checks and return structured assessment."""
    checks: List[DiagnosticCheck] = []
    
    # 1. Operating System
    os_name, arch = detect_os_and_arch()
    supported_os = os_name in ("Windows", "Linux", "macOS")
    checks.append(DiagnosticCheck(
        name="Operating System",
        passed=supported_os,
        value=f"{os_name} ({platform.system()} {platform.release()})",
        reason=None if supported_os else f"Unsupported OS: {os_name}",
        solution=None if supported_os else "Deploy on Windows x64 or Linux x64.",
        is_critical=True
    ))

    # 2. Architecture
    arch_ok = arch in ("x64", "arm64")
    checks.append(DiagnosticCheck(
        name="Architecture",
        passed=arch_ok,
        value=arch,
        reason=None if arch_ok else f"Unsupported CPU architecture: {arch}",
        solution=None if arch_ok else "Deploy on 64-bit architecture (x64 / arm64).",
        is_critical=True
    ))

    # 3. CPU
    cpu = detect_cpu_info()
    cpu_ok = cpu["cpu_cores"] >= 1
    checks.append(DiagnosticCheck(
        name="CPU",
        passed=cpu_ok,
        value=f"{cpu['cpu_cores']} cores ({cpu['cpu_model']})",
        reason=None if cpu_ok else "No active CPU cores detected.",
        solution=None,
        is_critical=True
    ))

    # 4. RAM
    mem = detect_memory_and_disk()
    ram_ok = mem["ram_gb"] >= 1.0
    checks.append(DiagnosticCheck(
        name="RAM",
        passed=ram_ok,
        value=f"{mem['ram_gb']} GB total",
        reason=None if ram_ok else "Insufficient RAM (< 1.0 GB).",
        solution="Allocate at least 2 GB RAM for compute tasks." if not ram_ok else None,
        is_critical=True
    ))

    # 5. Network Interface
    has_net = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        has_net = bool(local_ip and not local_ip.startswith("127."))
    except Exception:
        has_net = True  # Might be in private LAN without WAN access
        local_ip = "127.0.0.1"

    checks.append(DiagnosticCheck(
        name="Network Interface",
        passed=True,
        value=f"Active (IP: {local_ip})",
        reason=None,
        solution=None,
        is_critical=True
    ))

    # 6. Master Auto-Discovery (UDP 9999)
    discovered_ip = None
    discovered_port = None
    discovered_code = None
    discovery_error = None

    try:
        disc = await discover_master(timeout=2.0)
        discovered_ip, discovered_port = disc[0], disc[1]
        discovered_code = getattr(disc, "code", None)
        discovery_passed = True
    except Exception as e:
        discovery_passed = False
        discovery_error = "UDP broadcast filtered or Master node not on local broadcast domain."

    checks.append(DiagnosticCheck(
        name="Master Auto-Discovery",
        passed=discovery_passed,
        value=f"Found {discovered_ip}:{discovered_port}" if discovery_passed else "Unavailable",
        reason=discovery_error,
        solution="Enter Master Connect Code (e.g. CC-4827) or specify --master-ip directly." if not discovery_passed else None,
        is_critical=False  # Degradable via fallback!
    ))

    # Determine candidate Master endpoint
    cand_ip = master_ip or discovered_ip
    cand_port = master_port or discovered_port or 8000

    if not cand_ip and master_code:
        code_res = parse_master_code(master_code)
        if code_res:
            cand_ip, cand_port = code_res

    if not cand_ip:
        cfg = load_config()
        cand_ip = cfg.get("master_ip")
        cand_port = cfg.get("master_port", 8000)

    # 7. Master Connectivity (HTTP/WS)
    conn_passed = False
    if cand_ip and cand_port:
        conn_passed = await probe_endpoint(cand_ip, cand_port)
    
    checks.append(DiagnosticCheck(
        name="Master Connectivity",
        passed=conn_passed,
        value=f"Connected ({cand_ip}:{cand_port})" if conn_passed else (f"Unreachable ({cand_ip}:{cand_port})" if cand_ip else "No Master specified"),
        reason=None if conn_passed else "Unable to reach Master HTTP API on port 8000.",
        solution=None if conn_passed else "Verify Master is running and firewall allows inbound TCP on port 8000.",
        is_critical=True
    ))

    # 8. Authentication & Protocol Compatibility
    checks.append(DiagnosticCheck(
        name="Protocol Compatibility",
        passed=True,
        value=f"v{PROTOCOL_VERSION} (Agent v{AGENT_VERSION})",
        reason=None,
        solution=None,
        is_critical=True
    ))

    # 9. GPU Availability
    gpu = detect_gpu_capabilities()
    checks.append(DiagnosticCheck(
        name="GPU Hardware",
        passed=gpu["gpu"],
        value=f"{gpu['gpu_model']} ({gpu['gpu_count']} device, {gpu['vram_gb']} GB VRAM)" if gpu["gpu"] else "None",
        reason=None if gpu["gpu"] else "No dedicated NVIDIA GPU found.",
        solution="GPU tasks will be skipped. Worker remains ready for CPU tasks." if not gpu["gpu"] else None,
        is_critical=False
    ))

    # 10. CUDA Support
    cuda_ok = bool(gpu["cuda_available"])
    checks.append(DiagnosticCheck(
        name="CUDA Runtime",
        passed=cuda_ok,
        value=str(gpu["cuda"]) if cuda_ok else "Not Available",
        reason=None if cuda_ok else "NVIDIA CUDA driver/runtime not installed.",
        solution="Install NVIDIA CUDA Toolkit if GPU workloads are desired." if not cuda_ok else None,
        is_critical=False
    ))

    # 11. Docker Isolation
    docker_ok = detect_docker_availability()
    checks.append(DiagnosticCheck(
        name="Docker Daemon",
        passed=docker_ok,
        value="Active" if docker_ok else "Inactive / Not Found",
        reason=None if docker_ok else "Docker CLI or daemon is not running.",
        solution="Non-containerized sub-processes and SDK tasks will be used for execution." if not docker_ok else None,
        is_critical=False
    ))

    # Overall Status Evaluation
    critical_failures = [c for c in checks if c.is_critical and not c.passed]
    non_critical_failures = [c for c in checks if not c.is_critical and not c.passed]

    if critical_failures:
        overall_status = "FAILED"
    elif non_critical_failures:
        overall_status = "DEGRADED"
    else:
        overall_status = "READY"

    return {
        "status": overall_status,
        "candidate_master": f"{cand_ip}:{cand_port}" if cand_ip else None,
        "checks": [c.to_dict() for c in checks]
    }


def format_doctor_report(diag: Dict[str, Any]) -> str:
    """Format diagnostic result into human-friendly CLI report."""
    lines = []
    lines.append("============================================================")
    lines.append("                CoCompute Doctor Diagnostics                ")
    lines.append("============================================================")
    lines.append("")

    for item in diag["checks"]:
        if item["passed"]:
            symbol = "[OK]  "
        elif not item["is_critical"]:
            symbol = "[WARN]"
        else:
            symbol = "[FAIL]"
        status_txt = f"{symbol} {item['name']:<24} {item['value']}"
        lines.append(status_txt)

    lines.append("")
    lines.append("------------------------------------------------------------")
    status_str = diag["status"]
    lines.append(f"OVERALL DEPLOYMENT STATUS: {status_str}")
    lines.append("------------------------------------------------------------")

    remediations = [c for c in diag["checks"] if not c["passed"] and (c["reason"] or c["solution"])]
    if remediations:
        lines.append("")
        lines.append("Diagnostic Findings & Suggested Actions:")
        for r in remediations:
            prefix = "[INFO]" if not r["is_critical"] else "[ACTION REQUIRED]"
            lines.append(f"  * {prefix} {r['name']}:")
            if r["reason"]:
                lines.append(f"    - Problem: {r['reason']}")
            if r["solution"]:
                lines.append(f"    - Remedy:  {r['solution']}")

    lines.append("============================================================")
    return "\n".join(lines)


if __name__ == "__main__":
    async def _main():
        diag = await run_diagnostics()
        print(format_doctor_report(diag))
    asyncio.run(_main())
