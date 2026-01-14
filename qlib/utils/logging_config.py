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
import threading
import multiprocessing
from pathlib import Path
from typing import Any, Dict, Optional

# Global variables to track initialization state within the process
_initialization_lock = threading.Lock()
_initialized_pid = None

def load_logging_config() -> Dict[str, Any]:
    """Load logging parameters from centralized workflow.json."""
    # Resolve project root (src/utils/logging_config.py -> src/utils -> src -> qlib-crypto)
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "config" / "workflow.json"
    
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
            try:
                # In some cases, unlink might fail if file is locked
                with open(new_log, 'w') as f:
                    f.truncate(0)
            except Exception:
                pass
    return new_log

class NumberedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Custom RotatingFileHandler that uses -1.log, -2.log naming scheme."""
    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        
        base_path = Path(self.baseFilename)
        directory = base_path.parent
        # Expecting filename to end with -1.log
        if base_path.name.endswith("-1.log"):
            base_name = base_path.name[:-6]
            extension = ".log"
            rotate_numbered_logs(directory, base_name, extension, self.backupCount + 1)
        
        if not self.delay:
            self.stream = self._open()

def setup_logging(name: Optional[str] = None, skip_rotation: bool = False) -> logging.Logger:
    """Setup standard logging based on workflow.json with manual rotation and multi-process support.
    
    Args:
        name: Optional logger name. If not provided, uses script name.
        skip_rotation: If True, skip manual rotation at startup.
    """
    global _initialized_pid
    
    current_pid = os.getpid()
    with _initialization_lock:
        # Check if already initialized in this process
        if _initialized_pid == current_pid and name is None:
            return logging.getLogger()
        
        log_cfg = load_logging_config()
        
        log_level_str = log_cfg.get("level", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        
        # Identify module name
        if name:
            module_name = name
        elif hasattr(sys, 'argv') and sys.argv[0]:
            module_name = Path(sys.argv[0]).stem
        else:
            module_name = "unknown"
        
        # Handle log_file template
        log_file_tmpl = log_cfg.get("log_file", "<module.name>")
        log_suffix = log_file_tmpl.replace("<module.name>", module_name)
        
        # Multi-process support: Check if we are in the main process
        # In multi-processing, we add PID to filename for sub-processes to avoid collisions
        is_main_process = (multiprocessing.current_process().name == 'MainProcess')
        
        if not is_main_process:
            log_suffix = f"{log_suffix}-{current_pid}"
        
        log_base = log_cfg.get("log_base", "qlib-")
        combined_log_base = f"{log_base}{log_suffix}" if log_suffix else log_base
        
        max_index = int(log_cfg.get("max_index", 9))
        output_modes = [m.strip().lower() for m in log_cfg.get("output", "file").split(",")]
        
        # Get root logger
        logger = logging.getLogger()
        logger.setLevel(log_level)
        
        # Remove existing handlers to avoid duplication and override defaults
        while logger.handlers:
            logger.removeHandler(logger.handlers[0])
        
        # Format: time | level | name:func:line - message
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Console Handler
        if "console" in output_modes:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # File Handler logic
        if "file" in output_modes:
            project_root = Path(__file__).parent.parent.parent
            log_dir = project_root / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            extension = ".log"
            # Perform manual rotation at startup ONLY for the main process
            if not skip_rotation and is_main_process:
                log_path = rotate_numbered_logs(log_dir, combined_log_base, extension, max_index)
                mode = 'w'
            else:
                log_path = log_dir / f"{combined_log_base}-1{extension}"
                mode = 'a'
            
            # Use custom rotating handler for both startup and over-size rotation
            max_bytes = int(log_cfg.get("max_bytes", 100 * 1024 * 1024)) # Default 100MB
            # By using NumberedRotatingFileHandler, we support both the startup rotation 
            # and the runtime over-size rotation as requested.
            file_handler = NumberedRotatingFileHandler(
                log_path, mode=mode, encoding="utf-8", 
                maxBytes=max_bytes, backupCount=max_index-1
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            if _initialized_pid != current_pid:
                logger.info(f"Logging initialized for {module_name} (PID: {current_pid})")
                logger.info(f"Current log file: {log_path.name}")
        else:
            if _initialized_pid != current_pid:
                logger.info(f"Logging initialized for {module_name} (Console only)")
        
        # CRITICAL: Suppress qlib's default file logging to qlib.log
        try:
            from qlib.config import C
            def disable_qlib_file_logging(conf):
                if isinstance(conf, dict) and "logging_config" in conf:
                    lc = conf["logging_config"]
                    if "handlers" in lc:
                        lc["handlers"].pop("file", None)
                    if "loggers" in lc and "qlib" in lc["loggers"]:
                        qlib_cfg = lc["loggers"]["qlib"]
                        if "handlers" in qlib_cfg:
                            # Remove all qlib-specific handlers to avoid duplicates and use root logger
                            qlib_cfg["handlers"] = []
                        qlib_cfg["propagate"] = True

            # Disable in current config
            disable_qlib_file_logging(C.__dict__.get("_config", {}))
            # Disable in default config so qlib.init() won't restore it
            disable_qlib_file_logging(C.__dict__.get("_default_config", {}))
            
            # Also clear current handlers if already initialized
            qlib_logger = logging.getLogger("qlib")
            qlib_logger.propagate = True
            for h in qlib_logger.handlers[:]:
                qlib_logger.removeHandler(h)
        except (ImportError, AttributeError):
            pass
        
        # Log the full command line for traceability
        try:
            if hasattr(sys, 'argv') and sys.argv:
                cmd_line = " ".join(sys.argv)
                logger.debug(f"Command line: {cmd_line}")
        except Exception:
            pass

        _initialized_pid = current_pid

    return logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance with an optional name."""
    if name:
        return logging.getLogger(name)
    return logging.getLogger()

# Auto-initialize on import
#setup_logging()
