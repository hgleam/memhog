"""collect と parse を組み合わせ、プロセス一覧とシステム状況を構築する。"""

from . import collect, parse
from .models import Process, SystemMemory


def build_processes(count: int, pattern: str | None = None) -> tuple[list[Process], str]:
    """メモリ上位プロセスを取得し、必要ならコマンド名でフィルタする。

    フィルタ時は取り漏らしを防ぐため多めに top を取得してから絞り込む。

    Args:
        count: 返す最大件数。
        pattern: フルコマンドに対する部分一致(大文字小文字無視)。None なら全件対象。

    Returns:
        (Process のリスト, top の生出力) のタプル。生出力は SystemMemory 構築に再利用する。
    """
    sample_count = count * 4 if pattern else count
    if sample_count < 40:
        sample_count = 40 if pattern else count
    raw = collect.top_sample(sample_count)

    needle = pattern.lower() if pattern else None
    result: list[Process] = []
    for pid, mem_mb, cpu in parse.parse_top_processes(raw):
        command = collect.ps_command(pid)
        if not command:
            continue
        if needle is not None and needle not in command.lower():
            continue
        result.append(
            Process(
                pid=pid,
                mem_mb=round(mem_mb),
                rss_mb=collect.ps_rss_mb(pid),
                cpu=cpu,
                command=command,
            )
        )
        if len(result) >= count:
            break
    return result, raw


def build_system_memory(top_raw: str) -> SystemMemory:
    """システム全体のメモリ状況を構築する。

    Args:
        top_raw: build_processes が返した top の生出力(PhysMem 行を含む)。

    Returns:
        SystemMemory。
    """
    return SystemMemory(
        phys=parse.parse_phys_mem(top_raw),
        swap=collect.swap_usage() or None,
        free_percentage=parse.parse_free_percentage(collect.memory_pressure()),
    )
