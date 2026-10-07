"""
CoCompute Platform-Safe Core Configuration & Directory Resolver.

Manages cross-platform standard paths for configuration, logs, and task storage
without assuming repo-local or hardcoded operating system directories.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

APP_NAME = "CoCompute"
CONFIG_FILE_NAME = "worker_config.json"
LOG_FILE_NAME = "worker.log"


def get_base_dir() -> Path:
    """
    Returns platform-standard user directory for CoCompute data & settings:
    - Windows: %APPDATA%/CoCompute
    - Linux/macOS: ~/.config/cocompute (or $XDG_CONFIG_HOME/cocompute)
    """
    if sys.platform.startswith("win"):
        appdata = os.getenv("APPDATA")
        if appdata:
            base = Path(appdata) / APP_NAME
        else:
            base = Path.home() / f".{APP_NAME.lower()}"
    else:
        xdg_config = os.getenv("XDG_CONFIG_HOME")
        if xdg_config:
            base = Path(xdg_config) / APP_NAME.lower()
        else:
            base = Path.home() / ".config" / APP_NAME.lower()

    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        # Fallback to local temporary/home directory if creation fails
        fallback = Path.home() / f".{APP_NAME.lower()}"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    return base


def get_config_path() -> Path:
    """Returns absolute path to worker_config.json."""
    return get_base_dir() / CONFIG_FILE_NAME


def get_log_dir() -> Path:
    """Returns directory path where worker logs are kept."""
    log_dir = get_base_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_path() -> Path:
    """Returns absolute path to worker.log."""
    return get_log_dir() / LOG_FILE_NAME


def get_data_dir() -> Path:
    """Returns directory path for local databases/task history."""
    data_dir = get_base_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def load_config() -> Dict[str, Any]:
    """Load cached configuration from platform-standard directory."""
    path = get_config_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to read config from {path}: {e}")

    # Backward compatibility: check if old repo-level worker/config.json exists
    legacy_path = Path(__file__).resolve().parent.parent / "config.json"
    if legacy_path.exists():
        try:
            with open(legacy_path, "r", encoding="utf-8") as f:
                legacy_cfg = json.load(f)
                # Migrate to standard location
                save_config(legacy_cfg)
                return legacy_cfg
        except Exception:
            pass

    return {}


def save_config(updates: Dict[str, Any]):
    """Persist worker configuration updates to platform-standard directory."""
    path = get_config_path()
    try:
        current = load_config()
        current.update(updates)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to persist config to {path}: {e}")


def parse_master_code(code_str: str) -> Optional[Tuple[str, int]]:
    """
    Decodes a human-friendly Master Connect Code if applicable.
    Format examples: 'CC-4827', 'CC-192-168-1-50-8000', or standard IP:PORT.
    Returns (ip, port) or None.
    """
    if not code_str:
        return None
    cleaned = code_str.strip().upper()
    if cleaned.startswith("CC-"):
        payload = cleaned[3:]
        # Check if code is encoded octets: CC-192-168-1-50-8000
        parts = payload.split("-")
        if len(parts) == 5:
            try:
                ip = ".".join(parts[:4])
                port = int(parts[4])
                return ip, port
            except ValueError:
                pass
        elif len(parts) == 4:
            try:
                ip = ".".join(parts)
                return ip, 8000
            except ValueError:
                pass
    return None
