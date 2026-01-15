#!/usr/bin/env python3
"""
VTW - Bilibili 视频转文字工具
主程序入口
"""

import sys
import argparse
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from utils import (
    sanitize_filename,
    format_duration,
    format_date,
    generate_unique_filepath,
    convert_to_simplified,
    group_segments_to_paragraphs,
)
from subtitle import SubtitleDownloader, get_up_videos
from asr import ASREngine, transcribe_video
from verifier import create_verifier

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class MarkdownGenerator:
    """Markdown 文档生成器"""

    def __init__(self):
        """初始化生成器"""
        self.output_dir = config.output_dir
        self.include_metadata = config.include_metadata
        self.sanitize_filename = config.sanitize_filename
        self.convert_to_simplified = getattr(config, 'convert_to_simplified', True)
        self.format_paragraphs = getattr(config, 'format_paragraphs', True)

    def generate(
        self,
        video_info: Dict,
        text: str,
        segments: Optional[List[Dict]] = None,
        source: str = "subtitle",
        verification_info: Optional[Dict] = None
    ) -> Path:
        """
        生成 Markdown 文档

        Args:
            video_info: 视频信息字典
            text: 文本内容
            segments: Whisper 分段信息（可选，用于智能排版）
            source: 文本来源 ("subtitle" 或 "asr")
            verification_info: 校验信息（可选）

        Returns:
            生成的文件路径
        """
        # 准备文件名
        title = video_info.get('title', '未命名')
        if self.sanitize_filename:
            filename = f"{sanitize_filename(title)}.md"
        else:
            filename = f"{title}.md"

        filepath = generate_unique_filepath(self.output_dir, filename)

        # 智能排版（仅当有 segments 信息且来自 ASR 时）
        if self.format_paragraphs and segments and source == "asr":
            text = group_segments_to_paragraphs(segments)

        # 繁体转简体
        if self.convert_to_simplified:
            text = convert_to_simplified(text)

        # 生成内容
        content = self._generate_content(
            video_info,
            text,
            source,
            verification_info
        )

        # 写入文件
        filepath.write_text(content, encoding='utf-8')
        logger.info(f"✓ 已保存: {filepath}")

        return filepath

    def _generate_content(
        self,
        video_info: Dict,
        text: str,
        source: str,
        verification_info: Optional[Dict] = None
    ) -> str:
        """生成 Markdown 内容"""
        lines = []

        # 标题
        title = video_info.get('title', '未命名')
        lines.append(f"# {title}")
        lines.append("")

        # 元数据
        if self.include_metadata:
            lines.append("## 视频信息")
            lines.append("")
            lines.append(f"- **视频链接**: {video_info.get('url', '')}")

            upload_date = video_info.get('upload_date', '')
            if upload_date:
                formatted_date = format_date(upload_date)
                lines.append(f"- **上传时间**: {formatted_date}")

            duration = video_info.get('duration', 0)
            if duration:
                formatted_duration = format_duration(duration)
                lines.append(f"- **时长**: {formatted_duration}")

            lines.append(f"- **来源**: {'字幕' if source == 'subtitle' else '语音识别'}")

            if verification_info:
                lines.append(f"- **校验**: {verification_info.get('changes', '已校验')}")

            lines.append("")
            lines.append("## 转写文本")
            lines.append("")

        # 正文
        lines.append(text)
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"本文档由 [VTW](https://github.com/yourusername/vtw) 生成")

        return '\n'.join(lines)


class VideoProcessor:
    """视频处理器"""

    def __init__(self):
        """初始化处理器"""
        self.subtitle_downloader = SubtitleDownloader()
        self.asr_engine = None  # 延迟加载
        self.verifier = create_verifier()
        self.md_generator = MarkdownGenerator()

    def process_video(
        self,
        video_info: Dict,
        use_asr: bool = False
    ) -> bool:
        """
        处理单个视频

        Args:
            video_info: 视频信息
            use_asr: 是否强制使用语音识别

        Returns:
            处理是否成功
        """
        video_url = video_info['url']
        logger.info(f"\n{'='*60}")
        logger.info(f"处理视频: {video_info['title']}")
        logger.info(f"{'='*60}")

        # 优先尝试下载字幕
        text = None
        segments = None
        source = "unknown"

        if not use_asr:
            logger.info("尝试下载字幕...")
            text = self.subtitle_downloader.download_subtitle(
                video_url,
                config.output_dir
            )

            if text:
                source = "subtitle"
                logger.info("✓ 字幕下载成功")
            else:
                logger.info("✗ 无可用字幕，将使用语音识别")
                use_asr = True

        # 如果没有字幕或强制使用 ASR
        if use_asr:
            if self.asr_engine is None:
                logger.info("初始化语音识别引擎...")
                self.asr_engine = ASREngine()

            logger.info("正在进行语音识别...")
            result = transcribe_video(
                video_url,
                config.output_dir,
                self.asr_engine
            )

            if result:
                text = result.get('text', '')
                segments = result.get('segments', [])
                source = "asr"
                logger.info("✓ 语音识别完成")
            else:
                logger.error("✗ 语音识别失败")
                return False

        if not text or not text.strip():
            logger.error("✗ 未能获取文本内容")
            return False

        # 大模型校验
        verification_info = None
        if self.verifier:
            logger.info("正在进行文本校验...")
            verification_result = self.verifier.verify_text(text, video_info['title'])
            if verification_result:
                text = verification_result['text']
                verification_info = verification_result
                logger.info("✓ 校验完成")
            else:
                logger.info("跳过校验")

        # 生成 Markdown
        self.md_generator.generate(
            video_info,
            text,
            segments if source == "asr" else None,
            source,
            verification_info
        )

        return True

    def process_videos(
        self,
        videos: List[Dict],
        force_asr: bool = False
    ) -> Dict[str, int]:
        """
        批量处理视频

        Args:
            videos: 视频列表
            force_asr: 是否强制使用语音识别

        Returns:
            处理统计信息
        """
        total = len(videos)
        success = 0
        failed = 0
        skipped = 0

        logger.info(f"\n开始处理 {total} 个视频...")

        for idx, video in enumerate(videos, 1):
            logger.info(f"\n[{idx}/{total}]")

            try:
                result = self.process_video(video, force_asr)

                if result:
                    success += 1
                else:
                    failed += 1

                # 请求间隔
                if idx < total:
                    delay = config.delay_between_requests
                    if delay > 0:
                        time.sleep(delay)

            except KeyboardInterrupt:
                logger.info("\n\n用户中断，正在退出...")
                break
            except Exception as e:
                logger.error(f"处理出错: {e}")
                failed += 1
                continue

        logger.info(f"\n{'='*60}")
        logger.info(f"处理完成！")
        logger.info(f"  成功: {success}")
        logger.info(f"  失败: {failed}")
        logger.info(f"{'='*60}\n")

        return {
            'total': total,
            'success': success,
            'failed': failed,
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='VTW - Bilibili 视频转文字工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理 UP 主的所有视频
  python vtw.py https://space.bilibili.com/123456

  # 处理单个视频
  python vtw.py https://www.bilibili.com/video/BV1xx411c7mD

  # 限制处理最近 10 个视频
  python vtw.py https://space.bilibili.com/123456 -l 10

  # 强制使用语音识别
  python vtw.py https://www.bilibili.com/video/BV1xx411c7mD --asr
        """
    )

    parser.add_argument(
        'url',
        help='B站视频 URL 或 UP 主空间 URL'
    )
    parser.add_argument(
        '-l', '--limit',
        type=int,
        help='最多处理多少个视频（仅 UP 主模式）'
    )
    parser.add_argument(
        '-o', '--output',
        help='输出目录（覆盖配置文件）'
    )
    parser.add_argument(
        '--asr',
        action='store_true',
        help='强制使用语音识别（不下载字幕）'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细日志'
    )

    args = parser.parse_args()

    # 配置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 覆盖输出目录
    if args.output:
        config.output_dir = Path(args.output)
        config.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 判断是 UP 主还是单个视频
        if '/video/' in args.url or 'BV' in args.url:
            # 单个视频
            logger.info("检测到单个视频")

            downloader = SubtitleDownloader()
            video_info = downloader.get_video_info(args.url)

            if not video_info:
                logger.error("无法获取视频信息")
                sys.exit(1)

            processor = VideoProcessor()
            result = processor.process_video(video_info, args.asr)

            if result:
                logger.info("✓ 处理成功")
                sys.exit(0)
            else:
                logger.error("✗ 处理失败")
                sys.exit(1)

        else:
            # UP 主
            logger.info("检测到 UP 主空间")

            # 获取视频列表
            videos = get_up_videos(args.url, args.limit)

            if not videos:
                logger.error("未找到视频")
                sys.exit(1)

            # 确认
            print(f"\n即将处理 {len(videos)} 个视频，继续吗？")
            confirm = input("输入 'yes' 继续: ")
            if confirm.lower() != 'yes':
                print("已取消")
                sys.exit(0)

            # 批量处理
            processor = VideoProcessor()
            stats = processor.process_videos(videos, args.asr)

            if stats['failed'] == 0:
                sys.exit(0)
            else:
                sys.exit(1)

    except Exception as e:
        logger.error(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
