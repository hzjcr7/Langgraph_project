from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from .schemas import AgentEvent
from .security import redact_sensitive_text


class AuditLogger:
    def __init__(self, output_dir: Path, scenario: str) -> None:
        self.run_id = uuid4().hex[:12]
        self.scenario = scenario
        self.path = output_dir / f"audit_{scenario}_{self.run_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, agent: str, event: str, **detail: object) -> None:
        safe_detail = {
            key: redact_sensitive_text(value) if isinstance(value, str) else value
            for key, value in detail.items()
        }
        record = AgentEvent(
            run_id=self.run_id,
            scenario=self.scenario,
            agent=agent,
            event=event,
            detail=safe_detail,
        )
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

