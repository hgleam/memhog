"""render モジュールの単体テスト。"""

import pytest

from memhog.render import format_mb


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
