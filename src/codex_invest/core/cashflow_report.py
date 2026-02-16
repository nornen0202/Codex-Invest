"""Cashflow reporting utilities."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from codex_invest.connectors.banksalad_xlsx import MonthlyFinanceSnapshot


@dataclass(frozen=True)
class CashflowReportRow:
    """Monthly cashflow report row."""

    month: str
    net_cashflow: float | None
    net_worth: float | None
    investable_cash_estimate: float
    routine_status: str


def _baseline_investable_cash(rows: list[MonthlyFinanceSnapshot]) -> float | None:
    positive_values = sorted(
        max(item.net_cashflow or 0.0, 0.0)
        for item in rows
        if item.net_cashflow is not None and item.month
    )
    if not positive_values:
        return None

    middle = len(positive_values) // 2
    if len(positive_values) % 2 == 1:
        return positive_values[middle]
    return (positive_values[middle - 1] + positive_values[middle]) / 2


def build_cashflow_report(rows: list[MonthlyFinanceSnapshot]) -> list[CashflowReportRow]:
    """Build monthly cashflow trend report rows."""
    baseline = _baseline_investable_cash(rows)
    report_rows: list[CashflowReportRow] = []

    for item in rows:
        investable_cash_estimate = max(item.net_cashflow or 0.0, 0.0)
        if baseline is None or baseline == 0:
            routine_status = "INSUFFICIENT_HISTORY"
        elif investable_cash_estimate >= baseline * 0.8:
            routine_status = "ON_TRACK"
        else:
            routine_status = "BELOW_ROUTINE"

        report_rows.append(
            CashflowReportRow(
                month=item.month.isoformat()[:7],
                net_cashflow=item.net_cashflow,
                net_worth=item.net_worth,
                investable_cash_estimate=investable_cash_estimate,
                routine_status=routine_status,
            )
        )

    return report_rows


def _fmt_number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:,.0f}"


def render_cashflow_markdown(rows: list[CashflowReportRow]) -> str:
    """Render report rows into markdown table."""
    lines = [
        "# Cashflow Report",
        "",
        "| month | net_cashflow | net_worth | investable_cash_estimate | routine_status |",
        "|---|---:|---:|---:|---|",
    ]

    for row in rows:
        lines.append(
            "| "
            f"{row.month} | {_fmt_number(row.net_cashflow)} | {_fmt_number(row.net_worth)} | "
            f"{_fmt_number(row.investable_cash_estimate)} | {row.routine_status} |"
        )

    return "\n".join(lines) + "\n"


def write_cashflow_csv(rows: list[CashflowReportRow], out_path: Path) -> Path:
    """Write report rows into CSV file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "month",
                "net_cashflow",
                "net_worth",
                "investable_cash_estimate",
                "routine_status",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "month": row.month,
                    "net_cashflow": row.net_cashflow,
                    "net_worth": row.net_worth,
                    "investable_cash_estimate": row.investable_cash_estimate,
                    "routine_status": row.routine_status,
                }
            )
    return out_path


def write_cashflow_markdown(rows: list[CashflowReportRow], out_path: Path) -> Path:
    """Write markdown report file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_cashflow_markdown(rows), encoding="utf-8")
    return out_path
