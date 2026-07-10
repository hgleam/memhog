"""memhog のドメインモデル。"""

from dataclasses import dataclass

# GPU/Metal 常駐(ps に出ない)判定のしきい値
HIDDEN_GPU_MIN_MB = 2000
HIDDEN_GPU_RSS_RATIO = 4


@dataclass(frozen=True)
class Process:
    """1 プロセスのメモリ実態。

    Attributes:
        pid: プロセス ID。
        mem_mb: 物理フットプリント(MB)。Activity モニタ「メモリ」列 = top の MEM 相当。
        rss_mb: ps の RSS(MB)。Metal/MPS(GPU 共有メモリ)を数えないため過小に出る。
        cpu: CPU 使用率(%)。
        command: フルコマンド文字列。
    """

    pid: int
    mem_mb: int
    rss_mb: int
    cpu: float
    command: str

    @property
    def hidden_gpu(self) -> bool:
        """ps の RSS に現れない GPU/Metal 常駐メモリを抱えているか。

        物理フットプリントが十分大きく(>= HIDDEN_GPU_MIN_MB)、かつ ps RSS の
        HIDDEN_GPU_RSS_RATIO 倍を超える場合、「小さく見えるのに実は巨大」なプロセス
        (ComfyUI・llama-server 等の ML 系)とみなす。

        Returns:
            GPU/Metal 常駐と判定されれば True。
        """
        return (
            self.mem_mb >= HIDDEN_GPU_MIN_MB
            and self.mem_mb > self.rss_mb * HIDDEN_GPU_RSS_RATIO
        )


@dataclass(frozen=True)
class SystemMemory:
    """システム全体のメモリ状況。

    Attributes:
        phys: top の PhysMem 行(例 "63G used (...), 217M unused")。
        swap: sysctl vm.swapusage の値。
        free_percentage: memory_pressure の空き割合(例 "37%")。
    """

    phys: str | None
    swap: str | None
    free_percentage: str | None
