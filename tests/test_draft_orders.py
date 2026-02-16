"""Draft order generation tests."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from codex_invest.cli import main
from codex_invest.core.draft_orders import (
    DraftOrderError,
    generate_order_drafts,
    write_order_drafts,
)
from codex_invest.core.ingest import CashSnapshot, PositionSnapshot
from codex_invest.core.policy import load_policy_config


def _policy_file(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "policy.yml"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _base_policy() -> dict[str, object]:
    return {
        "version": 2,
        "base_currency": "USD",
        "risk_profile": "balanced",
        "account_policies": [],
        "draft_order": {
            "relative_band_tolerance": 0.2,
            "min_order_amount": 0,
            "lot_size": 1,
            "blocked_symbols": [],
        },
        "asset_policies": [
            {"symbol": "AAA", "target_weight": 0.6},
            {"symbol": "BBB", "target_weight": 0.4},
        ],
    }


def test_cash_only_buys_underweight_first(tmp_path: Path) -> None:
    policy = load_policy_config(_policy_file(tmp_path, _base_policy()))
    positions = [
        PositionSnapshot("A", "taxable", "AAA", "AAA", 3, "USD", 100, 300),
        PositionSnapshot("A", "taxable", "BBB", "BBB", 4, "USD", 100, 400),
    ]
    cash = [CashSnapshot("A", "taxable", "USD", 300)]

    drafts = generate_order_drafts(positions, cash, policy)

    assert drafts[0].side == "BUY"
    assert drafts[0].symbol == "AAA"
    assert drafts[0].qty == 3


def test_sell_is_generated_when_still_above_band(tmp_path: Path) -> None:
    policy_raw = _base_policy()
    policy_raw["asset_policies"] = [
        {"symbol": "AAA", "target_weight": 0.5, "band": {"min": 0.45, "max": 0.55}}
    ]
    policy = load_policy_config(_policy_file(tmp_path, policy_raw))

    positions = [PositionSnapshot("A", "taxable", "AAA", "AAA", 10, "USD", 100, 1000)]
    cash = [CashSnapshot("A", "taxable", "USD", 0)]

    drafts = generate_order_drafts(positions, cash, policy)

    assert len(drafts) == 1
    assert drafts[0].side == "SELL"
    assert drafts[0].qty == 4


def test_blocked_symbol_buy_is_not_generated(tmp_path: Path) -> None:
    policy_raw = _base_policy()
    policy_raw["draft_order"]["blocked_symbols"] = ["AAA"]
    policy_raw["asset_policies"] = [{"symbol": "AAA", "target_weight": 1.0}]
    policy = load_policy_config(_policy_file(tmp_path, policy_raw))

    positions = [PositionSnapshot("A", "taxable", "AAA", "AAA", 1, "USD", 100, 100)]
    cash = [CashSnapshot("A", "taxable", "USD", 100)]

    drafts = generate_order_drafts(positions, cash, policy)

    assert drafts[0].symbol == "AAA"
    assert drafts[0].qty == 0
    assert "BLOCKED_SYMBOL" in drafts[0].flags


def test_missing_price_prevents_buy(tmp_path: Path) -> None:
    policy = load_policy_config(_policy_file(tmp_path, _base_policy()))

    positions = [PositionSnapshot("A", "taxable", "AAA", "AAA", 1, "USD", None, 100)]
    cash = [CashSnapshot("A", "taxable", "USD", 50)]

    drafts = generate_order_drafts(positions, cash, policy)

    assert drafts[0].qty == 0
    assert "MISSING_PRICE" in drafts[0].flags


def test_min_order_amount_blocks_tiny_order(tmp_path: Path) -> None:
    policy_raw = _base_policy()
    policy_raw["draft_order"]["min_order_amount"] = 200
    policy_raw["asset_policies"] = [{"symbol": "AAA", "target_weight": 1.0}]
    policy = load_policy_config(_policy_file(tmp_path, policy_raw))

    positions = [PositionSnapshot("A", "taxable", "AAA", "AAA", 4.9, "USD", 100, 490)]
    cash = [CashSnapshot("A", "taxable", "USD", 150)]

    drafts = generate_order_drafts(positions, cash, policy)

    assert drafts[0].qty == 0
    assert "MIN_ORDER_NOTIONAL" in drafts[0].flags


def test_lot_size_rounding_applies(tmp_path: Path) -> None:
    policy_raw = _base_policy()
    policy_raw["draft_order"]["lot_size"] = 10
    policy_raw["asset_policies"] = [{"symbol": "AAA", "target_weight": 1.0}]
    policy = load_policy_config(_policy_file(tmp_path, policy_raw))

    positions = [PositionSnapshot("A", "taxable", "AAA", "AAA", 0, "USD", 10, 0)]
    cash = [CashSnapshot("A", "taxable", "USD", 95)]

    drafts = generate_order_drafts(positions, cash, policy)

    assert drafts == []


def test_raises_when_asset_policy_missing(tmp_path: Path) -> None:
    policy_raw = _base_policy()
    policy_raw["asset_policies"] = []
    policy = load_policy_config(_policy_file(tmp_path, policy_raw))

    with pytest.raises(DraftOrderError):
        generate_order_drafts([], [], policy)


def test_write_order_drafts_json(tmp_path: Path) -> None:
    out_path = write_order_drafts([], asof=date(2026, 1, 1), out_dir=tmp_path)
    assert out_path.exists()


def test_cli_draft_orders_end_to_end(tmp_path: Path) -> None:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")

    policy_path = _policy_file(tmp_path, _base_policy())
    positions_path = tmp_path / "positions_snapshot.parquet"
    cash_path = tmp_path / "cash_snapshot.parquet"

    positions_table = pa.Table.from_pylist(
        [
            {
                "account_id": "A",
                "account_type": "taxable",
                "symbol": "AAA",
                "name": "AAA",
                "qty": 3.0,
                "currency": "USD",
                "price": 100.0,
                "value": 300.0,
            }
        ]
    )
    cash_table = pa.Table.from_pylist(
        [{"account_id": "A", "account_type": "taxable", "currency": "USD", "amount": 100.0}]
    )
    pq.write_table(positions_table, positions_path)
    pq.write_table(cash_table, cash_path)

    exit_code = main(
        [
            "draft-orders",
            "--asof",
            "2026-01-01",
            "--policy",
            str(policy_path),
            "--positions",
            str(positions_path),
            "--cash",
            str(cash_path),
            "--out",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "order_drafts_20260101.json").exists()
