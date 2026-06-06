from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any, Literal


RiskLevel = Literal["low", "medium", "high"]
GateStatus = Literal["passed", "warning", "failed"]


@dataclass
class Transaction:
    trade_date: str
    description: str
    amount: float
    currency: str = "HKD"
    category: str = "uncategorized"
    risk_flags: list[str] = field(default_factory=list)


@dataclass
class BankStatement:
    account_name: str
    account_no: str
    period_start: str
    period_end: str
    opening_balance: float
    closing_balance: float
    transactions: list[Transaction] = field(default_factory=list)
    extraction_confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RegulatoryItem:
    title: str
    url: str
    published_at: str
    body: str
    source: str = "SFC"
    category: str = "uncategorized"
    summary: str = ""
    risk_level: RiskLevel = "low"
    obligations: list[str] = field(default_factory=list)
    action_owner: str = "compliance"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentRunResult:
    scenario: str
    artifacts: dict[str, str]
    metrics: dict[str, Any]
    trace: list[str]
    audit_path: str | None = None
    quality_gates: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentEvent:
    run_id: str
    scenario: str
    agent: str
    event: str
    detail: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QualityGate:
    name: str
    status: GateStatus
    score: float
    threshold: float
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def today_iso() -> str:
    return date.today().isoformat()
