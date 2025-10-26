from pathlib import Path
import os
import shutil

def setup_project_directories(base_dir=None):
    """Create project directory structure"""
    if base_dir is None:
        base_dir = Path(__file__).parent.parent
    
    directories = [
        "data/raw",
        "data/processed",
        "models",
        "features",
        "signals",
        "backtest",
        "reports"
    ]
    
    for dir_path in directories:
        full_path = base_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        # Ensure write permissions
        os.chmod(full_path, 0o755)
    
    return base_dir

if __name__ == "__main__":
    base_dir = setup_project_directories()
    print(f"Created project structure in {base_dir}")
