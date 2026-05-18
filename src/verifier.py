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

    def __init__(self, config_obj=None):
        """初始化校验器"""
        if OpenAI is None:
            raise ImportError("请安装 openai: pip install openai")

        self.config = config_obj if config_obj is not None else config
        self.llm_config = self.config.llm_config

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
        if not self.config.llm_enabled:
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

    def __init__(self, config_obj=None):
        """初始化简单校验器"""
        self.config = config_obj if config_obj is not None else config
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
        if not self.config.llm_enabled:
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

    MAX_CHUNK_CHARS = 6000

    def __init__(self, config_obj=None):
        """初始化知识校验器"""
        if OpenAI is None:
            raise ImportError("请安装 openai: pip install openai")

        self.config = config_obj if config_obj is not None else config
        self.llm_config = self.config.llm_config

        if not self.llm_config['api_key']:
            logger.warning("未配置大模型 API Key，知识模式将不可用")

        self.client = OpenAI(
            api_key=self.llm_config['api_key'],
            base_url=self.llm_config['base_url'],
        )

        self.model = self.llm_config['model']
        self.provider = self.llm_config['provider']

        logger.info(f"知识模式校验器初始化完成: {self.provider} / {self.model}")

    def _chunk_text(self, text: str) -> list:
        """按段落边界将文本拆分为多个块，每块不超过 MAX_CHUNK_CHARS"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_len = 0

        for para in paragraphs:
            if current_len + len(para) > self.MAX_CHUNK_CHARS and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_len = 0
            current_chunk.append(para)
            current_len += len(para)

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def _parse_json_response(self, result_text: str) -> Optional[Dict]:
        """解析 LLM 返回的 JSON，支持 markdown 代码块包裹"""
        try:
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
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    def _repair_json_with_llm(self, broken_response: str) -> Optional[Dict]:
        """尝试让 LLM 修复无效的 JSON 响应"""
        repair_prompt = f"""以下 JSON 格式有误，请修正后重新输出正确的 JSON：

```
{broken_response}
```

只输出修正后的 JSON，不要添加任何解释。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个 JSON 格式修复助手。"},
                    {"role": "user", "content": repair_prompt}
                ],
                temperature=0.1,
                max_tokens=8000,
            )
            repaired_text = response.choices[0].message.content.strip()
            return self._parse_json_response(repaired_text)
        except Exception as e:
            logger.warning(f"JSON 修复请求失败: {e}")
            return None

    def _call_llm_for_chunk(self, text: str, video_title: str,
                            video_description: str,
                            chunk_info: Optional[Dict] = None) -> Optional[Dict]:
        """调用 LLM 处理单个文本块，返回解析后的结果"""
        prompt = self._build_prompt(text, video_title, video_description, chunk_info)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个专业的知识内容整理助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=8000,
        )

        result_text = response.choices[0].message.content.strip()

        # 尝试解析 JSON，失败则尝试修复
        result = self._parse_json_response(result_text)
        if result is not None:
            return result

        logger.warning("LLM 返回的 JSON 解析失败，尝试修复...")
        result = self._repair_json_with_llm(result_text)
        if result is not None:
            logger.info("JSON 修复成功")
            return result

        logger.error("JSON 修复也失败，降级为原始文本模式")
        return None

    def _merge_multi_chunk_results(self, chunk_results: list, video_title: str) -> Dict:
        """合并多个块的 LLM 结果"""
        all_chapters = []
        for i, result in enumerate(chunk_results):
            chapters = result.get('chapters', [])
            for ch in chapters:
                ch['_chunk_index'] = i
            all_chapters.extend(chapters)

        # 重新编号章节
        for idx, ch in enumerate(all_chapters, 1):
            ch.pop('_chunk_index', None)

        # 用各章小结拼接总体总结
        summary_parts = []
        for idx, ch in enumerate(all_chapters, 1):
            ch_summary = ch.get('summary', '')
            if ch_summary:
                summary_parts.append(f"{idx}. {ch.get('title', '')}: {ch_summary}")

        overall_summary = '\n'.join(summary_parts) if summary_parts else ''

        return {
            'summary': overall_summary,
            'chapters': all_chapters,
            'type': 'knowledge',
            'changes': f'已结构化并添加章节总结（共{len(all_chapters)}个章节）',
        }

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
        if not self.config.knowledge_mode_enabled:
            logger.info("知识模式未启用")
            return None

        if not self.llm_config['api_key']:
            logger.warning("未配置 API Key，跳过知识模式处理")
            return None

        try:
            logger.info("正在使用大模型进行知识结构化...")

            if len(text) <= self.MAX_CHUNK_CHARS:
                # 单块处理（原有逻辑）
                result = self._call_llm_for_chunk(text, video_title, video_description)
                if result is None:
                    return self._fallback_result(text)

                chapters = result.get('chapters', [])
                overall_summary = result.get('overall_summary', '')
                logger.info(f"知识结构化完成，共识别 {len(chapters)} 个章节")
                return {
                    'summary': overall_summary,
                    'chapters': chapters,
                    'type': 'knowledge',
                    'changes': f'已结构化并添加章节总结（共{len(chapters)}个章节）',
                }
            else:
                # 多块处理
                chunks = self._chunk_text(text)
                logger.info(f"文本较长（{len(text)}字符），分为{len(chunks)}块处理")

                chunk_results = []
                for i, chunk in enumerate(chunks):
                    logger.info(f"处理第{i+1}/{len(chunks)}块（{len(chunk)}字符）...")
                    result = self._call_llm_for_chunk(
                        chunk, video_title, video_description,
                        chunk_info={"part": i + 1, "total": len(chunks)}
                    )
                    if result is None:
                        result = self._fallback_chapter_result(chunk, i)
                    chunk_results.append(result)

                merged = self._merge_multi_chunk_results(chunk_results, video_title)
                logger.info(f"多块知识结构化完成，共识别 {len(merged['chapters'])} 个章节")
                return merged

        except Exception as e:
            logger.error(f"知识模式处理失败: {e}")
            return self._fallback_result(text)

    def _fallback_result(self, text: str) -> Optional[Dict]:
        """LLM 处理失败时的降级结果"""
        logger.warning("知识模式降级：保留原始文本，不进行结构化")
        return {
            'summary': '',
            'chapters': [{'title': '转写内容', 'content': text, 'summary': ''}],
            'type': 'knowledge',
            'changes': '知识模式处理失败，保留原始内容',
        }

    def _fallback_chapter_result(self, text: str, chunk_index: int) -> Dict:
        """单个块处理失败时的降级结果"""
        return {
            'overall_summary': '',
            'chapters': [{
                'title': f'第{chunk_index + 1}部分',
                'content': text,
                'summary': ''
            }]
        }

    def _build_prompt(
        self,
        text: str,
        video_title: str = "",
        video_description: str = "",
        chunk_info: Optional[Dict] = None
    ) -> str:
        """
        构建知识结构化提示词

        Args:
            text: 待校验的文本
            video_title: 视频标题
            video_description: 视频描述
            chunk_info: 分块信息 {"part": N, "total": M}，None 表示未分块
        """
        title_part = f"这是关于「{video_title}」" if video_title else "这是"
        desc_part = f"\n视频描述：{video_description}" if video_description else ""

        if chunk_info:
            chunk_note = f"\n\n注意：这是视频转写文本的第 {chunk_info['part']}/{chunk_info['total']} 部分。"
        else:
            chunk_note = ""

        chapter_range = "2-5" if chunk_info else "3-8"

        prompt = f"""{title_part}的教学/知识类视频转写内容。{desc_part}{chunk_note}

请对以下内容进行结构化整理，完成以下任务：
1. 将内容划分为 {chapter_range} 个逻辑章节
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


def create_verifier(config_obj=None) -> Optional['TextVerifier']:
    """
    创建校验器实例

    Args:
        config_obj: 配置实例，默认使用全局配置
    """
    cfg = config_obj if config_obj is not None else config

    if not cfg.llm_enabled:
        logger.info("大模型校验未启用")
        return None

    try:
        # 如果启用了知识模式，返回 KnowledgeVerifier
        if cfg.knowledge_mode_enabled and cfg.llm_config.get('api_key'):
            return KnowledgeVerifier(cfg)
        # 否则返回标准 TextVerifier
        elif cfg.llm_config.get('api_key'):
            return TextVerifier(cfg)
        else:
            logger.info("未配置 API Key，使用简单校验器")
            return SimpleTextVerifier(cfg)
    except Exception as e:
        logger.warning(f"创建校验器失败: {e}，将不进行校验")
        return None
