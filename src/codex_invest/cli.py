"""Command-line interface for Codex-Invest."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from codex_invest.core.draft_orders import (
    DraftOrderError,
    generate_order_drafts,
    load_snapshots,
    write_order_drafts,
)
from codex_invest.core.ingest import HoldingsImportError, import_holdings
from codex_invest.core.policy import PolicyValidationError, load_policy_config


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
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Import portfolio holdings from supported templates.",
    )
    ingest_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to holdings template file (.xlsx or .csv)",
    )
    ingest_parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output directory for normalized parquet snapshots",
    )
    subparsers.add_parser("analyze", help="Evaluate holdings against policy constraints.")

    draft_orders_parser = subparsers.add_parser(
        "draft-orders",
        help="Generate draft orders (no auto-trading).",
    )
    draft_orders_parser.add_argument("--asof", type=date.fromisoformat, required=True)
    draft_orders_parser.add_argument("--policy", type=Path, required=True)
    draft_orders_parser.add_argument(
        "--positions",
        type=Path,
        default=Path("data/output/positions_snapshot.parquet"),
    )
    draft_orders_parser.add_argument(
        "--cash",
        type=Path,
        default=Path("data/output/cash_snapshot.parquet"),
    )
    draft_orders_parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/output"),
        help="Output directory for order_drafts artifact.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Codex-Invest CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "ingest":
        try:
            positions_path, cash_path = import_holdings(input_path=args.input, out_dir=args.out)
        except HoldingsImportError as exc:
            parser.error(str(exc))
        print(f"positions_snapshot: {positions_path}")
        print(f"cash_snapshot: {cash_path}")
        return 0

    if args.command == "draft-orders":
        try:
            policy = load_policy_config(args.policy)
            positions, cash = load_snapshots(args.positions, args.cash)
            drafts = generate_order_drafts(positions=positions, cash=cash, policy=policy)
            out_path = write_order_drafts(drafts=drafts, asof=args.asof, out_dir=args.out)
        except (PolicyValidationError, DraftOrderError, FileNotFoundError, OSError) as exc:
            parser.error(str(exc))

        print(f"order_drafts: {out_path}")
        print(f"count: {len(drafts)}")
        return 0

    print(f"[{args.command}] command is scaffolded and not implemented yet.")
    return 0
