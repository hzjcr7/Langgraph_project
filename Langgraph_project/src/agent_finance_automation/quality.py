from __future__ import annotations

from .schemas import BankStatement, QualityGate, RegulatoryItem


def bank_quality_gates(statement: BankStatement, warnings: list[str]) -> list[QualityGate]:
    balance_score = 1.0 if not any("Balance mismatch" in warning for warning in warnings) else 0.0
    field_score = sum(
        [
            bool(statement.account_name),
            bool(statement.account_no),
            bool(statement.period_start),
            bool(statement.period_end),
            bool(statement.transactions),
        ]
    ) / 5
    warning_score = 1.0 if not warnings else max(0.0, 1 - len(warnings) * 0.2)
    return [
        QualityGate("required_fields", _status(field_score, 0.9), field_score, 0.9, "Core account fields extracted"),
        QualityGate("balance_reconciliation", _status(balance_score, 1.0), balance_score, 1.0, "Opening + flows equals closing"),
        QualityGate("compliance_warning_budget", _status(warning_score, 0.8), warning_score, 0.8, "Warnings stay under review threshold"),
    ]


def regulatory_quality_gates(items: list[RegulatoryItem]) -> list[QualityGate]:
    if not items:
        return [QualityGate("news_coverage", "failed", 0.0, 1.0, "No regulatory items processed")]
    summary_score = sum(bool(item.summary) for item in items) / len(items)
    category_score = sum(item.category != "uncategorized" for item in items) / len(items)
    action_score = sum(bool(item.obligations) for item in items) / len(items)
    return [
        QualityGate("classification_coverage", _status(category_score, 1.0), category_score, 1.0, "Every item receives a category"),
        QualityGate("summary_coverage", _status(summary_score, 1.0), summary_score, 1.0, "Every item receives a summary"),
        QualityGate("obligation_extraction", _status(action_score, 0.8), action_score, 0.8, "Actionable obligations extracted"),
    ]


def _status(score: float, threshold: float) -> str:
    if score >= threshold:
        return "passed"
    if score >= threshold * 0.75:
        return "warning"
    return "failed"

