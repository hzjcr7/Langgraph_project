from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from .audit import AuditLogger
from .config import Settings
from .llm import HybridLLM
from .memory import AgentMemory
from .quality import bank_quality_gates, regulatory_quality_gates
from .schemas import AgentRunResult, RegulatoryItem
from .security import inspect_document_security
from .skills.bank_statement import (
    extract_bank_statement,
    validate_statement,
    write_statement_excel,
    write_statement_json,
)
from .skills.document_parser import parse_document
from .skills.regulatory_digest import (
    enrich_regulatory_items,
    load_regulatory_items,
    write_digest_docx,
    write_digest_json,
)


@dataclass
class WorkflowState:
    scenario: str
    input_path: str
    output_dir: str
    text: str = ""
    statement: Any = None
    regulatory_items: list[RegulatoryItem] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    trace: list[str] = field(default_factory=list)
    audit: AuditLogger | None = None
    quality_gates: list[dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=perf_counter)


class MiniStateGraph:
    def __init__(self) -> None:
        self.nodes: list[tuple[str, Callable[[WorkflowState], WorkflowState]]] = []

    def add_node(self, name: str, func: Callable[[WorkflowState], WorkflowState]) -> None:
        self.nodes.append((name, func))

    def invoke(self, state: WorkflowState) -> WorkflowState:
        for name, func in self.nodes:
            state.trace.append(f"agent:{name}:start")
            if state.audit:
                state.audit.log(name, "start")
            state = func(state)
            state.trace.append(f"agent:{name}:done")
            if state.audit:
                state.audit.log(name, "done", metrics=state.metrics.copy())
        return state


class FinanceAutomationGraph:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.llm = HybridLLM(settings)
        self.memory = AgentMemory(settings.memory_dir)

    def run_bank_statement(self, input_path: str | Path) -> AgentRunResult:
        graph = MiniStateGraph()
        graph.add_node("document_parser", self._parse_document)
        graph.add_node("security_guard", self._inspect_document_security)
        graph.add_node("bank_extractor", self._extract_bank_statement)
        graph.add_node("compliance_validator", self._validate_bank_statement)
        graph.add_node("quality_gate", self._bank_quality_gate)
        graph.add_node("excel_filler", self._write_bank_artifacts)
        state = WorkflowState("bank_statement", str(input_path), str(self.settings.output_dir))
        state.audit = AuditLogger(self.settings.output_dir, state.scenario)
        state.audit.log("orchestrator", "run_created", input_path=str(input_path))
        return self._finish(graph.invoke(state))

    def run_regulatory_digest(self, input_path: str | Path) -> AgentRunResult:
        graph = MiniStateGraph()
        graph.add_node("news_loader", self._load_regulatory_items)
        graph.add_node("classification_summarizer", self._enrich_regulatory_items)
        graph.add_node("quality_gate", self._regulatory_quality_gate)
        graph.add_node("word_archiver", self._write_regulatory_artifacts)
        state = WorkflowState("regulatory_digest", str(input_path), str(self.settings.output_dir))
        state.audit = AuditLogger(self.settings.output_dir, state.scenario)
        state.audit.log("orchestrator", "run_created", input_path=str(input_path))
        return self._finish(graph.invoke(state))

    def _parse_document(self, state: WorkflowState) -> WorkflowState:
        state.text = parse_document(state.input_path)
        self.memory.remember("document", f"Parsed {state.input_path} with {len(state.text)} characters")
        return state

    def _inspect_document_security(self, state: WorkflowState) -> WorkflowState:
        security = inspect_document_security(state.text)
        state.metrics["security"] = security
        if state.audit:
            state.audit.log("security_guard", "document_inspected", fingerprint=security["fingerprint"])
        if not security["within_size_limit"]:
            raise ValueError("Document exceeds configured security size limit")
        return state

    def _extract_bank_statement(self, state: WorkflowState) -> WorkflowState:
        context = self.memory.recall("bank_statement", state.text[:500])
        if context:
            state.trace.append("memory:bank_statement:context_attached")
        state.statement = extract_bank_statement(state.text)
        self.memory.remember(
            "bank_statement",
            f"Extracted account {state.statement.account_no} confidence {state.statement.extraction_confidence}",
            durable=True,
        )
        return state

    def _validate_bank_statement(self, state: WorkflowState) -> WorkflowState:
        warnings = validate_statement(state.statement)
        state.statement.warnings = warnings
        state.metrics["warning_count"] = len(warnings)
        state.metrics["extraction_confidence"] = state.statement.extraction_confidence
        state.metrics["transaction_count"] = len(state.statement.transactions)
        state.metrics["transaction_risk_flags"] = sum(len(tx.risk_flags) for tx in state.statement.transactions)
        state.metrics["compliance_passed"] = len(warnings) == 0
        return state

    def _bank_quality_gate(self, state: WorkflowState) -> WorkflowState:
        gates = bank_quality_gates(state.statement, state.statement.warnings)
        state.quality_gates = [gate.to_dict() for gate in gates]
        state.metrics["quality_passed"] = all(gate.status == "passed" for gate in gates)
        return state

    def _write_bank_artifacts(self, state: WorkflowState) -> WorkflowState:
        output_dir = Path(state.output_dir)
        excel_path = write_statement_excel(state.statement, output_dir / "filled_bank_statement.xlsx")
        json_path = write_statement_json(state.statement, output_dir / "bank_result.json")
        state.artifacts.update({"excel": str(excel_path), "json": str(json_path)})
        return state

    def _load_regulatory_items(self, state: WorkflowState) -> WorkflowState:
        state.regulatory_items = load_regulatory_items(state.input_path)
        self.memory.remember("regulatory", f"Loaded {len(state.regulatory_items)} regulatory items")
        return state

    def _enrich_regulatory_items(self, state: WorkflowState) -> WorkflowState:
        state.regulatory_items = enrich_regulatory_items(state.regulatory_items, self.llm)
        high_risk = sum(1 for item in state.regulatory_items if item.risk_level == "high")
        obligation_count = sum(len(item.obligations) for item in state.regulatory_items)
        state.metrics["item_count"] = len(state.regulatory_items)
        state.metrics["high_risk_count"] = high_risk
        state.metrics["obligation_count"] = obligation_count
        for item in state.regulatory_items:
            self.memory.remember("regulatory", f"{item.category}: {item.title}", durable=True)
        return state

    def _regulatory_quality_gate(self, state: WorkflowState) -> WorkflowState:
        gates = regulatory_quality_gates(state.regulatory_items)
        state.quality_gates = [gate.to_dict() for gate in gates]
        state.metrics["quality_passed"] = all(gate.status == "passed" for gate in gates)
        return state

    def _write_regulatory_artifacts(self, state: WorkflowState) -> WorkflowState:
        output_dir = Path(state.output_dir)
        docx_path = write_digest_docx(state.regulatory_items, output_dir / "regulatory_digest.docx")
        json_path = write_digest_json(state.regulatory_items, output_dir / "regulatory_digest.json")
        state.artifacts.update({"docx": str(docx_path), "json": str(json_path)})
        return state

    def _finish(self, state: WorkflowState) -> AgentRunResult:
        state.metrics["latency_seconds"] = round(perf_counter() - state.started_at, 3)
        return AgentRunResult(
            scenario=state.scenario,
            artifacts=state.artifacts,
            metrics=state.metrics,
            trace=state.trace,
            audit_path=str(state.audit.path) if state.audit else None,
            quality_gates=state.quality_gates,
        )
