"""CLI smoke tests."""

import pytest

from codex_invest.cli import main


def test_main_help_runs() -> None:
    """CLI help should exit cleanly."""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_main_placeholder_command_runs() -> None:
    """Placeholder command should return success."""
    exit_code = main(["init"])
    assert exit_code == 0
