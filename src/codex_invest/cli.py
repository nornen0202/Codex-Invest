"""Command-line interface for Codex-Invest."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser with placeholder workflow commands."""
    parser = argparse.ArgumentParser(
        prog="codex-invest",
        description=(
            "Invest OS CLI: portfolio ingestion, policy analysis, and "
            "draft order generation."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    subparsers.add_parser("init", help="Initialize local project templates.")
    subparsers.add_parser("ingest", help="Import portfolio holdings from supported templates.")
    subparsers.add_parser("analyze", help="Evaluate holdings against policy constraints.")
    subparsers.add_parser("draft-orders", help="Generate draft orders (no auto-trading).")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Codex-Invest CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    print(f"[{args.command}] command is scaffolded and not implemented yet.")
    return 0
