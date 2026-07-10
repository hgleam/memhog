"""collect モジュール(I/O 層)の単体テスト。

os.kill を monkeypatch し、副作用を collect に集約したことで例外→結果コードの
翻訳がテストできることを確認する。
"""

import signal

import pytest

from memhog import collect


class TestSendSignal:
    def test_ok(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sent: list[tuple[int, int]] = []
        monkeypatch.setattr(collect.os, "kill", lambda pid, sig: sent.append((pid, sig)))
        assert collect.send_signal(4321, signal.SIGTERM) == "ok"
        assert sent == [(4321, signal.SIGTERM)]

    def test_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(pid: int, sig: int) -> None:
            raise ProcessLookupError

        monkeypatch.setattr(collect.os, "kill", _raise)
        assert collect.send_signal(4321, signal.SIGKILL) == "not_found"

    def test_denied(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(pid: int, sig: int) -> None:
            raise PermissionError

        monkeypatch.setattr(collect.os, "kill", _raise)
        assert collect.send_signal(4321, signal.SIGTERM) == "denied"


class TestCurrentPid:
    def test_returns_own_pid(self) -> None:
        import os

        assert collect.current_pid() == os.getpid()
