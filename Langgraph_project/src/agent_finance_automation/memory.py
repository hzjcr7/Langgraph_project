from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, asdict
import json
import math
import re
from pathlib import Path
from typing import Iterable


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


@dataclass
class MemoryRecord:
    namespace: str
    text: str
    metadata: dict


class ShortTermMemory:
    def __init__(self, max_items: int = 12) -> None:
        self.items: deque[MemoryRecord] = deque(maxlen=max_items)

    def add(self, namespace: str, text: str, **metadata: str) -> None:
        self.items.append(MemoryRecord(namespace=namespace, text=text, metadata=metadata))

    def context(self, namespace: str | None = None) -> str:
        records = [item for item in self.items if namespace is None or item.namespace == namespace]
        return "\n".join(f"- {item.text}" for item in records[-6:])


class LongTermVectorMemory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records: list[MemoryRecord] = []
        self._load()

    def add(self, namespace: str, text: str, **metadata: str) -> None:
        self.records.append(MemoryRecord(namespace=namespace, text=text, metadata=metadata))
        self._save()

    def search(self, namespace: str, query: str, limit: int = 4) -> list[MemoryRecord]:
        query_vec = _vectorize(query)
        scored: list[tuple[float, MemoryRecord]] = []
        for record in self.records:
            if record.namespace != namespace:
                continue
            score = _cosine(query_vec, _vectorize(record.text))
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:limit]]

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.records = [MemoryRecord(**item) for item in raw]

    def _save(self) -> None:
        self.path.write_text(
            json.dumps([asdict(item) for item in self.records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class AgentMemory:
    def __init__(self, memory_dir: Path) -> None:
        self.short_term = ShortTermMemory()
        self.long_term = LongTermVectorMemory(memory_dir / "long_term_memory.json")

    def remember(self, namespace: str, text: str, durable: bool = False, **metadata: str) -> None:
        self.short_term.add(namespace, text, **metadata)
        if durable:
            self.long_term.add(namespace, text, **metadata)

    def recall(self, namespace: str, query: str) -> str:
        short_context = self.short_term.context(namespace)
        long_context = "\n".join(f"- {item.text}" for item in self.long_term.search(namespace, query))
        parts = [part for part in [short_context, long_context] if part]
        return "\n".join(parts)


def _tokens(text: str) -> Iterable[str]:
    for match in TOKEN_PATTERN.finditer(text.lower()):
        yield match.group(0)


def _vectorize(text: str) -> Counter[str]:
    return Counter(_tokens(text))


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(token, 0) for token, value in a.items())
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

