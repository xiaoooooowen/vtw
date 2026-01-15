"""
工具函数模块
提供通用的辅助函数
"""

import re
import time
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import urlparse

try:
    import opencc
    OPENCC_AVAILABLE = True
except ImportError:
    OPENCC_AVAILABLE = False


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    清理文件名，移除非法字符

    Args:
        filename: 原始文件名
        max_length: 最大长度

    Returns:
        清理后的文件名
    """
    # 移除非法字符
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # 移除控制字符
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)

    # 移除首尾空格和点
    filename = filename.strip(' .')

    # 限制长度
    if len(filename) > max_length:
        filename = filename[:max_length]

    return filename or 'unnamed'


def extract_bvid(url: str) -> Optional[str]:
    """
    从 B站 URL 中提取 BV 号

    Args:
        url: B站视频 URL

    Returns:
        BV 号，如果提取失败返回 None
    """
    # 匹配 BV 开头的 ID
    match = re.search(r'BV[a-zA-Z0-9]{10}', url)
    return match.group(0) if match else None


def extract_uid(url: str) -> Optional[str]:
    """
    从 B站空间 URL 中提取 UID

    Args:
        url: B站空间 URL

    Returns:
        UID，如果提取失败返回 None
    """
    # 匹配 space.bilibili.com/数字 格式
    match = re.search(r'space\.bilibili\.com/(\d+)', url)
    if match:
        return match.group(1)

    # 匹配纯数字
    match = re.search(r'/(\d+)$', url)
    return match.group(1) if match else None


def format_duration(seconds: float) -> str:
    """
    格式化时长

    Args:
        seconds: 秒数（可以是 int 或 float）

    Returns:
        格式化的时长字符串，如 "10:30"
    """
    seconds = float(seconds)  # 确保是 float
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_date(date_str: str) -> str:
    """
    格式化日期

    Args:
        date_str: 日期字符串，如 "20240115"

    Returns:
        格式化的日期字符串，如 "2024-01-15"
    """
    if not date_str or len(date_str) != 8:
        return date_str

    year = date_str[:4]
    month = date_str[4:6]
    day = date_str[6:8]

    return f"{year}-{month}-{day}"


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    失败重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


def generate_unique_filepath(directory: Path, filename: str) -> Path:
    """
    生成唯一的文件路径，如果文件已存在则添加序号

    Args:
        directory: 目标目录
        filename: 文件名

    Returns:
        唯一的文件路径
    """
    filepath = directory / filename

    if not filepath.exists():
        return filepath

    # 分离文件名和扩展名
    stem = filepath.stem
    suffix = filepath.suffix
    counter = 1

    while True:
        new_filename = f"{stem}_{counter}{suffix}"
        new_filepath = directory / new_filename

        if not new_filepath.exists():
            return new_filepath

        counter += 1


def parse_subtitles(subtitle_file: Path) -> List[Dict]:
    """
    解析字幕文件

    Args:
        subtitle_file: 字幕文件路径

    Returns:
        字幕片段列表，每个片段包含 'start'、'end'、'text'
    """
    content = subtitle_file.read_text(encoding='utf-8')
    subtitles = []

    # 根据文件扩展名选择解析方式
    if subtitle_file.suffix == '.ass':
        subtitles = _parse_ass(content)
    elif subtitle_file.suffix == '.srt':
        subtitles = _parse_srt(content)
    elif subtitle_file.suffix == '.json':
        subtitles = _parse_json_subtitle(content)

    return subtitles


def _parse_ass(content: str) -> List[Dict]:
    """解析 ASS 格式字幕"""
    subtitles = []
    pattern = re.compile(
        r'Dialog: \d+,\s*(\d+:\d+:\d+\.\d+),\s*(\d+:\d+:\d+\.\d+),[^,]*,[^,]*,'
        r'\d+,\d+,\d+,\d+,(.+)',
        re.MULTILINE
    )

    for match in pattern.finditer(content):
        start = match.group(1)
        end = match.group(2)
        text = match.group(3).replace('\\N', '\n').replace('\\n', '\n')
        text = re.sub(r'\{[^}]*\}', '', text)  # 移除样式标签

        subtitles.append({
            'start': _ass_time_to_seconds(start),
            'end': _ass_time_to_seconds(end),
            'text': text.strip()
        })

    return subtitles


def _parse_srt(content: str) -> List[Dict]:
    """解析 SRT 格式字幕"""
    subtitles = []
    pattern = re.compile(
        r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)',
        re.DOTALL
    )

    for match in pattern.finditer(content):
        start = _srt_time_to_seconds(match.group(2))
        end = _srt_time_to_seconds(match.group(3))
        text = match.group(4).strip()

        subtitles.append({
            'start': start,
            'end': end,
            'text': text
        })

    return subtitles


def _parse_json_subtitle(content: str) -> List[Dict]:
    """解析 JSON 格式字幕"""
    import json

    try:
        data = json.loads(content)
        # 假设格式为 {"body": [{"from": 开始时间, "to": 结束时间, "content": 文本}]}
        if isinstance(data, dict) and 'body' in data:
            return [
                {
                    'start': item.get('from', 0),
                    'end': item.get('to', 0),
                    'text': item.get('content', '')
                }
                for item in data['body']
            ]
    except json.JSONDecodeError:
        pass

    return []


def _ass_time_to_seconds(time_str: str) -> float:
    """将 ASS 时间格式转换为秒"""
    parts = time_str.replace('.', ':').split(':')
    if len(parts) == 4:
        hours, minutes, seconds, centiseconds = map(float, parts)
        return hours * 3600 + minutes * 60 + seconds + centiseconds / 100
    return 0.0


def _srt_time_to_seconds(time_str: str) -> float:
    """将 SRT 时间格式转换为秒"""
    time_str = time_str.replace(',', '.')
    parts = time_str.split(':')
    if len(parts) == 3:
        hours, minutes, seconds = map(float, parts)
        return hours * 3600 + minutes * 60 + seconds
    return 0.0


def merge_subtitles(subtitles: List[Dict], max_gap: float = 1.0) -> str:
    """
    合并字幕片段为纯文本

    Args:
        subtitles: 字幕列表
        max_gap: 最大间隔，超过此间隔则分段

    Returns:
        合并后的文本
    """
    if not subtitles:
        return ''

    text_parts = []
    last_end = 0

    for sub in subtitles:
        current_start = sub['start']
        current_text = sub['text']

        # 如果间隔太大，添加分段
        if last_end > 0 and (current_start - last_end) > max_gap:
            text_parts.append('')  # 空行分段

        text_parts.append(current_text)
        last_end = sub['end']

    return '\n'.join(text_parts).strip()


def convert_to_simplified(text: str) -> str:
    """
    将繁体中文转换为简体中文

    Args:
        text: 输入文本

    Returns:
        转换后的简体中文文本，如果 opencc 不可用则返回原文本
    """
    if not OPENCC_AVAILABLE:
        return text

    try:
        converter = opencc.OpenCC('t2s')  # 繁体转简体
        return converter.convert(text)
    except Exception:
        return text


def group_segments_to_paragraphs(segments: List[Dict], max_gap: float = 1.5, paragraph_length: int = 300) -> str:
    """
    将 Whisper 的分段信息组织成段落

    Args:
        segments: Whisper 分段列表，每个包含 start, end, text
        max_gap: 最大时间间隔（秒），超过此间隔则新起段落
        paragraph_length: 每个段落的字符数目标

    Returns:
        组织成段落的文本
    """
    if not segments:
        return ''

    paragraphs = []
    current_chars = 0
    current_lines = []

    for i, segment in enumerate(segments):
        text = segment['text'].strip()
        if not text:
            continue

        # 检查是否需要新起段落
        should_break = False

        # 基于时间间隔的判断（语音停顿超过阈值）
        if i < len(segments) - 1:
            next_segment = segments[i + 1]
            gap = next_segment['start'] - segment['end']
            if gap > max_gap and current_chars > 50:  # 至少有一些内容才分段
                should_break = True

        # 基于段落长度的判断（避免段落过长）
        if current_chars + len(text) > paragraph_length:
            should_break = True

        if should_break:
            if current_lines:
                # 将多行合并成一个段落，保留换行以提高可读性
                paragraph = '\n'.join(current_lines)
                paragraphs.append(paragraph.strip())
                current_lines = []
                current_chars = 0

        current_lines.append(text)
        current_chars += len(text)

    # 添加最后一个段落
    if current_lines:
        paragraph = '\n'.join(current_lines)
        paragraphs.append(paragraph.strip())

    return '\n\n'.join(paragraphs)
