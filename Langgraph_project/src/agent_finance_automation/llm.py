from __future__ import annotations

from dataclasses import dataclass
import json
import re
import urllib.error
import urllib.request

from .config import Settings


@dataclass
class LLMResponse:
    text: str
    used_remote: bool = False


class BaseLLM:
    def complete(self, system: str, user: str) -> LLMResponse:
        raise NotImplementedError


class OpenAIResponsesClient(BaseLLM):
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        self.settings = settings

    def complete(self, system: str, user: str) -> LLMResponse:
        payload = {
            "model": self.settings.openai_model,
            "input": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        request = urllib.request.Request(
            f"{self.settings.openai_base_url.rstrip('/')}/responses",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.openai_api_key}",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = data.get("output_text") or _extract_response_text(data)
        return LLMResponse(text=text.strip(), used_remote=True)


class LocalHeuristicLLM(BaseLLM):
    """A deterministic fallback for demos without network or API keys."""

    def complete(self, system: str, user: str) -> LLMResponse:
        lowered = f"{system}\n{user}".lower()
        if "classify" in lowered or "监管" in lowered:
            return LLMResponse(text=self._classify_and_summarize(user))
        if "extract" in lowered or "抽取" in lowered:
            return LLMResponse(text=self._extract_jsonish(user))
        return LLMResponse(text=self._summarize(user))

    def _summarize(self, text: str) -> str:
        clean = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(r"(?<=[.!?。！？])\s*", clean)
        return " ".join(sentences[:2])[:500]

    def _classify_and_summarize(self, text: str) -> str:
        business_text = _extract_business_text(text)
        rules = [
            ("aml", ["aml", "money laundering", "反洗钱", "洗钱"]),
            ("enforcement", ["fine", "penalty", "disciplinary", "reprimand", "罚款", "处分"]),
            ("market conduct", ["market", "trading", "disclosure", "市场", "交易", "披露"]),
            ("licensing", ["license", "licensing", "牌照", "持牌"]),
        ]
        category = "general compliance"
        for label, keywords in rules:
            if any(keyword in business_text.lower() for keyword in keywords):
                category = label
                break
        risk = "high" if category in {"enforcement", "aml"} else "medium"
        summary = self._summarize(business_text)
        return json.dumps({"category": category, "risk_level": risk, "summary": summary}, ensure_ascii=False)

    def _extract_jsonish(self, text: str) -> str:
        return json.dumps({"summary": self._summarize(text)}, ensure_ascii=False)


class HybridLLM(BaseLLM):
    def __init__(self, settings: Settings) -> None:
        self.local = LocalHeuristicLLM()
        self.remote: OpenAIResponsesClient | None = None
        if settings.openai_api_key:
            self.remote = OpenAIResponsesClient(settings)

    def complete(self, system: str, user: str) -> LLMResponse:
        if self.remote:
            try:
                return self.remote.complete(system, user)
            except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
                pass
        return self.local.complete(system, user)


def _extract_response_text(data: dict) -> str:
    chunks: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                chunks.append(content.get("text", ""))
    return "\n".join(chunks)


def _extract_business_text(prompt: str) -> str:
    marker = "Title:"
    if marker in prompt:
        return prompt[prompt.index(marker) :]
    return prompt
