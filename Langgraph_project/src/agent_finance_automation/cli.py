from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import DATA_DIR, get_settings
from .evaluation import run_evaluation
from .graph import FinanceAutomationGraph


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-agent finance office automation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bank = subparsers.add_parser("bank", help="Run bank statement automation")
    bank.add_argument("--input", default=str(DATA_DIR / "sample_bank_statement.txt"))

    regulatory = subparsers.add_parser("regulatory", help="Run regulatory digest automation")
    regulatory.add_argument("--input", default=str(DATA_DIR / "sample_regulatory_news.json"))

    subparsers.add_parser("eval", help="Run evaluation benchmark")
    subparsers.add_parser("demo", help="Run all workflows and evaluation")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    graph = FinanceAutomationGraph(settings)

    if args.command == "bank":
        result = graph.run_bank_statement(Path(args.input)).to_dict()
    elif args.command == "regulatory":
        result = graph.run_regulatory_digest(Path(args.input)).to_dict()
    elif args.command in {"eval", "demo"}:
        result = run_evaluation(settings)
    else:
        raise ValueError(args.command)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

