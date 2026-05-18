#!/usr/bin/env python3
"""
VTW - Bilibili 视频转文字工具
主程序入口
"""

import sys
import argparse
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    is_single_video_url,
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

    def __init__(self, config_obj=None):
        """初始化生成器"""
        self.config = config_obj if config_obj is not None else config
        self.output_dir = self.config.output_dir
        self.include_metadata = self.config.include_metadata
        self.sanitize_filename = self.config.sanitize_filename
        self.convert_to_simplified = getattr(self.config, 'convert_to_simplified', True)
        self.format_paragraphs = getattr(self.config, 'format_paragraphs', True)

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

        # 知识模式：在开头添加总体总结
        if verification_info and verification_info.get('type') == 'knowledge':
            if self.config.add_summary_at_top:
                lines.extend(self._generate_summary_section(verification_info))

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
                lines.append(f"- **处理模式**: {'知识模式' if verification_info.get('type') == 'knowledge' else '标准模式'}")

            lines.append("")

            # 知识模式的转写文本标题不同
            if verification_info and verification_info.get('type') == 'knowledge':
                lines.append("## 详细内容")
            else:
                lines.append("## 转写文本")
            lines.append("")

        # 正文
        if verification_info and verification_info.get('type') == 'knowledge':
            # 知识模式：生成结构化的章节内容
            lines.extend(self._generate_knowledge_content(verification_info))
        else:
            # 标准模式：直接使用文本
            lines.append(text)

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"本文档由 [VTW](https://github.com/xiaoooooowen/vtw) 生成")

        return '\n'.join(lines)

    def _generate_summary_section(self, verification_info: Dict) -> List[str]:
        """生成总结部分（开头）"""
        lines = []
        summary = verification_info.get('summary')
        if summary:
            lines.append("## 内容总结")
            lines.append("")
            lines.append(summary)
            lines.append("")
        return lines

    def _generate_knowledge_content(self, verification_info: Dict) -> List[str]:
        """生成知识类章节内容"""
        lines = []
        chapters = verification_info.get('chapters', [])

        for idx, chapter in enumerate(chapters, 1):
            # 章节标题
            title = chapter.get('title', '未命名章节')
            if self.config.chapter_numbering:
                lines.append(f"### {idx}. {title}")
            else:
                lines.append(f"### {title}")
            lines.append("")

            # 章节小结
            if self.config.show_chapter_summary:
                summary = chapter.get('summary', '')
                if summary:
                    lines.append(f"> {summary}")
                    lines.append("")

            # 章节内容
            content = chapter.get('content', '')
            lines.append(content)
            lines.append("")

        return lines


class VideoProcessor:
    """视频处理器"""

    def __init__(self, config_obj=None):
        """初始化处理器"""
        self.config = config_obj if config_obj is not None else config
        self.subtitle_downloader = SubtitleDownloader(self.config)
        self.asr_engine = None  # 延迟加载
        self.verifier = create_verifier(self.config)
        self.md_generator = MarkdownGenerator(self.config)
        self.stop_event = threading.Event()

    def get_video_info(self, video_url: str) -> Optional[Dict]:
        """获取视频信息（委托给 SubtitleDownloader）"""
        return self.subtitle_downloader.get_video_info(video_url)

    def cleanup(self):
        """释放资源（卸载 ASR 模型等）"""
        if self.asr_engine is not None:
            self.asr_engine.unload()
            self.asr_engine = None

    def process_video(
        self,
        video_info: Dict,
        use_asr: bool = False,
        subtitle_only: bool = False
    ) -> bool:
        """
        处理单个视频

        Args:
            video_info: 视频信息
            use_asr: 是否强制使用语音识别
            subtitle_only: 仅提取字幕，跳过 ASR 和 LLM

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
                self.config.output_dir
            )

            if text:
                source = "subtitle"
                logger.info("✓ 字幕下载成功")
            else:
                logger.info("✗ 无可用字幕，将使用语音识别")
                use_asr = True

        if self.stop_event.is_set():
            logger.info("用户请求停止，跳过当前视频")
            return False

        if subtitle_only and not text:
            logger.info("✗ 无可用字幕（subtitle-only 模式不启用 ASR）")
            return False

        # 如果没有字幕或强制使用 ASR（subtitle-only 模式跳过）
        if use_asr and not subtitle_only:
            if self.asr_engine is None:
                logger.info("初始化语音识别引擎...")
                self.asr_engine = ASREngine()

            logger.info("正在进行语音识别...")
            result = transcribe_video(
                video_url,
                self.config.output_dir,
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

        if self.stop_event.is_set():
            logger.info("用户请求停止，跳过 LLM 处理")
            return False

        # 大模型校验（subtitle-only 模式跳过）
        verification_info = None
        if not subtitle_only and self.verifier and not self.stop_event.is_set():
            logger.info("正在进行文本校验...")
            video_description = video_info.get('description', '')
            verification_result = self.verifier.verify_text(
                text,
                video_info['title'],
                video_description
            )
            if verification_result:
                # 知识模式：使用结构化数据，不覆盖原始文本
                if verification_result.get('type') == 'knowledge':
                    verification_info = verification_result
                    logger.info(f"✓ 知识模式处理完成")
                else:
                    # 标准模式：使用校验后的文本
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
        force_asr: bool = False,
        subtitle_only: bool = False,
        no_resume: bool = False
    ) -> Dict[str, int]:
        """
        批量处理视频

        Args:
            videos: 视频列表
            force_asr: 是否强制使用语音识别
            subtitle_only: 仅提取字幕
            no_resume: 禁用断点续传

        Returns:
            处理统计信息
        """
        import json

        total = len(videos)
        success = 0
        failed = 0
        failed_list = []
        max_workers = self.config.max_workers

        # 断点续传：加载已完成的视频
        progress_file = self.config.output_dir / '.vtw_progress.json'
        completed_urls = set()
        if not no_resume and progress_file.exists():
            try:
                progress_data = json.loads(progress_file.read_text(encoding='utf-8'))
                completed_urls = set(progress_data.get('completed', []))
                skipped = sum(1 for v in videos if v.get('url') in completed_urls)
                if skipped > 0:
                    logger.info(f"断点续传: 跳过 {skipped} 个已完成的视频")
            except Exception as e:
                logger.warning(f"读取进度文件失败，将重新处理全部: {e}")

        logger.info(f"\n开始处理 {total} 个视频（max_workers={max_workers}）...")

        def save_progress():
            if no_resume:
                return
            completed = list(completed_urls)
            try:
                progress_file.write_text(
                    json.dumps({'completed': completed}, ensure_ascii=False),
                    encoding='utf-8'
                )
            except Exception as e:
                logger.warning(f"保存进度文件失败: {e}")

        def handle_result(video, result):
            nonlocal success, failed
            if result:
                success += 1
                url = video.get('url', '')
                if url:
                    completed_urls.add(url)
                    save_progress()
            else:
                failed += 1
                failed_list.append({
                    'title': video.get('title', ''),
                    'url': video.get('url', ''),
                    'reason': '处理失败',
                })

        if max_workers <= 1:
            # 串行处理
            for idx, video in enumerate(videos, 1):
                if self.stop_event.is_set():
                    logger.info("用户请求停止，结束批处理")
                    break
                video_url = video.get('url', '')
                if video_url in completed_urls:
                    logger.info(f"\n[{idx}/{total}] 跳过（已完成）: {video.get('title', '')}")
                    success += 1
                    continue
                logger.info(f"\n[{idx}/{total}]")
                try:
                    result = self.process_video(video, force_asr, subtitle_only)
                    handle_result(video, result)
                    if idx < total:
                        delay = self.config.delay_between_requests
                        if delay > 0:
                            time.sleep(delay)
                except KeyboardInterrupt:
                    logger.info("\n\n用户中断，正在退出...")
                    break
                except Exception as e:
                    logger.error(f"处理出错: {e}")
                    failed += 1
                    failed_list.append({
                        'title': video.get('title', ''),
                        'url': video.get('url', ''),
                        'reason': str(e),
                    })
                    continue
        else:
            # 并发处理：过滤已完成的视频
            pending_videos = [
                v for v in videos if v.get('url') not in completed_urls
            ]
            already_done = len(videos) - len(pending_videos)
            success += already_done
            if already_done > 0:
                logger.info(f"断点续传: 跳过 {already_done} 个已完成的视频")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_video = {
                    executor.submit(self.process_video, video, force_asr, subtitle_only): video
                    for video in pending_videos
                }
                for future in as_completed(future_to_video):
                    video = future_to_video[future]
                    try:
                        result = future.result()
                        handle_result(video, result)
                    except Exception as e:
                        logger.error(f"处理出错 [{video.get('title', '')}]: {e}")
                        failed += 1
                        failed_list.append({
                            'title': video.get('title', ''),
                            'url': video.get('url', ''),
                            'reason': str(e),
                        })

        # 输出失败汇总
        self._write_failed_report(failed_list)

        logger.info(f"\n{'='*60}")
        logger.info(f"处理完成！")
        logger.info(f"  成功: {success}")
        logger.info(f"  失败: {failed}")
        if failed_list:
            logger.info(f"  失败列表:")
            for item in failed_list:
                logger.info(f"    - {item['title']}: {item['reason']}")
        logger.info(f"{'='*60}\n")

        return {
            'total': total,
            'success': success,
            'failed': failed,
        }

    def _write_failed_report(self, failed_list: list):
        """将失败列表写入 JSON 文件"""
        if not failed_list:
            return
        import json
        report_path = self.config.output_dir / '_failed.json'
        try:
            report_path.write_text(
                json.dumps(failed_list, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            logger.info(f"失败报告已保存: {report_path}")
        except Exception as e:
            logger.warning(f"写入失败报告出错: {e}")


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
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='跳过确认提示，直接开始处理'
    )
    parser.add_argument(
        '--subtitle-only',
        action='store_true',
        help='仅提取字幕，不启用 ASR 和大模型处理'
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='禁用断点续传，重新处理全部视频'
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
        if is_single_video_url(args.url):
            # 单个视频
            logger.info("检测到单个视频")

            processor = VideoProcessor()
            video_info = processor.get_video_info(args.url)

            if not video_info:
                logger.error("无法获取视频信息")
                sys.exit(1)

            result = processor.process_video(video_info, args.asr, args.subtitle_only)

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
            if not args.yes:
                print(f"\n即将处理 {len(videos)} 个视频，继续吗？")
                confirm = input("输入 'yes' 继续: ")
                if confirm.lower() != 'yes':
                    print("已取消")
                    sys.exit(0)

            # 批量处理
            processor = VideoProcessor()
            stats = processor.process_videos(
                videos, args.asr, args.subtitle_only, args.no_resume
            )

            if stats['failed'] == 0:
                sys.exit(0)
            else:
                sys.exit(1)

    except Exception as e:
        logger.error(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
