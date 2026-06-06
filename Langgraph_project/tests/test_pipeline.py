from __future__ import annotations

from pathlib import Path

from src.agent_finance_automation.config import DATA_DIR, get_settings
from src.agent_finance_automation.evaluation import run_evaluation
from src.agent_finance_automation.graph import FinanceAutomationGraph


def test_bank_pipeline(tmp_path: Path) -> None:
    settings = get_settings()
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    result = FinanceAutomationGraph(settings).run_bank_statement(DATA_DIR / "sample_bank_statement.txt")
    assert result.metrics["transaction_count"] == 6
    assert result.metrics["compliance_passed"] is True
    assert Path(result.artifacts["excel"]).exists()


def test_evaluation_report() -> None:
    settings = get_settings()
    report = run_evaluation(settings)
    assert report["accuracy"]["bank_extraction_confidence"] >= 0.8
    assert report["efficiency"]["estimated_agent_minutes"] == 5

