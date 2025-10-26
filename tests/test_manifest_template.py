import pytest
import yaml
from pathlib import Path
import coverage

@pytest.fixture(scope="module")
def cov():
    """Initialize coverage tracking"""
    cov = coverage.Coverage()
    cov.start()
    yield cov
    cov.stop()
    cov.save()

def test_manifest_template_exists(cov):
    """Test manifest template file exists and is valid YAML with coverage tracking"""
    template_path = Path(__file__).parent.parent / "features/crypto-workflow/manifest_template.yaml"
    assert template_path.exists(), "Manifest template file not found"
    
    # Test YAML loading
    with open(template_path) as f:
        manifest = yaml.safe_load(f)
    
    # Verify required fields with complete coverage
    all_fields = {
        "exchange_id": str,
        "symbol": str,
        "interval": str,
        "start_timestamp": str,
        "end_timestamp": str,
        "fetch_timestamp": str,
        "version": str,
        "row_count": int,
        "validation": dict
    }
    
    for field, expected_type in all_fields.items():
        assert field in manifest, f"Missing required field: {field}"
        assert isinstance(manifest[field], expected_type), f"Wrong type for {field}"
    
    # Verify validation subfields
    validation_fields = {"missing_rows", "outliers", "gaps_filled"}
    assert validation_fields.issubset(manifest["validation"].keys())
    


def test_manifest_template_validation(cov):
    """Test manifest validation logic"""
    template_path = Path(__file__).parent.parent / "features/crypto-workflow/manifest_template.yaml"
    
    with open(template_path) as f:
        manifest = yaml.safe_load(f)
    
    # Test field constraints
    assert len(manifest["symbol"].split("-")) == 2, "Symbol should be in BASE-QUOTE format"
    assert manifest["interval"] in ["1min", "5min", "15min", "1h", "1d"], "Invalid interval"
    assert manifest["row_count"] >= 0, "Row count cannot be negative"
    
    # Test timestamp formats
    from datetime import datetime
    datetime.strptime(manifest["start_timestamp"], "%Y-%m-%dT%H:%M:%SZ")
    datetime.strptime(manifest["end_timestamp"], "%Y-%m-%dT%H:%M:%SZ")
    datetime.strptime(manifest["fetch_timestamp"], "%Y-%m-%dT%H:%M:%SZ")
