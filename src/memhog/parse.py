"""top / memory_pressure などのテキスト出力を解析する純粋関数群。

外部コマンドを叩かないため単体テストが容易。書式変更への耐性はここで担保する。
"""

import re

_MEM_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)?)([GMKB]?)$")
_UNIT_TO_MB: dict[str, float] = {
    "G": 1024.0,
    "M": 1.0,
    "K": 1.0 / 1024,
    "B": 1.0 / (1024 * 1024),
    "": 1.0,
}


def parse_mem_to_mb(value: str) -> float:
    """top の MEM 文字列を MB(float)に変換する。

    末尾の増減記号(+/-, 前サンプルからの変化)は無視する。

    Args:
        value: "32G" / "6759M" / "745K" / "512B" / "745" / "32G+" 等。

    Returns:
        MB 単位の値。

    Raises:
        ValueError: 解釈できない文字列のとき。
    """
    v = value.strip().rstrip("+-")
    m = _MEM_RE.match(v)
    if not m:
        raise ValueError(f"unparseable mem value: {value!r}")
    return float(m.group(1)) * _UNIT_TO_MB[m.group(2)]


def parse_top_processes(output: str) -> list[tuple[int, float, float]]:
    """`top -l 1 -o mem -stats pid,mem,cpu` の出力を解析する。

    ヘッダ("PID ...")行以降のプロセス行のみを対象にする。

    Args:
        output: top コマンドの標準出力全体。

    Returns:
        (pid, mem_mb, cpu) のタプルのリスト。top の並び(メモリ降順)を保つ。
    """
    rows: list[tuple[int, float, float]] = []
    in_table = False
    for line in output.splitlines():
        if not in_table:
            if line.startswith("PID"):
                in_table = True
            continue
        parts = line.split()
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        pid = int(parts[0])
        try:
            mem_mb = parse_mem_to_mb(parts[1])
        except ValueError:
            continue
        try:
            cpu = float(parts[2])
        except ValueError:
            cpu = 0.0
        rows.append((pid, mem_mb, cpu))
    return rows


def parse_phys_mem(output: str) -> str | None:
    """top の出力ヘッダから PhysMem 行の内容を取り出す。

    Args:
        output: top コマンドの標準出力全体。

    Returns:
        "PhysMem: " 以降の文字列。見つからなければ None。
    """
    for line in output.splitlines():
        if line.startswith("PhysMem:"):
            return line.split(":", 1)[1].strip()
    return None


def parse_free_percentage(output: str) -> str | None:
    """memory_pressure の出力から空き割合を取り出す。

    Args:
        output: memory_pressure コマンドの標準出力。

    Returns:
        "37%" 等の文字列。見つからなければ None。
    """
    for line in output.splitlines():
        if "free percentage" in line:
            return line.split(":", 1)[1].strip()
    return None


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
