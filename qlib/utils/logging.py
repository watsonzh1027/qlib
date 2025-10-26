import logging
import sys
from pathlib import Path
from datetime import datetime
import json
from typing import Optional

class JsonFormatter(logging.Formatter):
    """Format log records as JSON"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include extra attributes from record.__dict__
        standard_keys = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
            'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
            'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
            'processName', 'process'
        }
        extra_keys = set(record.__dict__.keys()) - standard_keys
        for key in extra_keys:
            log_data[key] = record.__dict__[key]

        return json.dumps(log_data)

class LogCapture:
    """Context manager for capturing log records in tests"""
    
    def __init__(self):
        self.records = []
    
    def __enter__(self):
        self.handler = logging.Handler()
        self.handler.emit = lambda record: (
            setattr(record, "extra", getattr(record, "extra", {})),
            self.records.append(json.loads(JsonFormatter().format(record)))
        )
        # Ensure extra attributes are included in the record
        self.handler.handle = lambda record: (
            setattr(record, "extra", getattr(record, "extra", {})),
            self.handler.emit(record)
        )
        logging.getLogger().addHandler(self.handler)
        return self
    
    def __exit__(self, *args):
        logging.getLogger().removeHandler(self.handler)

def setup_logger(name: str, log_file: Optional[Path] = None) -> logging.Logger:
    """Setup logger with console and optional file output"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Create formatters
    json_formatter = JsonFormatter()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file is not None:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)
    
    return logger
