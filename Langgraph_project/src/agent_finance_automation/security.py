from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


ACCOUNT_PATTERN = re.compile(r"\b([A-Z]{2}-)?\d{3,}[-\d]*\b")
URL_TOKEN_PATTERN = re.compile(r"([?&](token|key|secret)=)[^&\s]+", re.I)


@dataclass(frozen=True)
class SecurityPolicy:
    private_deployment: bool = True
    redact_account_numbers: bool = True
    redact_url_tokens: bool = True
    allow_remote_llm_for_sensitive_docs: bool = False
    max_document_chars: int = 120_000


def redact_sensitive_text(value: str) -> str:
    value = URL_TOKEN_PATTERN.sub(r"\1***", value)
    return ACCOUNT_PATTERN.sub(lambda match: _mask(match.group(0)), value)


def document_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def inspect_document_security(text: str, policy: SecurityPolicy | None = None) -> dict:
    policy = policy or SecurityPolicy()
    account_matches = ACCOUNT_PATTERN.findall(text)
    return {
        "fingerprint": document_fingerprint(text),
        "char_count": len(text),
        "contains_account_like_id": bool(account_matches),
        "within_size_limit": len(text) <= policy.max_document_chars,
        "remote_llm_allowed": policy.allow_remote_llm_for_sensitive_docs,
        "private_deployment": policy.private_deployment,
    }


def _mask(value: str) -> str:
    if len(value) <= 6:
        return "***"
    return f"{value[:2]}***{value[-2:]}"

