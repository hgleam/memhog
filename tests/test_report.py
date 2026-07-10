"""report モジュールの単体テスト(collect をモックして top を叩かない)。"""

import pytest

from memhog import collect, report

TOP_SAMPLE = """\
PhysMem: 63G used (7613M wired, 32G compressor), 217M unused.

PID    MEM   %CPU
28632  32G   0.0
69624  8112M 0.0
29473  6759M 0.1
"""

_COMMANDS = {
    28632: "/usr/bin/python main.py --port 8188",
    69624: "com.apple.Virtualization.VirtualMachine",
    29473: "/opt/homebrew/bin/llama-server --port 8080",
}
_RSS = {28632: 26, 69624: 2600, 29473: 12}


@pytest.fixture(autouse=True)
def _mock_collect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(collect, "top_sample", lambda count: TOP_SAMPLE)
    monkeypatch.setattr(collect, "ps_command", lambda pid: _COMMANDS.get(pid, ""))
    monkeypatch.setattr(collect, "ps_rss_mb", lambda pid: _RSS.get(pid, 0))
    monkeypatch.setattr(collect, "swap_usage", lambda: "total = 32768.00M  used = 31855.94M")
    monkeypatch.setattr(collect, "memory_pressure", lambda: "free percentage: 37%\n")


class TestBuildProcesses:
    def test_builds_all(self) -> None:
        procs, _ = report.build_processes(count=10)
        assert [p.pid for p in procs] == [28632, 69624, 29473]
        assert procs[0].mem_mb == 32768
        assert procs[0].rss_mb == 26
        assert procs[0].hidden_gpu is True
        assert procs[1].hidden_gpu is False

    def test_respects_count(self) -> None:
        procs, _ = report.build_processes(count=2)
        assert len(procs) == 2

    def test_filters_by_pattern(self) -> None:
        procs, _ = report.build_processes(count=10, pattern="python")
        assert [p.pid for p in procs] == [28632]

    def test_pattern_is_case_insensitive(self) -> None:
        procs, _ = report.build_processes(count=10, pattern="LLAMA")
        assert [p.pid for p in procs] == [29473]

    def test_skips_pid_without_command(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            collect, "ps_command", lambda pid: "" if pid == 69624 else _COMMANDS[pid]
        )
        procs, _ = report.build_processes(count=10)
        assert 69624 not in [p.pid for p in procs]


class TestBuildSystemMemory:
    def test_builds(self) -> None:
        system = report.build_system_memory(TOP_SAMPLE)
        assert system.phys == "63G used (7613M wired, 32G compressor), 217M unused."
        assert system.free_percentage == "37%"
        assert system.swap is not None
