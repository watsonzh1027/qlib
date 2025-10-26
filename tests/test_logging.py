import pytest
import logging
from pathlib import Path
from qlib.utils.logging import setup_logger, LogCapture

def test_logger_setup(tmp_path):
    """Test logger initialization and configuration"""
    log_path = tmp_path / "crypto_trading.log"
    logger = setup_logger("crypto_trading", log_path)
    
    assert logger.name == "crypto_trading"
    assert len(logger.handlers) >= 2  # File and console handlers
    assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)

def test_logger_setup_with_nonexistent_parent_dir(tmp_path):
    """Test logger setup when parent directory does not exist"""
    log_path = tmp_path / "nonexistent_dir" / "crypto_trading.log"
    logger = setup_logger("crypto_trading", log_path)
    
    assert logger.name == "crypto_trading"
    assert len(logger.handlers) >= 2  # File and console handlers
    assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)

def test_log_levels(tmp_path):
    """Test different log levels are properly handled"""
    with LogCapture() as logs:
        logger = setup_logger("test", tmp_path / "test.log")
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        assert any(record["message"] == "Debug message" for record in logs.records)
        assert any(record["message"] == "Error message" for record in logs.records)

def test_log_format():
    """Test log message format"""
    with LogCapture() as logs:
        logger = setup_logger("test")
        logger.info("Test message")
        
        record = logs.records[0]
        assert "timestamp" in record
        assert "level" in record
        assert "message" in record

def test_log_format_with_extra():
    """Test log message format with extra attributes"""
    with LogCapture() as logs:
        logger = setup_logger("test")
        logger.info("Test message", extra={"key": "value"})
        
        record = logs.records[0]
        assert "timestamp" in record
        assert "level" in record
        assert "message" in record
        assert "key" in record
        assert record["key"] == "value"
