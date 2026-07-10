"""models モジュールの単体テスト(GPU/Metal 常駐判定が核心)。"""

from memhog.models import Process


def _proc(mem_mb: int, rss_mb: int) -> Process:
    return Process(pid=1, mem_mb=mem_mb, rss_mb=rss_mb, cpu=0.0, command="x")


class TestHiddenGpu:
    def test_comfyui_like_is_hidden(self) -> None:
        # 32G フットプリントだが ps RSS は 26MB(=ComfyUI 実測) -> 炙り出す
        assert _proc(32768, 26).hidden_gpu is True

    def test_llama_server_like_is_hidden(self) -> None:
        assert _proc(6759, 12).hidden_gpu is True

    def test_vm_like_is_not_hidden(self) -> None:
        # RSS も相応(2.6G)にある通常プロセスは炙り出さない
        assert _proc(8112, 2600).hidden_gpu is False

    def test_below_size_threshold_is_not_hidden(self) -> None:
        # 小さいプロセスは RSS 比が大きくても対象外
        assert _proc(1500, 1).hidden_gpu is False

    def test_exactly_four_times_is_not_hidden(self) -> None:
        # ちょうど 4 倍は超えていないので対象外(> 判定)
        assert _proc(4000, 1000).hidden_gpu is False

    def test_just_over_four_times_is_hidden(self) -> None:
        assert _proc(4001, 1000).hidden_gpu is True
