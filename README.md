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
