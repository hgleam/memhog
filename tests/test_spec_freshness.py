"""仕様書鮮度チェックの仕組みが揃っていることを検証する構造テスト。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".githooks" / "pre-commit"


def test_check_spec_freshness_script_exists() -> None:
    assert (ROOT / "scripts" / "check-spec-freshness.sh").exists()


def test_check_spec_freshness_has_watch_patterns() -> None:
    text = (ROOT / "scripts" / "check-spec-freshness.sh").read_text(encoding="utf-8")
    assert "WATCH_PATTERNS=(" in text
    assert '"src/memhog/*"' in text


def test_precommit_hook_exists() -> None:
    assert HOOK.exists()


def test_precommit_hook_calls_check_script() -> None:
    assert "check-spec-freshness.sh" in HOOK.read_text(encoding="utf-8")


def test_precommit_hook_blocks_main_branch() -> None:
    text = HOOK.read_text(encoding="utf-8")
    assert "main" in text and "exit 1" in text


def test_specification_rule_exists() -> None:
    assert (ROOT / ".claude" / "rules" / "specification-update.md").exists()


def test_specification_docs_exist() -> None:
    assert (ROOT / "docs" / "specification" / "client" / "README.md").exists()
    assert (ROOT / "docs" / "specification" / "develop" / "README.md").exists()
