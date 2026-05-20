import importlib.util
from pathlib import Path


def test_strategy_template_imports_current_data_apis():
    path = Path(__file__).resolve().parents[2] / "backtest" / "strategies" / "_template.py"
    spec = importlib.util.spec_from_file_location("strategy_template", path)
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert hasattr(module, "StrategyTemplate")
