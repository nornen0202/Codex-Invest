# Codex-Invest SPEC (Stage 6)

## 1. 목표
Codex-Invest는 개인 투자 운영을 위한 **안전한 의사결정 지원 시스템**이다.
시스템의 역할은 데이터 정리, 정책 적용, 주문 **초안** 생성이며, 실제 주문 실행은 범위 밖이다.

## 2. 범위 정의
### 포함
- 보유종목 데이터 ingest
- 정책 파일 기반 포트폴리오 분석
- 리밸런싱 및 신규매수 계산
- 초안 주문 파일 생성(JSON/XLSX/TXT)
- BankSalad 엑셀 기반 월별 현금흐름/순자산 리포트 생성(Markdown/CSV)

### 제외 (영구 금지)
- 브로커 자동주문 실행
- 계정 로그인 자동화
- 비공식 API 호출/스크래핑
- 투자자문(확정 매수/매도 추천)

## 3. 데이터 모델
### PolicyConfig
- `version: int`
- `base_currency: str`
- `risk_profile: str`
- `account_policies: list[AccountPolicy]`
- `asset_policies: list[AssetPolicy]`
- `draft_order_settings: DraftOrderSettings`

### AssetPolicy
- `symbol: str`
- `target_weight: float` (0~1)
- `band.min: float` (0~1)
- `band.max: float` (0~1, min 이상)

### DraftOrderSettings
- `relative_band_tolerance: float` (0 이상, 예: 0.2 = 목표비중 ±20%)
- `min_order_amount: float` (0 이상)
- `lot_size: float` (>0)
- `blocked_symbols: list[str]`

### PositionsSnapshotRow
- `account_id: str`
- `account_type: str` (`taxable` | `irp` | `pension`)
- `symbol: str`
- `name: str`
- `qty: float`
- `currency: str`
- `price: float | None`
- `value: float | None` (없으면 `qty * price` 계산)

### CashSnapshotRow
- `account_id: str`
- `account_type: str` (`taxable` | `irp` | `pension`)
- `currency: str`
- `amount: float`

### OrderDraft
- `account_id: str`
- `side: "BUY" | "SELL"`
- `symbol: str`
- `qty: float`
- `est_amount: float`
- `rationale: str`
- `flags: list[str]`

### MonthlyFinanceSnapshot (BankSalad)
- `month: date` (월 기준, 매월 1일로 정규화)
- `income: float | None`
- `expense: float | None`
- `net_cashflow: float | None` (없으면 `income - expense`)
- `net_worth: float | None`

### CashflowReportRow
- `month: str` (`YYYY-MM`)
- `net_cashflow: float | None`
- `net_worth: float | None`
- `investable_cash_estimate: float` (`max(net_cashflow, 0)`)
- `routine_status: "ON_TRACK" | "BELOW_ROUTINE" | "INSUFFICIENT_HISTORY"`

## 4. 주문 초안 엔진 규칙
1. 신규자금(현금)을 우선 사용해 목표 대비 부족 자산을 채운다.
2. 그래도 밴드 상단을 초과한 자산만 최소 매도로 줄인다.
3. 제약 위반 주문은 생성하지 않는다(금지 심볼, 최소 주문금액 미달, 가격 부재 등).

## 5. CLI 워크플로
1. `init`: 로컬 템플릿 파일 생성/검증
2. `ingest --input <.xlsx/.csv> --out <dir>`: 표준 스냅샷 parquet 변환
3. `analyze`: 정책 위반/리밸런싱 필요량 계산 (스캐폴드)
4. `draft-orders --asof YYYY-MM-DD --policy policy/policy.yml [--positions ... --cash ...]`: 주문 초안 생성
5. `report cashflow --input <banksalad.xlsx> [--format markdown|csv] [--out ...]`: 월별 현금흐름/순자산 리포트 생성

## 6. 출력 포맷
기본 출력 경로: `data/output/`

파일명:
- `order_drafts_YYYYMMDD.json`
- `order_draft.xlsx`
- `order_draft.txt`
- `cashflow_report.md` 또는 `cashflow_report.csv`

JSON 구조:
- `asof`
- `order_drafts[]` (`account_id`, `side`, `symbol`, `qty`, `est_amount`, `rationale`, `flags`)

XLSX 구조:
- `SUMMARY`: 계좌별 현재/목표/편차/제약 위반 경고
- `ACCOUNT_<id>`: 계좌별 주문 리스트 + 복붙용 텍스트 라인

TXT 구조:
- 계좌별 섹션(`[ACCOUNT_<id>]`) 아래 `SYMBOL BUY|SELL QTY` 라인


Cashflow Markdown 구조:
- 헤더: `month`, `net_cashflow`, `net_worth`, `investable_cash_estimate`, `routine_status`
- `routine_status`는 월별 투자 가능 현금이 과거 양수 현금흐름 중앙값의 80% 이상인지로 판정

Cashflow CSV 구조:
- 컬럼: `month,net_cashflow,net_worth,investable_cash_estimate,routine_status`

## 7. 비기능 요구사항
- Python 3.11+
- 테스트 가능 구조(도메인 로직은 core 모듈에 집중)
- 재현성(입력이 같으면 출력 동일)
- 안전성(자동주문/자문 기능 금지)
