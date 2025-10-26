import pytest
from pathlib import Path
import os
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.setup_project_structure import setup_project_directories

def test_directory_creation(tmp_path):
    """Test project directory structure creation"""
    # Mock base directory for testing
    original_dir = Path(__file__).parent.parent
    test_dir = tmp_path / "qlib"
    test_dir.mkdir()
    
    expected_dirs = [
        "data/raw",
        "data/processed",
        "models",
        "features",
        "signals",
        "backtest",
        "reports"
    ]
    
    # Run directory setup
    setup_project_directories(test_dir)
    
    # Verify directories exist
    for dir_path in expected_dirs:
        full_path = test_dir / dir_path
        assert full_path.exists(), f"Directory not created: {dir_path}"
        assert full_path.is_dir(), f"Not a directory: {dir_path}"
        
        # Check permissions (755 = read/write/execute for owner, read/execute for others)
        stat = os.stat(full_path)
        assert stat.st_mode & 0o777 == 0o755, f"Incorrect permissions for {dir_path}"
        
        # Verify writeable
        try:
            test_file = full_path / "test.txt"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            pytest.fail(f"Directory not writeable: {dir_path}, error: {e}")
