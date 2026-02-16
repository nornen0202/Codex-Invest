"""BankSalad XLSX importer for monthly cashflow/net worth data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


class BankSaladImportError(ValueError):
    """Raised when BankSalad XLSX data cannot be parsed."""


@dataclass(frozen=True)
class MonthlyFinanceSnapshot:
    """Normalized monthly finance snapshot from BankSalad export."""

    month: date
    income: float | None
    expense: float | None
    net_cashflow: float | None
    net_worth: float | None


_HEADER_ALIASES: dict[str, set[str]] = {
    "month": {"month", "월", "기준월", "년월", "연월", "date"},
    "income": {"income", "수입", "입금", "총수입"},
    "expense": {"expense", "지출", "출금", "총지출"},
    "net_cashflow": {"net_cashflow", "순현금흐름", "순현금", "현금흐름", "cashflow"},
    "net_worth": {"net_worth", "순자산", "자산", "총자산", "순자산추이"},
}


def _normalize_label(value: object) -> str:
    text = str(value or "").strip().lower()
    return text.replace(" ", "").replace("_", "")


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    normalized = (
        text.replace(",", "")
        .replace("₩", "")
        .replace("원", "")
        .replace(" ", "")
        .replace("−", "-")
    )
    if normalized.startswith("(") and normalized.endswith(")"):
        normalized = f"-{normalized[1:-1]}"

    try:
        return float(normalized)
    except ValueError as exc:
        raise BankSaladImportError(f"숫자 파싱 실패: {value!r}") from exc


def _coerce_month(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return date(value.year, value.month, 1)
    if isinstance(value, date):
        return date(value.year, value.month, 1)

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace(".", "-").replace("/", "-")
    if len(normalized) == 7:
        normalized = f"{normalized}-01"
    if len(normalized) == 6 and normalized.isdigit():
        normalized = f"{normalized[:4]}-{normalized[4:]}-01"

    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            parsed = datetime.strptime(normalized, fmt)
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            continue

    raise BankSaladImportError(
        f"월 파싱 실패: {value!r}. 예시 형식: 2025-01, 2025.01, 202501"
    )


def _find_header_mapping(sheet: object) -> tuple[int, dict[str, int]] | None:
    row_iter = sheet.iter_rows(min_row=1, max_row=30, values_only=True)
    for row_index, row in enumerate(row_iter, start=1):
        labels = [_normalize_label(item) for item in row]
        mapping: dict[str, int] = {}
        for key, aliases in _HEADER_ALIASES.items():
            for idx, label in enumerate(labels):
                if label and label in aliases:
                    mapping[key] = idx
                    break

        required_metrics = {"income", "expense", "net_cashflow", "net_worth"}
        if "month" in mapping and (required_metrics & mapping.keys()):
            return row_index, mapping
    return None


def import_banksalad_monthly_snapshots(path: Path) -> list[MonthlyFinanceSnapshot]:
    """Import monthly snapshots from a BankSalad XLSX export."""
    if path.suffix.lower() != ".xlsx":
        raise BankSaladImportError("BankSalad importer는 .xlsx 입력만 지원합니다.")

    try:
        from openpyxl import load_workbook
    except ModuleNotFoundError as exc:
        raise BankSaladImportError("openpyxl이 필요합니다. 먼저 의존성을 설치해 주세요.") from exc

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        for sheet in workbook.worksheets:
            header_info = _find_header_mapping(sheet)
            if header_info is None:
                continue

            header_row_index, mapping = header_info
            snapshots: list[MonthlyFinanceSnapshot] = []
            for row in sheet.iter_rows(min_row=header_row_index + 1, values_only=True):
                month_value = row[mapping["month"]] if mapping["month"] < len(row) else None
                month = _coerce_month(month_value)
                if month is None:
                    continue

                income = _coerce_float(row[mapping["income"]]) if "income" in mapping else None
                expense = _coerce_float(row[mapping["expense"]]) if "expense" in mapping else None
                net_cashflow = (
                    _coerce_float(row[mapping["net_cashflow"]])
                    if "net_cashflow" in mapping
                    else None
                )
                net_worth = (
                    _coerce_float(row[mapping["net_worth"]])
                    if "net_worth" in mapping
                    else None
                )

                if net_cashflow is None and income is not None and expense is not None:
                    net_cashflow = income - expense

                snapshots.append(
                    MonthlyFinanceSnapshot(
                        month=month,
                        income=income,
                        expense=expense,
                        net_cashflow=net_cashflow,
                        net_worth=net_worth,
                    )
                )

            if snapshots:
                snapshots.sort(key=lambda item: item.month)
                return snapshots

        raise BankSaladImportError(
            "BankSalad 월별 데이터 헤더를 찾지 못했습니다.\n"
            "가이드: 월/수입/지출/순현금흐름/순자산 중 최소 2개 컬럼이 포함된 시트를 사용하세요."
        )
    finally:
        workbook.close()
