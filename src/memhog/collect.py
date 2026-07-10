"""macOS の外部コマンド(top / ps / sysctl / memory_pressure)を叩く薄い I/O 層。

副作用を持つのはこのモジュールに限定し、解析ロジック(parse.py)から分離する。
"""

import subprocess


def _run(args: list[str]) -> str:
    """コマンドを実行し標準出力を返す(失敗時は空文字)。

    Args:
        args: コマンドと引数のリスト。

    Returns:
        標準出力。コマンドが見つからない/失敗しても例外は投げず空文字を返す。
    """
    try:
        proc = subprocess.run(args, capture_output=True, text=True, check=False)
    except (OSError, ValueError):
        return ""
    return proc.stdout


def top_sample(count: int) -> str:
    """メモリ降順で上位 count 件を含む top のワンショット出力を返す。

    Args:
        count: 取得件数。

    Returns:
        top の標準出力全体(PhysMem ヘッダを含む)。
    """
    return _run(["top", "-l", "1", "-o", "mem", "-n", str(count), "-stats", "pid,mem,cpu"])


def ps_command(pid: int) -> str:
    """PID のフルコマンド文字列を返す。

    Args:
        pid: プロセス ID。

    Returns:
        フルコマンド。取得できなければ空文字。
    """
    return _run(["ps", "-o", "command=", "-p", str(pid)]).strip()


def ps_rss_mb(pid: int) -> int:
    """PID の ps RSS を MB で返す。

    Args:
        pid: プロセス ID。

    Returns:
        RSS(MB)。取得できなければ 0。
    """
    out = _run(["ps", "-o", "rss=", "-p", str(pid)]).strip()
    return int(out) // 1024 if out.isdigit() else 0


def swap_usage() -> str:
    """sysctl vm.swapusage の値を返す。

    Returns:
        スワップ使用状況の文字列。取得できなければ空文字。
    """
    return _run(["sysctl", "-n", "vm.swapusage"]).strip()


def memory_pressure() -> str:
    """memory_pressure の出力を返す。

    Returns:
        標準出力全体。取得できなければ空文字。
    """
    return _run(["memory_pressure"])
