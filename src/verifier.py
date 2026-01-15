"""
大模型校验模块
使用大模型 API 对识别结果进行校验和优化
"""

import logging
from typing import Optional, Dict

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from config import config

logger = logging.getLogger(__name__)


class TextVerifier:
    """文本校验器"""

    def __init__(self):
        """初始化校验器"""
        if OpenAI is None:
            raise ImportError("请安装 openai: pip install openai")

        self.llm_config = config.llm_config

        if not self.llm_config['api_key']:
            logger.warning("未配置大模型 API Key，校验功能将不可用")

        self.client = OpenAI(
            api_key=self.llm_config['api_key'],
            base_url=self.llm_config['base_url'],
        )

        self.model = self.llm_config['model']
        self.provider = self.llm_config['provider']

        logger.info(f"大模型校验器初始化完成: {self.provider} / {self.model}")

    def verify_text(
        self,
        text: str,
        video_title: str = ""
    ) -> Optional[Dict]:
        """
        校验和优化文本

        Args:
            text: 待校验的文本
            video_title: 视频标题（用于上下文）

        Returns:
            校验结果字典，包含:
                - text: 校验后的文本
                - changes: 修改说明
            如果校验失败返回 None
        """
        if not config.llm_enabled:
            logger.info("大模型校验未启用，跳过校验")
            return None

        if not self.llm_config['api_key']:
            logger.warning("未配置 API Key，跳过校验")
            return None

        try:
            logger.info("正在使用大模型校验文本...")

            prompt = self._build_prompt(text, video_title)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的文本校验助手。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=4000,
            )

            result_text = response.choices[0].message.content.strip()

            logger.info("大模型校验完成")

            return {
                'text': result_text,
                'changes': '已由大模型校验和优化',
            }

        except Exception as e:
            logger.error(f"大模型校验失败: {e}")
            return None

    def _build_prompt(self, text: str, video_title: str = "") -> str:
        """
        构建提示词

        Args:
            text: 待校验的文本
            video_title: 视频标题

        Returns:
            提示词
        """
        context = f"这是关于「{video_title}」的视频字幕。" if video_title else ""

        prompt = f"""{context}

请对以下中文文本进行校验和优化：

1. 修正错别字和同音字错误
2. 优化标点符号使用
3. 统一术语表达
4. 保持原有的段落结构和换行
5. 不要添加或删除内容
6. 不要添加任何解释或说明

待校验文本：
```
{text}
```

直接输出校验后的文本，不要添加任何前缀或说明。"""

        return prompt


class SimpleTextVerifier:
    """简单文本校验器（不使用大模型）"""

    def __init__(self):
        """初始化简单校验器"""
        logger.info("使用简单文本校验器")

    def verify_text(
        self,
        text: str,
        video_title: str = ""
    ) -> Optional[Dict]:
        """
        简单校验文本

        Args:
            text: 待校验的文本
            video_title: 视频标题（未使用）

        Returns:
            校验结果字典，包含简单的文本优化
        """
        if not config.llm_enabled:
            return None

        # 简单的文本清理
        cleaned = self._simple_clean(text)

        if cleaned == text:
            return None  # 没有变化

        return {
            'text': cleaned,
            'changes': '已进行简单清理',
        }

    def _simple_clean(self, text: str) -> str:
        """
        简单的文本清理

        Args:
            text: 待清理的文本

        Returns:
            清理后的文本
        """
        # 移除多余空行
        lines = text.split('\n')
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            stripped = line.strip()
            if stripped:
                cleaned_lines.append(stripped)
                prev_empty = False
            elif not prev_empty:
                cleaned_lines.append('')
                prev_empty = True

        return '\n'.join(cleaned_lines)


def create_verifier() -> Optional['TextVerifier']:
    """
    创建校验器实例

    Returns:
        校验器实例，如果未启用则返回 None
    """
    if not config.llm_enabled:
        logger.info("大模型校验未启用")
        return None

    try:
        if config.llm_config.get('api_key'):
            return TextVerifier()
        else:
            logger.info("未配置 API Key，使用简单校验器")
            return SimpleTextVerifier()
    except Exception as e:
        logger.warning(f"创建校验器失败: {e}，将不进行校验")
        return None
