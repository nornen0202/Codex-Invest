"""Policy schema and restrictions validator tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from codex_invest.core.policy import (
    HoldingInput,
    PolicyValidationError,
    load_accounts_config,
    load_policy_config,
    load_restrictions_config,
    validate_restrictions,
)


def test_load_policy_example() -> None:
    """Policy example should parse into account policies."""
    config = load_policy_config(Path("policy/policy.example.yml"))

    assert config.version == 2
    assert len(config.account_policies) == 2
    assert config.account_policies[0].alias == "taxable_main"


def test_load_accounts_example() -> None:
    """Accounts example should parse with unique aliases."""
    config = load_accounts_config(Path("policy/accounts.example.yml"))

    assert config.version == 1
    assert {account.alias for account in config.accounts} == {"taxable_main", "irp"}


def test_invalid_band_raises_validation_error(tmp_path: Path) -> None:
    """Band min should not exceed max."""
    sample = tmp_path / "bad-policy.yml"
    sample.write_text(
        """
{
  "version": 2,
  "base_currency": "KRW",
  "risk_profile": "balanced",
  "account_policies": [
    {
      "alias": "irp",
      "target_weight": 0.5,
      "band": {"min": 0.7, "max": 0.6}
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(PolicyValidationError):
        load_policy_config(sample)


def test_validate_restrictions_detects_risk_limit_and_blocked_symbol() -> None:
    """Risk limit and blocked symbol violations should be reported."""
    restrictions = load_restrictions_config(Path("policy/restrictions.example.yml"))
    holdings = [
        HoldingInput(account_alias="irp", symbol="TQQQ", name="ProShares UltraPro QQQ"),
    ]
    violations = validate_restrictions(
        holdings=holdings,
        account_risk_weights={"irp": 0.8},
        restrictions=restrictions,
    )

    codes = {item.code for item in violations}
    assert "MAX_RISK_ASSET_WEIGHT_EXCEEDED" in codes
    assert "BLOCKED_SYMBOL" in codes


def test_validate_restrictions_detects_blocked_keyword() -> None:
    """Blocked keyword should trigger a violation."""
    restrictions = load_restrictions_config(Path("policy/restrictions.example.yml"))
    holdings = [
        HoldingInput(account_alias="taxable_main", symbol="KODEX-123", name="KODEX 인버스 2X"),
    ]

    violations = validate_restrictions(
        holdings=holdings,
        account_risk_weights={"taxable_main": 0.5},
        restrictions=restrictions,
    )

    assert len(violations) == 1
    assert violations[0].code == "BLOCKED_KEYWORD"


def test_validate_restrictions_passes_for_allowed_inputs() -> None:
    """No violations should be returned for policy-compliant holdings."""
    restrictions = load_restrictions_config(Path("policy/restrictions.example.yml"))
    holdings = [
        HoldingInput(
            account_alias="taxable_main",
            symbol="VTI",
            name="Vanguard Total Stock Market",
        ),
    ]

    violations = validate_restrictions(
        holdings=holdings,
        account_risk_weights={"taxable_main": 0.4, "irp": 0.6},
        restrictions=restrictions,
    )

    assert violations == []
