"""BankSalad cashflow report tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from codex_invest.cli import main
from codex_invest.connectors.banksalad_xlsx import (
    BankSaladImportError,
    import_banksalad_monthly_snapshots,
)
from codex_invest.core.cashflow_report import build_cashflow_report


def _create_banksalad_sample_xlsx(path: Path) -> Path:
    """Create synthetic BankSalad-like workbook for tests."""
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "월별추이"
    sheet.append(["월", "수입", "지출", "순자산"])
    sheet.append(["2025-01", 3000000, 2100000, 50000000])
    sheet.append(["2025-02", 3200000, 2200000, 51200000])
    sheet.append(["2025-03", 2800000, 2300000, 51700000])
    workbook.save(path)
    workbook.close()
    return path


def test_import_banksalad_monthly_snapshots_reads_fixture(tmp_path: Path) -> None:
    """Fixture workbook should parse to normalized monthly rows."""
    fixture_path = _create_banksalad_sample_xlsx(tmp_path / "banksalad_sample.xlsx")
    snapshots = import_banksalad_monthly_snapshots(fixture_path)

    assert [item.month.isoformat()[:7] for item in snapshots] == ["2025-01", "2025-02", "2025-03"]
    assert snapshots[0].net_cashflow == 900000.0
    assert snapshots[-1].net_worth == 51700000.0


def test_import_banksalad_monthly_snapshots_gives_header_guidance(tmp_path: Path) -> None:
    """Unknown sheet format should raise a user-guiding parsing error."""
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["foo", "bar"])
    sheet.append(["a", "b"])
    path = tmp_path / "invalid.xlsx"
    workbook.save(path)
    workbook.close()

    with pytest.raises(BankSaladImportError, match="가이드"):
        import_banksalad_monthly_snapshots(path)


def test_build_cashflow_report_marks_below_routine(tmp_path: Path) -> None:
    """Rows below baseline should be tagged as BELOW_ROUTINE."""
    fixture_path = _create_banksalad_sample_xlsx(tmp_path / "banksalad_sample.xlsx")
    snapshots = import_banksalad_monthly_snapshots(fixture_path)
    report_rows = build_cashflow_report(snapshots)

    assert report_rows[0].routine_status == "ON_TRACK"
    assert report_rows[-1].routine_status == "BELOW_ROUTINE"


def test_cli_report_cashflow_writes_markdown(tmp_path: Path) -> None:
    """Cashflow report command should generate markdown output."""
    fixture_path = _create_banksalad_sample_xlsx(tmp_path / "banksalad_sample.xlsx")
    out_path = tmp_path / "cashflow_report.md"
    exit_code = main(
        [
            "report",
            "cashflow",
            "--input",
            str(fixture_path),
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    output = out_path.read_text(encoding="utf-8")
    assert "# Cashflow Report" in output
    assert "2025-02" in output
