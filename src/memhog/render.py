"""プロセス一覧・システム状況の出力(リッチな表 / JSON)。"""

import json
import shlex

from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.text import Text

from .models import Process, ProcessGroup, SystemMemory

_MAX_CMD = 96

# この値以上を食っているものは赤で強調する(プロセス単位・アプリ単位で共通)。
_ALERT_MB = 8000


def _shorten(command: str) -> str:
    """長いコマンドを末尾省略する。

    Note:
        省略しても中身は他プロセス由来の文字列のままなので、rich の console.print へ
        渡す際は必ず `escape()` を通すこと(マークアップとして解釈させない)。
    """
    return command if len(command) <= _MAX_CMD else command[: _MAX_CMD - 3] + "..."


def format_mb(mb: float) -> str:
    """MB を人間可読(G/M)に整形する。

    Args:
        mb: MB 単位の値。

    Returns:
        1024 以上なら "12.3G"、未満なら "512M"。
    """
    if mb >= 1024:
        return f"{mb / 1024:.1f}G"
    return f"{round(mb)}M"


def _render_system(console: Console, system: SystemMemory) -> None:
    """システムメモリの概況を出力する(プロセス別 / アプリ別で共通)。

    Args:
        console: 出力先の rich Console。
        system: システム全体のメモリ状況。
    """
    console.print()
    console.print("[bold]== システムメモリ ==[/bold]")
    if system.phys:
        console.print(f"  PhysMem: {escape(system.phys)}")
    if system.swap:
        console.print(f"  Swap: {escape(system.swap)}")
    if system.free_percentage:
        console.print(f"  空き: {escape(system.free_percentage)}")


def _system_payload(system: SystemMemory) -> dict[str, str | None]:
    """SystemMemory を JSON 用の辞書にする(出力形式の正本を 1 箇所に保つ)。

    Args:
        system: システム全体のメモリ状況。

    Returns:
        JSON へそのまま入れられる辞書。
    """
    return {
        "phys": system.phys,
        "swap": system.swap,
        "free_percentage": system.free_percentage,
    }


def render_table(
    console: Console, processes: list[Process], system: SystemMemory
) -> None:
    """人間向けに表形式で出力する。

    Args:
        console: 出力先の rich Console。
        processes: 表示するプロセス一覧(メモリ降順)。
        system: システム全体のメモリ状況。
    """
    _render_system(console, system)

    table = Table(
        title="実メモリ上位 (物理フットプリント = Activity モニタ「メモリ」相当)",
        title_style="bold",
        title_justify="left",
        header_style="dim",
        expand=False,
    )
    table.add_column("#", justify="right")
    table.add_column("MEM", justify="right")
    table.add_column("psRSS", justify="right")
    table.add_column("%CPU", justify="right")
    table.add_column("PID", justify="right")
    table.add_column("COMMAND")

    for rank, p in enumerate(processes, start=1):
        row_style = "red" if p.mem_mb >= _ALERT_MB else ""
        cmd = Text(_shorten(p.command), style=row_style)
        if p.hidden_gpu:
            cmd.append("  ⚠ GPU/Metal常駐(psに出ない)", style="yellow")
        table.add_row(
            str(rank),
            format_mb(p.mem_mb),
            format_mb(p.rss_mb),
            f"{p.cpu:g}",
            str(p.pid),
            cmd,
            style=row_style,
        )
    console.print(table)

    if processes:
        top = processes[0]
        console.print("[bold]== 最大の消費元 ==[/bold]")
        console.print(f"  [green]PID {top.pid} / {format_mb(top.mem_mb)}[/green]")
        console.print(f"  [dim]{escape(_shorten(top.command))}[/dim]")
        console.print(
            f"  停止するなら:  [bold]memhog --kill[/bold]  または  [bold]kill {top.pid}[/bold]"
        )
    console.print()


def build_json(processes: list[Process], system: SystemMemory) -> str:
    """機械可読な JSON 文字列を生成する。

    Args:
        processes: プロセス一覧。
        system: システム状況。

    Returns:
        整形済み JSON 文字列。
    """
    payload = {
        "system": _system_payload(system),
        "processes": [
            {
                "rank": rank,
                "pid": p.pid,
                "mem_mb": p.mem_mb,
                "rss_mb": p.rss_mb,
                "cpu": p.cpu,
                "hidden_gpu": p.hidden_gpu,
                "command": p.command,
            }
            for rank, p in enumerate(processes, start=1)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_group_table(
    console: Console,
    groups: list[ProcessGroup],
    system: SystemMemory,
    grep: str | None = None,
) -> None:
    """アプリ単位に集約した結果を表形式で出力する。

    Args:
        console: 出力先の rich Console。
        groups: 表示するグループ(合計メモリ降順)。
        system: システム全体のメモリ状況。
        grep: 適用中の -g パターン。指定時は「部分合計」であることを見出しに明示する。
    """
    _render_system(console, system)

    title = "アプリ別 実メモリ合計 (ヘルパープロセスを親子関係で合算)"
    if grep:
        title += f" ※ -g {escape(shlex.quote(grep))} 一致プロセスのみの部分合計"
    table = Table(
        title=title,
        title_style="bold",
        title_justify="left",
        header_style="dim",
        expand=False,
    )
    table.add_column("#", justify="right")
    table.add_column("合計MEM", justify="right")
    table.add_column("件数", justify="right")
    table.add_column("最大単体", justify="right")
    table.add_column("最大PID", justify="right")
    table.add_column("APP")

    for rank, g in enumerate(groups, start=1):
        row_style = "red" if g.total_mb >= _ALERT_MB else ""
        label = Text(g.label, style=row_style)
        if g.hidden_gpu:
            label.append("  ⚠ GPU/Metal常駐(psに出ない)", style="yellow")
        table.add_row(
            str(rank),
            format_mb(g.total_mb),
            str(g.count),
            format_mb(g.largest.mem_mb),
            str(g.largest.pid),
            label,
            style=row_style,
        )
    console.print(table)

    if groups:
        top = groups[0]
        console.print("[bold]== 最大の消費元 ==[/bold]")
        console.print(
            f"  [green]{escape(top.label)} / {format_mb(top.total_mb)}"
            f" / {top.count}プロセス[/green]"
        )
        console.print(
            f"  [dim]最大単体: PID {top.largest.pid} "
            f"{escape(_shorten(top.largest.command))}[/dim]"
        )
        console.print(
            "  内訳を見るなら:  "
            f"[bold]memhog --app {escape(shlex.quote(top.label))}[/bold]"
        )
    console.print()


def build_group_json(groups: list[ProcessGroup], system: SystemMemory) -> str:
    """アプリ別集約結果を機械可読な JSON 文字列にする。

    Args:
        groups: グループ一覧。
        system: システム状況。

    Returns:
        整形済み JSON 文字列。
    """
    payload = {
        "system": _system_payload(system),
        "groups": [
            {
                "rank": rank,
                "label": g.label,
                "total_mb": g.total_mb,
                "count": g.count,
                "hidden_gpu": g.hidden_gpu,
                "largest": {
                    "pid": g.largest.pid,
                    "mem_mb": g.largest.mem_mb,
                    "command": g.largest.command,
                },
            }
            for rank, g in enumerate(groups, start=1)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
