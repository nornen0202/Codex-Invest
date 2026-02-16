# AGENTS.md

## Purpose
This repository builds **Codex-Invest**, a personal investment operations system that supports
portfolio ingestion, policy evaluation, and **draft-order** generation only.

## Hard safety boundaries
- Never implement broker auto-order execution.
- Never implement login automation, credential replay, or web scraping for broker accounts.
- Never provide investment advice, recommendations, or “final buy/sell decisions.”
- Never commit sensitive personal data (real names, account numbers, resident IDs, raw broker exports).

## Data handling rules
- Keep raw/source files under `data/raw/` locally only.
- Keep generated artifacts under `data/output/` locally only.
- Use sanitized templates in `policy/` and docs.
- If sample data is required for tests, use synthetic non-identifying fixtures only.

## Engineering guardrails
- Target Python 3.11+.
- Keep dependencies minimal and explicit.
- Prefer pure functions in core logic for testability.
- CLI should remain deterministic and safe (no side effects by default).

## Quality gates
Before finalizing changes, run:
1. `python -m pip install -e .`
2. `python -m pytest`
3. `python -m ruff check .`

## Documentation expectations
- Update `README.md` for user-facing workflow changes.
- Update `SPEC.md` for domain model or output format changes.
- Update `SECURITY.md` for any new security-relevant behavior.
