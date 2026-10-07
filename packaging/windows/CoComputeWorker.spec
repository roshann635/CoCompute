# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

repo_root = os.path.abspath(os.path.join(SPECPATH, "..", ".."))

added_files = [
    (os.path.join(repo_root, "shared"), "shared"),
    (os.path.join(repo_root, "worker", "app"), "worker/app"),
]

hidden_imports = [
    "psutil",
    "websockets",
    "websockets.client",
    "httpx",
    "httpcore",
    "json",
    "uuid",
    "hashlib",
    "hmac",
    "socket",
    "platform",
    "asyncio",
    "urllib.request",
    "urllib.error",
    "worker.app.core_config",
    "worker.app.monitor.capabilities",
    "worker.app.diagnostics.doctor",
    "worker.app.network.discovery",
    "worker.app.monitor.metrics",
    "worker.app.execution.docker_engine",
    "worker.app.history.task_history",
    "shared.protocol",
    "shared.sdk.registry",
    "shared.sdk.task_definition",
]

excluded_modules = [
    "torch",
    "tensorflow",
    "PySide6",
    "PyQt5",
    "PyQt6",
    "matplotlib",
    "scipy",
    "pandas",
    "tkinter",
]

a = Analysis(
    [os.path.join(repo_root, "worker", "start_worker.py")],
    pathex=[repo_root],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CoComputeWorker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
