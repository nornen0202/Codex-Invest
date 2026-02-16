"""Holdings importer tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from codex_invest.cli import main
from codex_invest.core.ingest import HoldingsImportError, normalize_snapshots, read_holdings_rows


@pytest.fixture
def holdings_xlsx(tmp_path: Path) -> Path:
    """Create synthetic holdings template workbook."""
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()

    path = tmp_path / "holdings_sample.xlsx"
    sheet = workbook.active
    sheet.append(
        [
            "account_id",
            "account_type",
            "symbol",
            "name",
            "qty",
            "currency",
            "price",
            "value",
        ]
    )
    sheet.append(["ACC-001", "taxable", "AAPL", "Apple", 3, "USD", 100, ""])
    sheet.append(["ACC-001", "taxable", "CASH", "Cash", 1, "USD", "", 1250])
    workbook.save(path)
    workbook.close()
    return path


def test_normalize_snapshots_splits_position_and_cash() -> None:
    """Cash rows should be emitted to cash snapshot only."""
    rows = [
        {
            "account_id": "ACC-1",
            "account_type": "taxable",
            "symbol": "VTI",
            "name": "Vanguard Total Stock Market",
            "qty": "2",
            "currency": "usd",
            "price": "110",
            "value": "",
        },
        {
            "account_id": "ACC-1",
            "account_type": "taxable",
            "symbol": "CASH",
            "name": "Cash",
            "qty": "1",
            "currency": "USD",
            "price": "",
            "value": "500",
        },
    ]

    positions, cash = normalize_snapshots(rows)

    assert len(positions) == 1
    assert positions[0].value == 220.0
    assert len(cash) == 1
    assert cash[0].amount == 500.0


def test_read_holdings_rows_requires_required_columns(tmp_path: Path) -> None:
    """Missing required columns should raise explicit import errors."""
    path = tmp_path / "invalid.csv"
    path.write_text("account_id,account_type\nACC-1,taxable\n", encoding="utf-8")

    with pytest.raises(HoldingsImportError):
        read_holdings_rows(path)


def test_cli_ingest_writes_parquet_snapshots(holdings_xlsx: Path, tmp_path: Path) -> None:
    """Ingest command should write standardized parquet snapshots."""
    pq = pytest.importorskip("pyarrow.parquet")

    out_dir = tmp_path / "staging"
    exit_code = main(["ingest", "--input", str(holdings_xlsx), "--out", str(out_dir)])

    assert exit_code == 0

    positions_table = pq.read_table(out_dir / "positions_snapshot.parquet")
    cash_table = pq.read_table(out_dir / "cash_snapshot.parquet")

    assert positions_table.num_rows == 1
    assert positions_table.column("symbol").to_pylist() == ["AAPL"]
    assert cash_table.num_rows == 1
    assert cash_table.column("amount").to_pylist() == [1250.0]
