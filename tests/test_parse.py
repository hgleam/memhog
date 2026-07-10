"""parse モジュールの単体テスト。"""

import pytest

from memhog.parse import (
    format_mb,
    parse_free_percentage,
    parse_mem_to_mb,
    parse_phys_mem,
    parse_top_processes,
)

# 実際の `top -l 1 -o mem -n N -stats pid,mem,cpu` 出力を模したフィクスチャ
TOP_SAMPLE = """\
Processes: 700 total, 3 running, 697 sleeping, 3400 threads
PhysMem: 63G used (7613M wired, 32G compressor), 217M unused.
VM: 680T vsize, 5363M framework vsize, 36693660(0) swapins, 64364611(0) swapouts.

PID    MEM   %CPU
28632  32G   0.0
69624  8112M 0.0
29473  6759M 0.1
172    1210M 0.0
50209  745M  0.0
"""


class TestParseMemToMb:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("32G", 32768.0),
            ("6759M", 6759.0),
            ("745M", 745.0),
            ("512K", 0.5),
            ("1048576B", 1.0),
            ("745", 745.0),
            ("32G+", 32768.0),
            ("745M-", 745.0),
            ("  32G  ", 32768.0),
        ],
    )
    def test_valid(self, value: str, expected: float) -> None:
        assert parse_mem_to_mb(value) == pytest.approx(expected)

    @pytest.mark.parametrize("value", ["", "abc", "12X", "G12"])
    def test_invalid_raises(self, value: str) -> None:
        with pytest.raises(ValueError):
            parse_mem_to_mb(value)


class TestParseTopProcesses:
    def test_extracts_rows_in_order(self) -> None:
        rows = parse_top_processes(TOP_SAMPLE)
        assert rows[0] == (28632, 32768.0, 0.0)
        assert rows[1] == (69624, 8112.0, 0.0)
        assert rows[2] == (29473, 6759.0, 0.1)
        assert len(rows) == 5

    def test_ignores_header_and_blank(self) -> None:
        rows = parse_top_processes(TOP_SAMPLE)
        pids = [r[0] for r in rows]
        assert 700 not in pids  # "Processes: 700 total" をプロセス行と誤認しない

    def test_empty_output(self) -> None:
        assert parse_top_processes("") == []


class TestParsePhysMem:
    def test_extracts(self) -> None:
        assert parse_phys_mem(TOP_SAMPLE) == "63G used (7613M wired, 32G compressor), 217M unused."

    def test_missing(self) -> None:
        assert parse_phys_mem("no header here") is None


class TestParseFreePercentage:
    def test_extracts(self) -> None:
        out = "Pages compressed: 5\nSystem-wide memory free percentage: 37%\n"
        assert parse_free_percentage(out) == "37%"

    def test_missing(self) -> None:
        assert parse_free_percentage("nothing") is None


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
