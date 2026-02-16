# Codex-Invest

Codex-Invest는 개인 투자 운영 시스템(Invest OS)을 위한 Python 기반 CLI 프로젝트입니다.
현재 단계에서는 **자동 주문 없이**, 보유종목/정책 분석을 거쳐 **주문 초안(draft orders)** 생성 워크플로를 위한 스캐폴딩을 제공합니다.

## 핵심 원칙
- 자동 주문 실행 금지 (draft only)
- 민감정보(계좌번호, 실명, 주민번호, 원본 거래내역) 커밋 금지
- 계산/검증/초안 생성 중심 (투자자문 기능 제외)

## 요구 환경
- Python 3.11+
- pip

## 설치
```bash
python -m pip install -e .
```

개발 도구까지 함께 설치하려면:
```bash
python -m pip install -e .[dev]
```

## CLI 사용
도움말:
```bash
python -m codex_invest --help
```

플레이스홀더 명령:
```bash
python -m codex_invest init
python -m codex_invest ingest
python -m codex_invest analyze
python -m codex_invest draft-orders
```

현재 명령들은 스캐폴딩 상태이며, 다음 단계에서 실제 도메인 로직(보유종목 import, 정책 검증, 주문초안 생성)을 구현합니다.

## 디렉토리 구조
```text
src/codex_invest/           # 패키지 루트
src/codex_invest/core/      # 정책/포트폴리오/리밸런싱 엔진 예정
src/codex_invest/connectors/# banksalad/broker importer 예정
policy/                     # 정책/계정 템플릿 (샘플)
data/raw/                   # 원본 입력 파일 위치(로컬 전용)
data/output/                # 산출물 위치(로컬 전용)
tests/                      # 테스트
.github/workflows/          # CI
```


## 정책 파일 수정 가이드
정책 관련 파일은 `policy/` 아래 3개 템플릿을 복사해 사용합니다. 현재 로더는 JSON 호환 YAML(예: JSON 문법) 형식을 사용합니다.

- `policy/policy.example.yml`: 계좌별 목표 비중(`target_weight`)과 허용 밴드(`band.min/max`)
- `policy/accounts.example.yml`: 계좌 별칭/브로커/통화/계좌유형
- `policy/restrictions.example.yml`: 계좌별 위험자산 상한과 금지 종목/키워드

예시 (`policy/restrictions.yml`):
```yaml
{
  "version": 1,
  "restrictions": {
    "account_limits": [{"account_alias": "irp", "max_risk_asset_weight": 0.70}],
    "blocked_symbols": ["TQQQ", "SQQQ"],
    "blocked_keywords": ["레버리지", "인버스", "leverage", "inverse"]
  }
}
```

검증 로직은 다음 규칙을 검사합니다.
- 계좌별 위험자산 비중이 상한을 초과하는지
- 금지 종목 목록에 포함된 심볼인지
- 종목명에 금지 키워드가 포함되는지

## 품질 확인
```bash
python -m pytest
python -m ruff check .
```

## 다음 구현 예정
1. 보유종목 템플릿 ingest 파이프라인
2. `policy.yml` 기반 제약 검증
3. 리밸런싱/신규매수 계산
4. 주문 초안 엑셀 출력 (draft only)
