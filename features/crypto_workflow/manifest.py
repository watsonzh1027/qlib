"""Manifest writer for data files"""
import yaml
from pathlib import Path
import hashlib
from typing import Dict, Any

def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def write_manifest(file_path: Path, metadata: Dict[str, Any]) -> None:
    """Write/update manifest file for data file"""
    manifest_path = file_path.parent / 'manifest.yaml'
    
    # Compute file hash
    metadata['file_hash'] = compute_file_hash(file_path)
    
    # Load existing manifest if it exists
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f) or {}
    
    # Update manifest with new file entry
    manifest[file_path.name] = metadata
    
    # Write manifest atomically
    temp_path = manifest_path.with_suffix('.tmp')
    with open(temp_path, 'w') as f:
        yaml.dump(manifest, f)
    temp_path.rename(manifest_path)
