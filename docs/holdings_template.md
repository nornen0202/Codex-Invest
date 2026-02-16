# Holdings Template Columns

`ingest` 명령은 `.xlsx` 또는 `.csv` 파일을 받아 아래 표준 컬럼을 인식합니다.

| column | required | description |
|---|---|---|
| `account_id` | yes | 계좌 식별자(익명 ID 권장) |
| `account_type` | yes | `taxable`, `irp`, `pension` 중 하나 |
| `symbol` | yes (cash row는 `CASH` 권장) | 종목 심볼 |
| `name` | yes (cash row는 `Cash`/`현금` 허용) | 종목명 |
| `qty` | yes | 수량 |
| `currency` | yes | 통화 코드(예: `KRW`, `USD`) |
| `price` | optional | 단가 |
| `value` | optional | 평가금액 |

추가 규칙:
- `value`가 비어 있고 `qty`와 `price`가 있으면 `value = qty * price`로 계산됩니다.
- `symbol/name`이 현금 행으로 인식되면 `cash_snapshot`으로 분리됩니다.
- 일반 종목은 `positions_snapshot`으로 저장됩니다.
