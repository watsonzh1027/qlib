"""
Logging configuration for qlib-crypto.
Uses standard logging module and reads parameters from config/trading_params.json.
Main features:
1. xxx-1.log is always the current latest log file.
2. Each run starts a fresh log file (overwrites xxx-1.log after rotating older ones).
"""

import logging
import json
import sys
import shutil
import os
from pathlib import Path
from typing import Any, Dict, Optional

def load_logging_config() -> Dict[str, Any]:
    """Load logging parameters from centralized trading_params.json."""
    # Resolve project root (src/utils/logging_config.py -> src/utils -> src -> qlib-crypto)
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "config" / "trading_params.json"
    
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("logging", {})
        except Exception as e:
            # Fallback to defaults if file is unreadable
            pass
    
    return {}

def rotate_numbered_logs(directory: Path, base_name: str, extension: str, max_index: int = 9) -> Path:
    """Rotate existing numbered logs and return the path for the new log (base-1.ext).
    
    This shifts base-(i-1).ext -> base-i.ext for i from max_index down to 2,
    then ensures base-1.ext is available for the new log file.
    """
    # Move from highest to lowest to avoid clobbering
    for i in range(max_index, 1, -1):
        src = directory / f"{base_name}-{i-1}{extension}"
        dst = directory / f"{base_name}-{i}{extension}"
        if src.exists():
            try:
                if dst.exists():
                    dst.unlink()
                src.replace(dst)
            except Exception:
                # Best-effort: try shutil.move as fallback
                try:
                    shutil.move(str(src), str(dst))
                except Exception:
                    pass

    # New log is base-1.ext
    new_log = directory / f"{base_name}-1{extension}"
    # If base-1 still exists unexpectedly, remove it (it should have been moved)
    if new_log.exists():
        try:
            new_log.unlink()
        except Exception:
            pass
    return new_log

def setup_logging(skip_rotation: bool = False) -> logging.Logger:
    """Setup standard logging based on trading_params.json with manual rotation."""
    log_cfg = load_logging_config()
    
    log_level_str = log_cfg.get("level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Parameters for rotation
    log_base = log_cfg.get("log_base", "glib-crypto")
    max_index = int(log_cfg.get("max_index", 9))
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplication
    while logger.handlers:
        logger.removeHandler(logger.handlers[0])
    
    # Format: time | level | name:func:line - message
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Rotating File logic
    project_root = Path(__file__).parent.parent.parent
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Extension and rotation
    extension = ".log"
    # Perform manual rotation at startup if not skipped
    if not skip_rotation:
        log_path = rotate_numbered_logs(log_dir, log_base, extension, max_index)
    else:
        log_path = log_dir / f"{log_base}-1{extension}"
    
    # Use mode='a' if skipping rotation to append to existing log, 'w' otherwise
    mode = 'a' if skip_rotation else 'w'
    file_handler = logging.FileHandler(log_path, mode=mode, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"Logging initialized with level: {log_level_str}")
    logger.info(f"Current log file: {log_path.name}")
    
    # Log the full command line for traceability
    try:
        if hasattr(sys, 'argv') and sys.argv:
            cmd_line = " ".join(sys.argv)
            logger.info(f"Command line: {cmd_line}")
    except Exception:
        pass

    return logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance with an optional name."""
    if name:
        return logging.getLogger(name)
    return logging.getLogger()

# Auto-initialize on import
setup_logging()
