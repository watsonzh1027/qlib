import os
import json
import joblib
from pathlib import Path
from typing import Any, Dict
import tempfile
import shutil

def save_model(obj: Any, path: str, metadata: Dict = None) -> None:
    """Save model with metadata using atomic write."""
    path = Path(path)
    
    # Create temporary directory for atomic write
    tmp_dir = tempfile.mkdtemp()
    tmp_model = Path(tmp_dir) / "model.joblib"
    tmp_meta = Path(tmp_dir) / "metadata.json"
    
    try:
        # Save model
        joblib.dump(obj, tmp_model)
        
        # Save metadata if provided
        if metadata:
            with open(tmp_meta, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        # Create target directory if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic move of files
        shutil.move(str(tmp_model), str(path))
        if metadata:
            shutil.move(str(tmp_meta), str(path.with_suffix('.json')))
            
    finally:
        # Cleanup temp directory
        shutil.rmtree(tmp_dir, ignore_errors=True)

def load_model(path: str) -> tuple[Any, Dict]:
    """Load model and metadata if exists."""
    path = Path(path)
    
    # Load model
    model = joblib.load(path)
    
    # Load metadata if exists
    metadata = {}
    meta_path = path.with_suffix('.json')
    if meta_path.exists():
        with open(meta_path) as f:
            metadata = json.load(f)
            
    return model, metadata
