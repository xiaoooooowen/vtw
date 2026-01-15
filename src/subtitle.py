"""
字幕下载模块
负责从 B站下载和解析字幕
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

from config import config
from utils import extract_bvid, merge_subtitles, retry_on_failure

logger = logging.getLogger(__name__)


class SubtitleDownloader:
    """字幕下载器"""

    def __init__(self):
        """初始化字幕下载器"""
        if yt_dlp is None:
            raise ImportError("请安装 yt-dlp: pip install yt-dlp")

        self.ydl_opts = {
            'quiet': False,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': True,
            'writeautomaticsub': True,  # 也下载自动生成的字幕
            'subtitleslangs': ['zh-Hans', 'zh-CN', 'zh-Hant', 'zh', 'zh-Hans-auto'],
            'skip_download': True,  # 只下载字幕，不下载视频
            'outtmpl': '%(id)s.%(ext)s',
        }

        # 如果配置了 cookies，添加到选项中
        cookies = config.bilibili_cookies
        if cookies:
            self.ydl_opts['cookiefile'] = cookies

    def download_subtitle(self, video_url: str, output_dir: Path) -> Optional[str]:
        """
        下载单个视频的字幕

        Args:
            video_url: B站视频 URL
            output_dir: 输出目录

        Returns:
            字幕文本，如果下载失败返回 None
        """
        try:
            bvid = extract_bvid(video_url)
            if not bvid:
                logger.warning(f"无法提取 BV 号: {video_url}")
                return None

            # 尝试下载字幕
            self.ydl_opts['outtmpl'] = str(output_dir / f'{bvid}.%(ext)s')

            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)

                if not info:
                    logger.warning(f"无法获取视频信息: {video_url}")
                    return None

                # 检查是否有字幕
                subtitles = info.get('subtitles', {})
                automatic_captions = info.get('automatic_captions', {})

                if not subtitles and not automatic_captions:
                    logger.info(f"视频无可用字幕: {video_url}")
                    return None

                # 查找下载的字幕文件
                subtitle_file = self._find_subtitle_file(output_dir, bvid)

                if subtitle_file and subtitle_file.exists():
                    logger.info(f"字幕下载成功: {subtitle_file}")
                    return self._parse_subtitle_to_text(subtitle_file)

                logger.warning(f"未找到字幕文件: {bvid}")
                return None

        except Exception as e:
            logger.error(f"下载字幕失败: {video_url}, 错误: {e}")
            return None

    def _find_subtitle_file(self, directory: Path, bvid: str) -> Optional[Path]:
        """
        查找字幕文件

        Args:
            directory: 搜索目录
            bvid: 视频 BV 号

        Returns:
            字幕文件路径，如果未找到返回 None
        """
        # 常见的字幕文件扩展名
        subtitle_extensions = ['.ass', '.srt', '.json', '.vtt']

        for ext in subtitle_extensions:
            # 尝试各种可能的文件名模式
            patterns = [
                f"{bvid}{ext}",
                f"{bvid}.zh-Hans{ext}",
                f"{bvid}.zh-CN{ext}",
                f"{bvid}.zh{ext}",
            ]

            for pattern in patterns:
                filepath = directory / pattern
                if filepath.exists():
                    return filepath

        # 搜索所有以 BV 号开头的字幕文件
        for filepath in directory.iterdir():
            if filepath.is_file() and filepath.stem.startswith(bvid):
                if filepath.suffix.lower() in subtitle_extensions:
                    return filepath

        return None

    def _parse_subtitle_to_text(self, subtitle_file: Path) -> Optional[str]:
        """
        解析字幕文件为纯文本

        Args:
            subtitle_file: 字幕文件路径

        Returns:
            字幕文本，如果解析失败返回 None
        """
        from utils import parse_subtitles, merge_subtitles

        try:
            subtitles = parse_subtitles(subtitle_file)
            if not subtitles:
                # 如果解析失败，尝试直接读取
                content = subtitle_file.read_text(encoding='utf-8')
                return content

            return merge_subtitles(subtitles)

        except Exception as e:
            logger.error(f"解析字幕文件失败: {subtitle_file}, 错误: {e}")

            # 回退方案：直接读取文件内容
            try:
                return subtitle_file.read_text(encoding='utf-8')
            except Exception:
                return None

    def get_video_info(self, video_url: str) -> Optional[Dict]:
        """
        获取视频信息

        Args:
            video_url: B站视频 URL

        Returns:
            视频信息字典，包含:
                - id: 视频 ID
                - title: 标题
                - description: 描述
                - upload_date: 上传日期
                - duration: 时长（秒）
                - url: 视频链接
        """
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(video_url, download=False)

                if not info:
                    return None

                return {
                    'id': info.get('id', ''),
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'upload_date': info.get('upload_date', ''),
                    'duration': info.get('duration', 0),
                    'url': f"https://www.bilibili.com/video/{info.get('id', '')}",
                }

        except Exception as e:
            logger.error(f"获取视频信息失败: {video_url}, 错误: {e}")
            return None


def get_up_videos(up_url: str, limit: Optional[int] = None) -> List[Dict]:
    """
    获取 UP 主的视频列表

    Args:
        up_url: UP 主空间 URL
        limit: 最多获取多少个视频

    Returns:
        视频信息列表
    """
    from utils import extract_uid
    import requests
    import time

    uid = extract_uid(up_url)
    if not uid:
        logger.error(f"无法从 URL 中提取 UID: {up_url}")
        return []

    videos = []
    page = 1

    logger.info(f"正在获取 UP 主视频列表: {up_url} (UID: {uid})")

    while True:
        api_url = f"https://api.bilibili.com/x/space/arc/search"
        params = {
            'mid': uid,
            'ps': 30,  # 每页数量
            'pn': page,
            'order': 'pubdate',  # 按发布时间排序
        }

        try:
            response = requests.get(api_url, params=params, timeout=10)
            data = response.json()

            if data.get('code') != 0:
                logger.error(f"获取视频列表失败: {data.get('message')}")
                break

            vlist = data.get('data', {}).get('list', {}).get('vlist', [])

            if not vlist:
                break

            for video in vlist:
                videos.append({
                    'id': video.get('bvid'),
                    'title': video.get('title'),
                    'url': f"https://www.bilibili.com/video/{video.get('bvid')}",
                    'description': video.get('description', ''),
                    'upload_date': video.get('created', ''),
                    'duration': video.get('length', ''),
                })

                if limit and len(videos) >= limit:
                    return videos[:limit]

            page += 1
            time.sleep(0.5)  # 避免请求过快

        except Exception as e:
            logger.error(f"请求失败: {e}")
            break

    logger.info(f"共获取到 {len(videos)} 个视频")
    return videos
