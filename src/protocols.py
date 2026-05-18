"""Protocol 接口定义 — 轻量级抽象层，支持依赖注入和测试"""

from typing import Optional, Dict, List, Protocol


class TextExtractor(Protocol):
    """文本提取器接口（字幕或 ASR）"""

    def extract(self, video_url: str, output_dir: str) -> Optional[str]:
        """从视频 URL 提取文本"""
        ...


class TextVerifierProtocol(Protocol):
    """文本校验器接口"""

    def verify_text(
        self,
        text: str,
        video_title: str = "",
        video_description: str = ""
    ) -> Optional[Dict]:
        """校验/优化文本"""
        ...
