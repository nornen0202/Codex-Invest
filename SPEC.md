# Codex-Invest SPEC (Stage 3)

## 1. 목표
Codex-Invest는 개인 투자 운영을 위한 **안전한 의사결정 지원 시스템**이다.
시스템의 역할은 데이터 정리, 정책 적용, 주문 **초안** 생성이며, 실제 주문 실행은 범위 밖이다.

## 2. 범위 정의
### 포함
- 보유종목 데이터 ingest
- 정책 파일 기반 포트폴리오 분석
- 리밸런싱 및 신규매수 계산
- 초안 주문 파일 생성

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

### AccountPolicy
- `alias: str`
- `target_weight: float` (0~1)
- `band.min: float` (0~1)
- `band.max: float` (0~1, min 이상)

### AccountsConfig
- `version: int`
- `accounts: list[AccountDefinition]`

### AccountDefinition
- `alias: str`
- `broker: str`
- `currency: str`
- `account_type: str`

### RestrictionsConfig
- `version: int`
- `restrictions.account_limits[].account_alias: str`
- `restrictions.account_limits[].max_risk_asset_weight: float` (0~1)
- `restrictions.blocked_symbols: list[str]`
- `restrictions.blocked_keywords: list[str]`

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


## 4. 정책 파일 규약
### 파일 위치
- `policy/policy.yml` (실파일)
- `policy/accounts.yml` (실파일)
- `policy/restrictions.yml` (실파일)
- `policy/*.example.yml` (샘플)

### 검증 항목
- 필수 키 존재
- 비중 값 범위(0~1)
- 밴드 유효성(`min <= target_weight <= max`)
- 계좌 alias 유일성
- 계좌별 위험자산 상한 위반 여부
- 금지 종목 및 금지 키워드 포함 여부

## 5. 주문 초안 출력 포맷(예정)
기본 출력 경로: `data/output/`

권장 파일명:
- `draft_orders_YYYYMMDD.xlsx`

시트 제안:
1. `orders`
   - account_alias, symbol, side, quantity, order_type, limit_price, reason_code, note
2. `summary`
   - before_weight, target_weight, delta_weight, estimated_cash_change
3. `validation`
   - policy_check_name, result, message

## 6. CLI 워크플로
1. `init`: 로컬 템플릿 파일 생성/검증
2. `ingest --input <.xlsx/.csv> --out <dir>`: 보유종목 원본을 내부 표준 스키마(`positions_snapshot`, `cash_snapshot`) parquet로 변환
3. `analyze`: 정책 위반/리밸런싱 필요량 계산
4. `draft-orders`: 주문 초안 파일 생성

## 7. 비기능 요구사항
- Python 3.11+
- 테스트 가능 구조(도메인 로직은 core 모듈에 집중)
- 재현성(입력이 같으면 출력 동일)
- 안전성(자동주문/자문 기능 금지)
