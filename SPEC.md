# Codex-Invest SPEC (Stage 1)

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

## 3. 데이터 모델(초안)
### HoldingsRecord
- `account_alias: str`
- `symbol: str`
- `asset_class: str`
- `quantity: float`
- `avg_cost: float | None`
- `market_price: float | None`
- `market_value: float | None`
- `currency: str`
- `as_of_date: date`

### PolicyConfig
- `base_currency: str`
- `risk_profile: str`
- `constraints.max_single_asset_weight: float`
- `constraints.min_cash_weight: float`
- `constraints.max_sector_weight: float`
- `rebalancing.threshold_bps: int`
- `execution.mode: "draft_only"`

### DraftOrder
- `account_alias: str`
- `symbol: str`
- `side: Literal["BUY", "SELL"]`
- `quantity: float`
- `order_type: Literal["MARKET", "LIMIT"]`
- `limit_price: float | None`
- `reason_code: str`
- `note: str`

## 4. 정책 파일 규약
- 위치: `policy/policy.yml` (실파일), `policy/policy.example.yml` (샘플)
- 형식: YAML
- 검증 항목:
  - 필수 키 존재
  - 값 범위(0~1 비중, threshold 양수)
  - `execution.allow_auto_order`는 항상 `false`

## 5. 계정 매핑 파일 규약
- 위치: `policy/accounts.yml` (실파일), `policy/accounts.example.yml` (샘플)
- 목적: 브로커/계좌별 ingest 포맷 매핑
- 민감정보 금지: 실계좌번호 저장 금지, 별칭(alias)만 사용

## 6. 주문 초안 출력 포맷(예정)
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

## 7. CLI 워크플로(예정)
1. `init`: 로컬 템플릿 파일 생성/검증
2. `ingest`: 보유종목 원본을 내부 표준 스키마로 변환
3. `analyze`: 정책 위반/리밸런싱 필요량 계산
4. `draft-orders`: 주문 초안 파일 생성

## 8. 비기능 요구사항
- Python 3.11+
- 테스트 가능 구조(도메인 로직은 core 모듈에 집중)
- 재현성(입력이 같으면 출력 동일)
- 안전성(자동주문/자문 기능 금지)
