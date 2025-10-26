import pytest
import importlib.util
from pathlib import Path

EXAMPLE_SCRIPTS = [
    "collect_okx_ohlcv.py",
    "preprocess_features.py",
    "train_lgb.py",
    "predict_and_signal.py",
    "backtest.py"
]

def test_example_scripts_exist():
    """Test that all example script stubs exist"""
    examples_dir = Path(__file__).parent.parent / "examples"
    for script in EXAMPLE_SCRIPTS:
        script_path = examples_dir / script
        assert script_path.exists(), f"Missing script: {script}"

@pytest.mark.parametrize("script_name", EXAMPLE_SCRIPTS)
def test_script_imports(script_name):
    """Test that scripts can be imported without errors"""
    examples_dir = Path(__file__).parent.parent / "examples"
    script_path = examples_dir / script_name
    
    spec = importlib.util.spec_from_file_location(
        script_name.replace(".py", ""), 
        script_path
    )
    assert spec is not None, f"Cannot load spec for {script_name}"
    
    module = importlib.util.module_from_spec(spec)
    assert module is not None, f"Cannot create module for {script_name}"

@pytest.mark.parametrize("script_name", EXAMPLE_SCRIPTS)
def test_script_main_guard(script_name):
    """Test that scripts have proper __main__ guard"""
    examples_dir = Path(__file__).parent.parent / "examples"
    script_path = examples_dir / script_name
    
    with open(script_path) as f:
        content = f.read()
        assert '__main__' in content, f"Missing __main__ guard in {script_name}"
        assert 'if __name__ == "__main__":' in content, f"Improper main guard in {script_name}"
