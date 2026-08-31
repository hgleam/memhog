"""memhog の typer エントリポイント。"""

import signal
import time

import typer
from rich.console import Console

from . import __version__, collect, render, report
from .models import Process

app = typer.Typer(
    add_completion=False,
    help="macOS の実メモリ(物理フットプリント)を食っているプロセスを特定して提示する。",
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"memhog {__version__}")
        raise typer.Exit()


def _kill_process(
    processes: list[Process], console: Console, force: bool, assume_yes: bool
) -> None:
    """一覧から PID を選んで停止する(不可逆操作のため既定で確認する)。

    Args:
        processes: 表示済みのプロセス一覧。
        console: 出力先 Console。
        force: True なら SIGKILL、False なら SIGTERM。
        assume_yes: True なら確認プロンプトを省略する。
    """
    if not processes:
        console.print("[yellow]対象プロセスがありません。[/yellow]")
        return
    default_pid = processes[0].pid
    pid = typer.prompt("停止する PID", default=default_pid, type=int)

    target = next((p for p in processes if p.pid == pid), None)
    label = target.command if target else "(一覧外の PID)"
    if pid <= 1 or pid == collect.current_pid():
        console.print("[red]その PID は停止できません(システム/自分自身)。[/red]")
        raise typer.Exit(code=1)

    sig = signal.SIGKILL if force else signal.SIGTERM
    console.print(f"[dim]{label}[/dim]")
    if not assume_yes and not typer.confirm(
        f"PID {pid} を {sig.name} で停止します。よいですか?"
    ):
        console.print("中止しました。")
        return
    result = collect.send_signal(pid, sig)
    if result == "not_found":
        console.print(f"[yellow]PID {pid} は存在しません(既に終了?)。[/yellow]")
        return
    if result == "denied":
        console.print(f"[red]PID {pid} を停止する権限がありません(sudo が必要かも)。[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]PID {pid} に {sig.name} を送信しました。[/green]")


@app.command()
def main(
    count: int = typer.Option(15, "-n", "--count", help="表示する件数。"),
    sort: str = typer.Option(
        "mem",
        "--sort",
        help="並べる基準。mem(実メモリ) または cpu(CPU使用率)。",
    ),
    grep: str | None = typer.Option(
        None, "-g", "--grep", help="フルコマンドに部分一致するものだけ表示(大小無視)。"
    ),
    json_out: bool = typer.Option(False, "--json", help="機械可読な JSON で出力する。"),
    group_by_app: bool = typer.Option(
        False,
        "--group",
        help="プロセス単位でなくアプリ単位に合算して表示する(分散して埋もれるものを炙り出す)。",
    ),
    app: str | None = typer.Option(
        None,
        "--app",
        help="--group の APP 名を指定し、そのアプリに属するプロセスだけを一覧する(内訳)。",
    ),
    watch: float | None = typer.Option(
        None, "--watch", help="指定秒間隔で画面を更新し続ける(top のように監視)。"
    ),
    kill: bool = typer.Option(False, "--kill", help="一覧から PID を選んで停止する。"),
    force: bool = typer.Option(False, "--force", help="--kill 時に SIGKILL を使う。"),
    assume_yes: bool = typer.Option(False, "-y", "--yes", help="--kill の確認を省略する。"),
    _version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="バージョン表示。"
    ),
) -> None:
    """実メモリ(既定)または CPU の上位プロセスを表示する。

    ps の RSS は Metal/MPS(GPU 共有メモリ)を数えないため、ComfyUI 等の ML 系は
    小さく見える。本コマンドは top の物理フットプリントでランクし、その乖離を
    「⚠ GPU/Metal常駐」印で炙り出す。
    """
    console = Console()

    if sort not in ("mem", "cpu"):
        console.print("[red]--sort は mem か cpu を指定してください。[/red]")
        raise typer.Exit(code=1)

    if group_by_app and app is not None:
        console.print(
            "[red]--group と --app は併用できません(合計か内訳かを選んでください)。[/red]"
        )
        raise typer.Exit(code=1)

    if group_by_app and kill:
        console.print(
            "[red]--group は --kill と併用できません(停止対象は PID で選ぶ必要があるため)。[/red]"
        )
        raise typer.Exit(code=1)

    if watch is not None:
        if json_out or kill:
            console.print("[red]--watch は --json / --kill と併用できません。[/red]")
            raise typer.Exit(code=1)
        _run_watch(console, count, grep, watch, group_by_app, app, sort)
        return

    if app is not None:
        processes, top_raw = report.build_app_processes(app, count, sort)
        system = report.build_system_memory(top_raw)
        cpu = report.build_system_cpu(top_raw)
        if json_out:
            typer.echo(render.build_json(processes, system, cpu))
            return
        render.render_table(console, processes, system, cpu, sort)
        if kill:
            _kill_process(processes, console, force, assume_yes)
        return

    if group_by_app:
        groups, top_raw = report.build_groups(count, grep, sort)
        system = report.build_system_memory(top_raw)
        cpu = report.build_system_cpu(top_raw)
        if json_out:
            typer.echo(render.build_group_json(groups, system, cpu))
            return
        render.render_group_table(console, groups, system, cpu, grep, sort)
        return

    processes, top_raw = report.build_processes(count, grep, sort)
    system = report.build_system_memory(top_raw)
    cpu = report.build_system_cpu(top_raw)

    if json_out:
        typer.echo(render.build_json(processes, system, cpu))
        return

    render.render_table(console, processes, system, cpu, sort)
    if kill:
        _kill_process(processes, console, force, assume_yes)


def _run_watch(
    console: Console,
    count: int,
    grep: str | None,
    interval: float,
    group_by_app: bool = False,
    app: str | None = None,
    sort: str = "mem",
) -> None:
    """--watch: 一定間隔で画面を再描画し続ける。

    Args:
        console: 出力先 Console。
        count: 表示件数。
        grep: フィルタ文字列。
        interval: 更新間隔(秒)。
        group_by_app: True ならアプリ単位に合算して描画する。
        app: 指定時はそのアプリに属するプロセスだけを描画する。
        sort: 並べる基準("mem" または "cpu")。
    """
    try:
        while True:
            if group_by_app:
                groups, top_raw = report.build_groups(count, grep, sort)
                system = report.build_system_memory(top_raw)
                cpu = report.build_system_cpu(top_raw)
                console.clear()
                render.render_group_table(console, groups, system, cpu, grep, sort)
                console.print(f"[dim]{interval:g}秒ごとに更新 / Ctrl-C で終了[/dim]")
                time.sleep(interval)
                continue
            if app is not None:
                processes, top_raw = report.build_app_processes(app, count, sort)
            else:
                processes, top_raw = report.build_processes(count, grep, sort)
            system = report.build_system_memory(top_raw)
            cpu = report.build_system_cpu(top_raw)
            console.clear()
            render.render_table(console, processes, system, cpu, sort)
            console.print(f"[dim]{interval:g}秒ごとに更新 / Ctrl-C で終了[/dim]")
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n終了しました。")


if __name__ == "__main__":
    app()
