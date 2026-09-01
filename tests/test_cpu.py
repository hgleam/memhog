"""CPU 表示の検証。

reshog は元々 `%CPU` 列を出していたが、`top -l 1` は 1 サンプル目の CPU を必ず 0.0 で
返すため、**表示されていた値は常に 0 だった**（前サンプルとの差分が取れないため）。
2 サンプル取って 2 つ目を読む形へ直した。ここではその形を固定する。

「CPU 順に出せる」側だけでなく、**取り違えやすい側**も検査する:

  - 2 サンプルの出力を継ぎ足していないか（同じ PID が 2 回出ると件数も合計も倍になる）
  - ヘッダ値は**最後のサンプル**を採っているか（最新の状態）
  - CPU 順のとき **top 側の並び順ごと**切り替えているか（取得後に並べ替えるだけだと、
    母集団が「メモリ上位 N 件」のままで CPU 上位が入らない）
"""

import pytest

from reshog import collect, group, parse, report
from reshog.models import Process, ProcessGroup, PsEntry

# 2 サンプル分の top 出力。1 サンプル目の %CPU は 0.0（実機と同じ挙動）。
TWO_SAMPLES = """Processes: 100 total
Load Avg: 1.00, 2.00, 3.00
CPU usage: 1.0% user, 2.0% sys, 97.0% idle
PhysMem: 10G used (1G wired), 2G unused.

PID    MEM   %CPU
101    500M  0.0
102    200M  0.0

Processes: 101 total
Load Avg: 9.99, 8.88, 7.77
CPU usage: 20.0% user, 70.0% sys, 10.0% idle
PhysMem: 11G used (1G wired), 1G unused.

PID    MEM   %CPU
101    500M  12.5
102    200M  150.0
"""


class TestParsesOnlyTheLastSample:
    def test_does_not_duplicate_rows(self) -> None:
        rows = parse.parse_top_processes(TWO_SAMPLES)
        assert [r[0] for r in rows] == [101, 102], "2 サンプル分を継ぎ足している"

    def test_takes_cpu_from_the_second_sample(self) -> None:
        rows = parse.parse_top_processes(TWO_SAMPLES)
        assert [r[2] for r in rows] == [12.5, 150.0]

    def test_takes_the_latest_phys_mem(self) -> None:
        assert parse.parse_phys_mem(TWO_SAMPLES) == "11G used (1G wired), 1G unused."

    def test_single_sample_still_works(self) -> None:
        one = "PID    MEM   %CPU\n101    500M  3.5\n"
        assert parse.parse_top_processes(one) == [(101, 500.0, 3.5)]


class TestSystemCpuHeader:
    def test_load_average_is_the_latest(self) -> None:
        assert parse.parse_load_average(TWO_SAMPLES) == "9.99, 8.88, 7.77"

    def test_usage_is_the_latest(self) -> None:
        assert parse.parse_cpu_usage(TWO_SAMPLES) == "20.0% user, 70.0% sys, 10.0% idle"

    def test_missing_header_is_none(self) -> None:
        assert parse.parse_load_average("PID MEM %CPU\n1 1M 0.0\n") is None
        assert parse.parse_cpu_usage("") is None

    def test_report_builds_system_cpu(self) -> None:
        cpu = report.build_system_cpu(TWO_SAMPLES)
        assert cpu.load_average == "9.99, 8.88, 7.77"
        assert cpu.usage == "20.0% user, 70.0% sys, 10.0% idle"


class TestTopIsSampledTwice:
    def test_uses_two_samples(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen: list[list[str]] = []
        monkeypatch.setattr(collect, "_run", lambda args: seen.append(args) or "")
        collect.top_sample(5)
        assert seen[0][:3] == ["top", "-l", "2"], seen[0]

    def test_order_is_passed_to_top(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """並べ替えは top 側で行う。取得後に並べ替えると母集団が偏る。"""
        seen: list[list[str]] = []
        monkeypatch.setattr(collect, "_run", lambda args: seen.append(args) or "")
        collect.top_sample(5, "cpu")
        assert "-o" in seen[0] and seen[0][seen[0].index("-o") + 1] == "cpu"

    def test_default_order_is_mem(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen: list[list[str]] = []
        monkeypatch.setattr(collect, "_run", lambda args: seen.append(args) or "")
        collect.top_sample(5)
        assert seen[0][seen[0].index("-o") + 1] == "mem"


def _proc(pid: int, mem_mb: int, cpu: float, command: str) -> Process:
    return Process(pid=pid, mem_mb=mem_mb, rss_mb=mem_mb, cpu=cpu, command=command)


def _entry(pid: int, ppid: int, command: str) -> PsEntry:
    return PsEntry(pid=pid, ppid=ppid, rss_mb=0, command=command)


class TestGroupCpuTotals:
    """1 プロセスずつ見ると小さいが、数が多いと合計は跳ねる（分散して埋もれる消費）。"""

    def _fixture(self) -> tuple[list[Process], dict[int, PsEntry]]:
        # big: 1 プロセスで 50%。swarm: 20 プロセス × 5% = 100%
        procs = [_proc(1, 4000, 50.0, "/Applications/Big.app/Contents/MacOS/Big")]
        snapshot = {1: _entry(1, 0, "/Applications/Big.app/Contents/MacOS/Big")}
        for pid in range(100, 120):
            procs.append(_proc(pid, 10, 5.0, "/usr/local/bin/swarm"))
            snapshot[pid] = _entry(pid, 0, "/usr/local/bin/swarm")
        return procs, snapshot

    def test_total_cpu_is_derived_from_members(self) -> None:
        g = ProcessGroup(label="x", members=(_proc(1, 1, 1.5, "a"), _proc(2, 1, 2.5, "b")))
        assert g.total_cpu == 4.0

    def test_cpu_order_surfaces_the_swarm(self) -> None:
        procs, snapshot = self._fixture()
        groups = group.group_processes(procs, snapshot, order="cpu")
        assert groups[0].label == "swarm", [g.label for g in groups]
        assert groups[0].total_cpu == 100.0
        assert groups[0].count == 20

    def test_mem_order_still_ranks_by_memory(self) -> None:
        """既定（メモリ順）の順位を CPU 対応で壊していないこと。"""
        procs, snapshot = self._fixture()
        groups = group.group_processes(procs, snapshot)
        assert groups[0].label == "Big"

    def test_members_follow_the_same_order(self) -> None:
        procs = [
            _proc(1, 4000, 1.0, "/usr/local/bin/swarm"),
            _proc(2, 10, 90.0, "/usr/local/bin/swarm"),
        ]
        snapshot = {
            1: _entry(1, 0, "/usr/local/bin/swarm"),
            2: _entry(2, 0, "/usr/local/bin/swarm"),
        }
        by_cpu = group.group_processes(procs, snapshot, order="cpu")
        assert by_cpu[0].largest.pid == 2
        by_mem = group.group_processes(procs, snapshot)
        assert by_mem[0].largest.pid == 1
