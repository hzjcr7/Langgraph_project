from __future__ import annotations

import json
import re
from pathlib import Path

from openpyxl import Workbook

from ..schemas import BankStatement, Transaction


FIELD_PATTERNS = {
    "account_name": re.compile(r"Account Name\s*:\s*(.+)", re.I),
    "account_no": re.compile(r"Account No\.?\s*:\s*([A-Z0-9\-]+)", re.I),
    "period": re.compile(r"Period\s*:\s*(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})", re.I),
    "opening_balance": re.compile(r"Opening Balance\s*:\s*([\-0-9,.]+)", re.I),
    "closing_balance": re.compile(r"Closing Balance\s*:\s*([\-0-9,.]+)", re.I),
}

TRANSACTION_PATTERN = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})\s+\|\s+(?P<desc>[^|]+)\|\s+(?P<currency>[A-Z]{3})\s+(?P<amount>[\-0-9,.]+)",
    re.I,
)


def extract_bank_statement(text: str) -> BankStatement:
    warnings: list[str] = []

    def find_field(name: str, default: str = "") -> str:
        match = FIELD_PATTERNS[name].search(text)
        if not match:
            warnings.append(f"Missing field: {name}")
            return default
        return match.group(1).strip()

    period_match = FIELD_PATTERNS["period"].search(text)
    if period_match:
        period_start, period_end = period_match.group(1), period_match.group(2)
    else:
        warnings.append("Missing field: period")
        period_start, period_end = "", ""

    transactions = [
        Transaction(
            trade_date=match.group("date"),
            description=match.group("desc").strip(),
            currency=match.group("currency"),
            amount=_to_float(match.group("amount")),
            category=_categorize_transaction(match.group("desc")),
            risk_flags=_transaction_risk_flags(match.group("desc"), _to_float(match.group("amount"))),
        )
        for match in TRANSACTION_PATTERN.finditer(text)
    ]
    if not transactions:
        warnings.append("No transactions extracted")

    statement = BankStatement(
        account_name=find_field("account_name"),
        account_no=find_field("account_no"),
        period_start=period_start,
        period_end=period_end,
        opening_balance=_to_float(find_field("opening_balance", "0")),
        closing_balance=_to_float(find_field("closing_balance", "0")),
        transactions=transactions,
        warnings=warnings,
    )
    statement.extraction_confidence = _estimate_confidence(statement)
    return statement


def validate_statement(statement: BankStatement) -> list[str]:
    warnings = list(statement.warnings)
    net_flow = sum(item.amount for item in statement.transactions)
    expected_closing = round(statement.opening_balance + net_flow, 2)
    actual_closing = round(statement.closing_balance, 2)
    if abs(expected_closing - actual_closing) > 0.01:
        warnings.append(
            f"Balance mismatch: opening + transactions = {expected_closing}, closing = {actual_closing}"
        )
    for tx in statement.transactions:
        if abs(tx.amount) >= 500000:
            warnings.append(f"Large transaction requires review: {tx.trade_date} {tx.description} {tx.amount}")
    return warnings


def write_statement_excel(statement: BankStatement, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    ws = workbook.active
    ws.title = "Bank Statement"

    rows = [
        ("Account Name", statement.account_name),
        ("Account No", statement.account_no),
        ("Period", f"{statement.period_start} to {statement.period_end}"),
        ("Opening Balance", statement.opening_balance),
        ("Closing Balance", statement.closing_balance),
        ("Extraction Confidence", statement.extraction_confidence),
    ]
    for row in rows:
        ws.append(row)

    ws.append([])
    ws.append(["Date", "Description", "Currency", "Amount", "Category", "Risk Flags"])
    for tx in statement.transactions:
        ws.append([tx.trade_date, tx.description, tx.currency, tx.amount, tx.category, ", ".join(tx.risk_flags)])

    ws.append([])
    ws.append(["Validation Warnings"])
    for warning in validate_statement(statement):
        ws.append([warning])

    for column in "ABCDEF":
        ws.column_dimensions[column].width = 24
    workbook.save(path)
    return path


def write_statement_json(statement: BankStatement, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(statement.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _to_float(value: str) -> float:
    return float(value.replace(",", "").strip())


def _categorize_transaction(description: str) -> str:
    lowered = description.lower()
    if any(word in lowered for word in ["subscription", "fee", "service"]):
        return "service_fee"
    if any(word in lowered for word in ["salary", "payroll"]):
        return "payroll"
    if any(word in lowered for word in ["transfer", "settlement"]):
        return "transfer"
    if any(word in lowered for word in ["interest", "dividend"]):
        return "income"
    return "other"


def _transaction_risk_flags(description: str, amount: float) -> list[str]:
    lowered = description.lower()
    flags: list[str] = []
    if abs(amount) >= 500000:
        flags.append("large_amount")
    if any(word in lowered for word in ["cash", "third party", "offshore", "crypto"]):
        flags.append("enhanced_due_diligence")
    if amount < 0 and any(word in lowered for word in ["custody", "external"]):
        flags.append("asset_transfer_review")
    return flags


def _estimate_confidence(statement: BankStatement) -> float:
    checks = [
        bool(statement.account_name),
        bool(statement.account_no),
        bool(statement.period_start and statement.period_end),
        len(statement.transactions) > 0,
        not validate_statement(statement),
    ]
    return round(sum(checks) / len(checks), 2)
