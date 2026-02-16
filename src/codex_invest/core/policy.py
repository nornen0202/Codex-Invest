"""Policy schema loading and restriction validators."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PolicyValidationError(ValueError):
    """Raised when policy input data violates schema or constraints."""


@dataclass(frozen=True)
class WeightBand:
    """Target weight band where values are between 0 and 1."""

    min: float
    max: float

    def __post_init__(self) -> None:
        _validate_weight(self.min, "band.min")
        _validate_weight(self.max, "band.max")
        if self.min > self.max:
            raise PolicyValidationError("band.min must be <= band.max")


@dataclass(frozen=True)
class AccountPolicy:
    """Per-account target and tolerance band."""

    alias: str
    target_weight: float
    band: WeightBand

    def __post_init__(self) -> None:
        if not self.alias.strip():
            raise PolicyValidationError("account alias must be non-empty")
        _validate_weight(self.target_weight, f"account[{self.alias}].target_weight")
        if not self.band.min <= self.target_weight <= self.band.max:
            raise PolicyValidationError(
                f"account[{self.alias}].target_weight must be within configured band"
            )


@dataclass(frozen=True)
class PolicyConfig:
    """Portfolio-level policy configuration."""

    version: int
    base_currency: str
    risk_profile: str
    account_policies: tuple[AccountPolicy, ...]

    def __post_init__(self) -> None:
        if self.version < 1:
            raise PolicyValidationError("version must be >= 1")
        if not self.base_currency.strip():
            raise PolicyValidationError("base_currency must be non-empty")
        if not self.risk_profile.strip():
            raise PolicyValidationError("risk_profile must be non-empty")
        aliases = [policy.alias for policy in self.account_policies]
        if len(aliases) != len(set(aliases)):
            raise PolicyValidationError("account aliases must be unique")


@dataclass(frozen=True)
class AccountDefinition:
    """Sanitized account metadata for alias mapping."""

    alias: str
    broker: str
    currency: str
    account_type: str

    def __post_init__(self) -> None:
        if not self.alias.strip():
            raise PolicyValidationError("account alias must be non-empty")


@dataclass(frozen=True)
class AccountsConfig:
    """Account definition collection."""

    version: int
    accounts: tuple[AccountDefinition, ...]

    def __post_init__(self) -> None:
        aliases = [account.alias for account in self.accounts]
        if len(aliases) != len(set(aliases)):
            raise PolicyValidationError("account aliases in accounts config must be unique")


@dataclass(frozen=True)
class AccountRestriction:
    """Per-account risk asset limit."""

    account_alias: str
    max_risk_asset_weight: float

    def __post_init__(self) -> None:
        if not self.account_alias.strip():
            raise PolicyValidationError("account_alias must be non-empty")
        _validate_weight(
            self.max_risk_asset_weight,
            f"restriction[{self.account_alias}].max_risk_asset_weight",
        )


@dataclass(frozen=True)
class RestrictionsConfig:
    """Rule set used by restriction validator."""

    version: int
    account_limits: tuple[AccountRestriction, ...]
    blocked_symbols: tuple[str, ...]
    blocked_keywords: tuple[str, ...]


@dataclass(frozen=True)
class HoldingInput:
    """Minimal holding input needed for restriction validation."""

    account_alias: str
    symbol: str
    name: str


@dataclass(frozen=True)
class RestrictionViolation:
    """Constraint violation payload."""

    account_alias: str
    code: str
    message: str
    symbol: str | None = None


def _validate_weight(value: float, field_name: str) -> None:
    if not 0 <= value <= 1:
        raise PolicyValidationError(f"{field_name} must be between 0 and 1")


def _load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise PolicyValidationError(f"Expected mapping at root: {path}")
    return data


def load_policy_config(path: str | Path) -> PolicyConfig:
    """Load policy YAML and parse into PolicyConfig."""
    raw = _load_yaml(path)
    account_policies = tuple(
        AccountPolicy(
            alias=item["alias"],
            target_weight=float(item["target_weight"]),
            band=WeightBand(min=float(item["band"]["min"]), max=float(item["band"]["max"])),
        )
        for item in raw.get("account_policies", [])
    )
    return PolicyConfig(
        version=int(raw["version"]),
        base_currency=str(raw["base_currency"]),
        risk_profile=str(raw["risk_profile"]),
        account_policies=account_policies,
    )


def load_accounts_config(path: str | Path) -> AccountsConfig:
    """Load account YAML and parse into AccountsConfig."""
    raw = _load_yaml(path)
    accounts = tuple(
        AccountDefinition(
            alias=item["alias"],
            broker=item["broker"],
            currency=item["currency"],
            account_type=item["account_type"],
        )
        for item in raw.get("accounts", [])
    )
    return AccountsConfig(version=int(raw["version"]), accounts=accounts)


def load_restrictions_config(path: str | Path) -> RestrictionsConfig:
    """Load restrictions YAML and parse into RestrictionsConfig."""
    raw = _load_yaml(path)
    restrictions = raw.get("restrictions", {})
    account_limits = tuple(
        AccountRestriction(
            account_alias=item["account_alias"],
            max_risk_asset_weight=float(item["max_risk_asset_weight"]),
        )
        for item in restrictions.get("account_limits", [])
    )
    return RestrictionsConfig(
        version=int(raw["version"]),
        account_limits=account_limits,
        blocked_symbols=tuple(
            symbol.upper() for symbol in restrictions.get("blocked_symbols", [])
        ),
        blocked_keywords=tuple(
            keyword.casefold() for keyword in restrictions.get("blocked_keywords", [])
        ),
    )


def validate_restrictions(
    holdings: list[HoldingInput],
    account_risk_weights: dict[str, float],
    restrictions: RestrictionsConfig,
) -> list[RestrictionViolation]:
    """Validate account-level and instrument-level restrictions.

    Parameters are pure data structures so callers can unit-test deterministically.
    """
    violations: list[RestrictionViolation] = []

    for limit in restrictions.account_limits:
        weight = account_risk_weights.get(limit.account_alias)
        if weight is None:
            continue
        if weight > limit.max_risk_asset_weight:
            violations.append(
                RestrictionViolation(
                    account_alias=limit.account_alias,
                    code="MAX_RISK_ASSET_WEIGHT_EXCEEDED",
                    message=(
                        "risk asset weight exceeds account limit "
                        f"({weight:.2%} > {limit.max_risk_asset_weight:.2%})"
                    ),
                )
            )

    blocked_symbols = set(restrictions.blocked_symbols)
    for item in holdings:
        symbol = item.symbol.upper()
        if symbol in blocked_symbols:
            violations.append(
                RestrictionViolation(
                    account_alias=item.account_alias,
                    symbol=item.symbol,
                    code="BLOCKED_SYMBOL",
                    message=f"{item.symbol} is explicitly blocked by policy",
                )
            )
            continue

        lowered_name = item.name.casefold()
        keyword = next(
            (word for word in restrictions.blocked_keywords if word in lowered_name), None
        )
        if keyword:
            violations.append(
                RestrictionViolation(
                    account_alias=item.account_alias,
                    symbol=item.symbol,
                    code="BLOCKED_KEYWORD",
                    message=f"{item.symbol} contains blocked keyword: {keyword}",
                )
            )

    return violations
