"""render モジュールの単体テスト。"""

import io
import shlex

import pytest
from rich.console import Console

from memhog.models import Process, ProcessGroup, SystemMemory
from memhog.render import format_mb, render_group_table, render_table


class TestFormatMb:
    @pytest.mark.parametrize(
        ("mb", "expected"),
        [
            (32768, "32.0G"),
            (1536, "1.5G"),
            (1024, "1.0G"),
            (745, "745M"),
            (0, "0M"),
        ],
    )
    def test_format(self, mb: float, expected: str) -> None:
        assert format_mb(mb) == expected


_SYSTEM = SystemMemory(phys="63G used", swap="total = 1M", free_percentage="37%")


def _render(fn, *args) -> str:
    """幅を固定した Console へ描画して、素のテキストを取り出す。"""
    buffer = io.StringIO()
    console = Console(file=buffer, width=200, no_color=True, highlight=False)
    fn(console, *args)
    return buffer.getvalue()


class TestUntrustedTextIsNotInterpreted:
    """コマンド文字列・アプリ名は他プロセス由来。rich のマークアップとして解釈させない。"""

    HOSTILE = "/usr/bin/evil [bold red]INJECTED[/bold red] --flag"

    def test_process_footer_escapes_markup(self) -> None:
        proc = Process(pid=42, mem_mb=100, rss_mb=50, cpu=0.0, command=self.HOSTILE)
        out = _render(render_table, [proc], _SYSTEM)
        assert "[bold red]INJECTED[/bold red]" in out

    def test_group_footer_escapes_markup(self) -> None:
        proc = Process(pid=42, mem_mb=100, rss_mb=50, cpu=0.0, command=self.HOSTILE)
        group = ProcessGroup(label="[red]evil[/red]", members=(proc,))
        out = _render(render_group_table, [group], _SYSTEM)
        assert "[red]evil[/red]" in out
        assert "[bold red]INJECTED[/bold red]" in out


class TestSuggestedCommandIsShellSafe:
    """フッタの提案コマンドはそのまま貼られる。アプリ名は shlex でクォートする。"""

    def test_label_with_quote_and_semicolon_is_quoted(self) -> None:
        proc = Process(pid=42, mem_mb=100, rss_mb=50, cpu=0.0, command="/bin/x")
        group = ProcessGroup(label="ev'il; touch /tmp/pwned", members=(proc,))
        label = "ev'il; touch /tmp/pwned"
        out = _render(render_group_table, [group], _SYSTEM)
        assert f"memhog --app {shlex.quote(label)}" in out
        # クォート漏れ（アプリ名をそのまま ' で囲んだだけ）は不可。
        assert f"memhog --app '{label}'" not in out
