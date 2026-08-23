"""実エントリを subprocess で叩くスモークテスト。

内部関数を直接呼ぶテストは、利用者が実際に叩く経路の壊れを見逃す。typer / click の版
非互換・引数パース崩れ・起動時クラッシュは、`memhog --help` を実行して初めて出る
（実例: typer 0.12.5 + click 8.4 の `make_metavar` 非互換で --help が TypeError になった）。

外部コマンド(top/ps)を叩かない経路（--help / --version / 併用制約のエラー）だけを対象に
するので、macOS 以外の CI でも動く。
"""

import os
import re
import subprocess
import sys

CLI = [sys.executable, "-m", "memhog.cli"]
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    """非 TTY でも折り返し・色でテキスト検査が壊れないように整えて実行する。"""
    env = {**os.environ, "COLUMNS": "220", "NO_COLOR": "1", "TERM": "dumb"}
    result = subprocess.run(
        [*CLI, *args], capture_output=True, text=True, timeout=60, env=env
    )
    result.stdout = _ANSI.sub("", result.stdout)
    result.stderr = _ANSI.sub("", result.stderr)
    return result


class TestEntryPoint:
    def test_help_exits_zero(self) -> None:
        result = _run("--help")
        assert result.returncode == 0, result.stderr[-500:]

    def test_help_lists_every_option(self) -> None:
        out = _run("--help").stdout
        for option in ("--count", "--grep", "--json", "--group", "--app", "--watch", "--kill"):
            assert option in out, f"{option} が --help に出ていない"

    def test_version_exits_zero(self) -> None:
        result = _run("--version")
        assert result.returncode == 0, result.stderr[-500:]
        assert "memhog" in result.stdout


class TestOptionGuards:
    """併用制約は外部コマンドを叩く前に落ちるので、CI(Linux)でも実行経路を検証できる。"""

    def test_group_with_kill_is_rejected(self) -> None:
        result = _run("--group", "--kill")
        assert result.returncode == 1
        assert "併用できません" in result.stdout

    def test_group_with_app_is_rejected(self) -> None:
        result = _run("--group", "--app", "x")
        assert result.returncode == 1
        assert "併用できません" in result.stdout

    def test_watch_with_json_is_rejected(self) -> None:
        result = _run("--watch", "1", "--json")
        assert result.returncode == 1
        assert "併用できません" in result.stdout

    def test_unknown_option_is_rejected(self) -> None:
        assert _run("--no-such-option").returncode != 0
