"""
大模型校验模块
使用大模型 API 对识别结果进行校验和优化
"""

import json
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
        video_title: str = "",
        video_description: str = ""
    ) -> Optional[Dict]:
        """
        校验和优化文本

        Args:
            text: 待校验的文本
            video_title: 视频标题（用于上下文）
            video_description: 视频描述（未使用，保留参数兼容性）

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


class KnowledgeVerifier:
    """知识类视频校验器

    功能：
    1. 识别章节结构（自动生成章节标题）
    2. 为每个章节添加小结
    3. 生成总体总结
    """

    def __init__(self):
        """初始化知识校验器"""
        if OpenAI is None:
            raise ImportError("请安装 openai: pip install openai")

        self.llm_config = config.llm_config

        if not self.llm_config['api_key']:
            logger.warning("未配置大模型 API Key，知识模式将不可用")

        self.client = OpenAI(
            api_key=self.llm_config['api_key'],
            base_url=self.llm_config['base_url'],
        )

        self.model = self.llm_config['model']
        self.provider = self.llm_config['provider']

        logger.info(f"知识模式校验器初始化完成: {self.provider} / {self.model}")

    def verify_text(
        self,
        text: str,
        video_title: str = "",
        video_description: str = ""
    ) -> Optional[Dict]:
        """
        对知识类视频进行结构化处理

        Args:
            text: 待校验的文本
            video_title: 视频标题
            video_description: 视频描述

        Returns:
            {
                'summary': '总体总结',
                'chapters': [
                    {'title': '章节标题', 'content': '章节内容', 'summary': '章节小结'},
                    ...
                ],
                'type': 'knowledge',
                'changes': '已结构化并添加章节总结'
            }
            如果校验失败返回 None
        """
        if not config.knowledge_mode_enabled:
            logger.info("知识模式未启用")
            return None

        if not self.llm_config['api_key']:
            logger.warning("未配置 API Key，跳过知识模式处理")
            return None

        try:
            logger.info("正在使用大模型进行知识结构化...")

            prompt = self._build_prompt(text, video_title, video_description)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的知识内容整理助手。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=8000,
            )

            result_text = response.choices[0].message.content.strip()

            # 解析 JSON 结果
            try:
                # 尝试提取 JSON 部分（可能包含 markdown 代码块）
                if "```json" in result_text:
                    json_start = result_text.find("```json") + 7
                    json_end = result_text.find("```", json_start)
                    json_str = result_text[json_start:json_end].strip()
                elif "```" in result_text:
                    json_start = result_text.find("```") + 3
                    json_end = result_text.find("```", json_start)
                    json_str = result_text[json_start:json_end].strip()
                else:
                    json_str = result_text

                result = json.loads(json_str)

                # 转换为标准格式
                chapters = result.get('chapters', [])
                overall_summary = result.get('overall_summary', '')

                logger.info(f"知识结构化完成，共识别 {len(chapters)} 个章节")

                return {
                    'summary': overall_summary,
                    'chapters': chapters,
                    'type': 'knowledge',
                    'changes': f'已结构化并添加章节总结（共{len(chapters)}个章节）',
                }

            except json.JSONDecodeError as e:
                logger.error(f"解析大模型返回的 JSON 失败: {e}")
                logger.debug(f"返回内容: {result_text}")
                return None

        except Exception as e:
            logger.error(f"知识模式处理失败: {e}")
            return None

    def _build_prompt(
        self,
        text: str,
        video_title: str = "",
        video_description: str = ""
    ) -> str:
        """
        构建知识结构化提示词

        Args:
            text: 待校验的文本
            video_title: 视频标题
            video_description: 视频描述

        Returns:
            提示词
        """
        title_part = f"这是关于「{video_title}」" if video_title else "这是"
        desc_part = f"\n视频描述：{video_description}" if video_description else ""

        # 限制文本长度，避免超过 token 限制
        max_text_length = 8000
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."

        prompt = f"""{title_part}的教学/知识类视频转写内容。{desc_part}

请对以下内容进行结构化整理，完成以下任务：
1. 将内容划分为 3-8 个逻辑章节
2. 为每个章节生成合适的标题（简洁明了，8-15字）
3. 为每个章节写 1-2 句小结
4. 生成总体总结（3-5 句话，概括核心知识点和价值）

待整理文本：
```
{text}
```

请以 JSON 格式返回：
{{
    "overall_summary": "总体总结：核心知识点和价值",
    "chapters": [
        {{
            "title": "章节标题",
            "content": "该章节的完整内容（保留原文并优化格式）",
            "summary": "章节小结：1-2句话"
        }}
    ]
}}

注意：
- 章节划分要符合逻辑，不要随意分割
- 标题要反映章节的核心内容
- 章节内容要保留原文精华，不要过度删减
- 小结要提炼章节的核心知识点
- 确保返回的是有效的 JSON 格式，不要包含其他说明文字"""

        return prompt


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
        # 如果启用了知识模式，返回 KnowledgeVerifier
        if config.knowledge_mode_enabled and config.llm_config.get('api_key'):
            return KnowledgeVerifier()
        # 否则返回标准 TextVerifier
        elif config.llm_config.get('api_key'):
            return TextVerifier()
        else:
            logger.info("未配置 API Key，使用简单校验器")
            return SimpleTextVerifier()
    except Exception as e:
        logger.warning(f"创建校验器失败: {e}，将不进行校验")
        return None
