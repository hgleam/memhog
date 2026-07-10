"""プロセス一覧・システム状況の出力(リッチな表 / JSON)。"""

import json

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .models import Process, SystemMemory

_MAX_CMD = 96


def _shorten(command: str) -> str:
    """長いコマンドを末尾省略する。"""
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


def render_table(
    console: Console, processes: list[Process], system: SystemMemory
) -> None:
    """人間向けに表形式で出力する。

    Args:
        console: 出力先の rich Console。
        processes: 表示するプロセス一覧(メモリ降順)。
        system: システム全体のメモリ状況。
    """
    console.print()
    console.print("[bold]== システムメモリ ==[/bold]")
    if system.phys:
        console.print(f"  PhysMem: {system.phys}")
    if system.swap:
        console.print(f"  Swap: {system.swap}")
    if system.free_percentage:
        console.print(f"  空き: {system.free_percentage}")

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
        row_style = "red" if p.mem_mb >= 8000 else ""
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
        console.print(f"  [dim]{top.command}[/dim]")
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
        "system": {
            "phys": system.phys,
            "swap": system.swap,
            "free_percentage": system.free_percentage,
        },
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
