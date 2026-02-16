"""Draft order generation engine (draft-only, no execution)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from codex_invest.core.ingest import CashSnapshot, PositionSnapshot
from codex_invest.core.policy import PolicyConfig


@dataclass(frozen=True)
class OrderDraft:
    """Order draft payload."""

    side: str
    symbol: str
    qty: float
    est_amount: float
    rationale: str
    flags: tuple[str, ...]


class DraftOrderError(ValueError):
    """Raised when draft order generation input is invalid."""


@dataclass(frozen=True)
class _AssetState:
    symbol: str
    qty: float
    value: float
    price: float | None


@dataclass(frozen=True)
class _BuyCandidate:
    symbol: str
    gap_to_target: float


def _load_parquet_rows(path: Path) -> list[dict[str, object]]:
    import pyarrow.parquet as pq

    table = pq.read_table(path)
    return table.to_pylist()


def load_snapshots(
    positions_path: Path,
    cash_path: Path,
) -> tuple[list[PositionSnapshot], list[CashSnapshot]]:
    """Load normalized snapshots from parquet files."""
    position_rows = _load_parquet_rows(positions_path)
    cash_rows = _load_parquet_rows(cash_path)

    positions = [
        PositionSnapshot(
            account_id=str(row["account_id"]),
            account_type=str(row["account_type"]),
            symbol=str(row["symbol"]),
            name=str(row["name"]),
            qty=float(row["qty"]),
            currency=str(row["currency"]),
            price=float(row["price"]) if row["price"] is not None else None,
            value=float(row["value"]) if row["value"] is not None else None,
        )
        for row in position_rows
    ]
    cash = [
        CashSnapshot(
            account_id=str(row["account_id"]),
            account_type=str(row["account_type"]),
            currency=str(row["currency"]),
            amount=float(row["amount"]),
        )
        for row in cash_rows
    ]
    return positions, cash


def _aggregate_assets(positions: list[PositionSnapshot]) -> dict[str, _AssetState]:
    assets: dict[str, _AssetState] = {}
    for item in positions:
        symbol = item.symbol.upper()
        value = item.value
        if value is None:
            value = item.qty * item.price if item.price else 0.0
        price = item.price
        prev = assets.get(symbol)
        if prev is None:
            assets[symbol] = _AssetState(symbol=symbol, qty=item.qty, value=value, price=price)
            continue
        assets[symbol] = _AssetState(
            symbol=symbol,
            qty=prev.qty + item.qty,
            value=prev.value + value,
            price=prev.price if prev.price is not None else price,
        )
    return assets


def _round_qty(raw_qty: float, lot_size: float) -> float:
    return float(int(raw_qty / lot_size) * lot_size)


def _calc_est_amount(qty: float, price: float) -> float:
    return round(qty * price, 2)


def generate_order_drafts(
    positions: list[PositionSnapshot],
    cash: list[CashSnapshot],
    policy: PolicyConfig,
) -> list[OrderDraft]:
    """Generate BUY/SELL order drafts from snapshots and policy."""
    if not policy.asset_policies:
        raise DraftOrderError("policy.asset_policies must be configured for draft-order generation")

    asset_states = _aggregate_assets(positions)
    cash_available = sum(item.amount for item in cash)
    positions_total_value = sum(state.value for state in asset_states.values())
    portfolio_total = positions_total_value + cash_available

    if portfolio_total <= 0:
        return []

    settings = policy.draft_order_settings
    lot_size = settings.lot_size
    min_order_amount = settings.min_order_amount
    blocked_symbols = {symbol.upper() for symbol in settings.blocked_symbols}

    drafts: list[OrderDraft] = []
    allocated_buy: dict[str, float] = {}

    buy_candidates: list[_BuyCandidate] = []
    for asset_policy in policy.asset_policies:
        symbol = asset_policy.symbol.upper()
        current_value = asset_states.get(symbol, _AssetState(symbol, 0.0, 0.0, None)).value
        target_value = portfolio_total * asset_policy.target_weight
        gap_to_target = max(0.0, target_value - current_value)
        if gap_to_target > 0:
            buy_candidates.append(_BuyCandidate(symbol=symbol, gap_to_target=gap_to_target))

    buy_candidates.sort(key=lambda item: item.gap_to_target, reverse=True)

    for candidate in buy_candidates:
        if cash_available <= 0:
            break
        if candidate.symbol in blocked_symbols:
            drafts.append(
                OrderDraft(
                    side="BUY",
                    symbol=candidate.symbol,
                    qty=0.0,
                    est_amount=0.0,
                    rationale="Skipped underweight buy due to policy constraint.",
                    flags=("BLOCKED_SYMBOL",),
                )
            )
            continue

        state = asset_states.get(candidate.symbol, _AssetState(candidate.symbol, 0.0, 0.0, None))
        if state.price is None or state.price <= 0:
            drafts.append(
                OrderDraft(
                    side="BUY",
                    symbol=candidate.symbol,
                    qty=0.0,
                    est_amount=0.0,
                    rationale="Skipped underweight buy because price is unavailable.",
                    flags=("MISSING_PRICE",),
                )
            )
            continue

        buy_budget = min(cash_available, candidate.gap_to_target)
        raw_qty = buy_budget / state.price
        qty = _round_qty(raw_qty=raw_qty, lot_size=lot_size)
        if qty <= 0:
            continue
        est_amount = _calc_est_amount(qty=qty, price=state.price)
        if est_amount < min_order_amount:
            drafts.append(
                OrderDraft(
                    side="BUY",
                    symbol=candidate.symbol,
                    qty=0.0,
                    est_amount=0.0,
                    rationale="Skipped underweight buy because order amount is below minimum.",
                    flags=("MIN_ORDER_NOTIONAL",),
                )
            )
            continue

        drafts.append(
            OrderDraft(
                side="BUY",
                symbol=candidate.symbol,
                qty=qty,
                est_amount=est_amount,
                rationale="Allocate available cash to underweight target first.",
                flags=(),
            )
        )
        cash_available -= est_amount
        allocated_buy[candidate.symbol] = allocated_buy.get(candidate.symbol, 0.0) + est_amount

    post_buy_values = {
        symbol: state.value + allocated_buy.get(symbol, 0.0)
        for symbol, state in asset_states.items()
    }
    for asset_policy in policy.asset_policies:
        symbol = asset_policy.symbol.upper()
        post_buy_values.setdefault(symbol, allocated_buy.get(symbol, 0.0))

    for asset_policy in policy.asset_policies:
        symbol = asset_policy.symbol.upper()
        if symbol in blocked_symbols:
            continue
        state = asset_states.get(symbol)
        if state is None or state.qty <= 0 or state.price is None or state.price <= 0:
            continue

        current_weight = post_buy_values.get(symbol, 0.0) / portfolio_total
        if current_weight <= asset_policy.band.max:
            continue

        max_allowed_value = portfolio_total * asset_policy.band.max
        excess_value = post_buy_values[symbol] - max_allowed_value
        raw_qty = excess_value / state.price
        qty = min(state.qty, _round_qty(raw_qty=raw_qty, lot_size=lot_size))
        if qty <= 0:
            continue
        est_amount = _calc_est_amount(qty=qty, price=state.price)
        if est_amount < min_order_amount:
            continue

        drafts.append(
            OrderDraft(
                side="SELL",
                symbol=symbol,
                qty=qty,
                est_amount=est_amount,
                rationale="Sell only the excess above configured weight band.",
                flags=(),
            )
        )

    return drafts


def write_order_drafts(
    drafts: list[OrderDraft],
    asof: date,
    out_dir: Path,
) -> Path:
    """Write order drafts into a deterministic JSON artifact."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"order_drafts_{asof:%Y%m%d}.json"
    payload = {
        "asof": asof.isoformat(),
        "order_drafts": [asdict(item) for item in drafts],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
