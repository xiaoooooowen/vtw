"""
语音识别模块
使用 faster-whisper 进行本地语音识别
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, List

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from config import config

# 设置 Hugging Face 镜像（国内用户）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

logger = logging.getLogger(__name__)


class ASREngine:
    """语音识别引擎"""

    def __init__(self):
        """初始化语音识别引擎"""
        if WhisperModel is None:
            raise ImportError("请安装 faster-whisper: pip install faster-whisper")

        whisper_config = config.whisper_config
        models_dir = config.models_dir

        logger.info(f"正在加载 Whisper 模型: {whisper_config['model']}")
        logger.info(f"设备: {whisper_config['device']}, 计算类型: {whisper_config['compute_type']}")

        self.model = WhisperModel(
            whisper_config['model'],
            device=whisper_config['device'],
            compute_type=whisper_config['compute_type'],
            download_root=str(models_dir),
        )

        self.language = whisper_config['language']
        logger.info("Whisper 模型加载完成")

    def transcribe_audio(
        self,
        audio_file: Path,
        verbose: bool = False
    ) -> Optional[Dict]:
        """
        识别音频文件

        Args:
            audio_file: 音频文件路径
            verbose: 是否显示详细进度

        Returns:
            识别结果字典，包含:
                - text: 完整文本
                - segments: 分段信息列表
                - duration: 时长（秒）
        """
        if not audio_file.exists():
            logger.error(f"音频文件不存在: {audio_file}")
            return None

        try:
            logger.info(f"正在识别音频: {audio_file}")

            segments, info = self.model.transcribe(
                str(audio_file),
                language=self.language,
                beam_size=5,
                vad_filter=False,  # 禁用 VAD 滤波器
            )

            detected_language = info.language
            language_probability = info.language_probability

            logger.info(
                f"检测到语言: {detected_language} "
                f"(概率: {language_probability:.2f})"
            )

            # 收集分段信息
            segments_list = []
            full_text_parts = []

            for segment in segments:
                text = segment.text.strip()
                segments_list.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': text,
                })
                if text:  # 只添加非空文本
                    full_text_parts.append(text)

                if verbose:
                    logger.debug(
                        f"[{segment.start:.2f}s -> {segment.end:.2f}s] "
                        f"{segment.text}"
                    )

            # 调试信息
            logger.info(f"共识别到 {len(segments_list)} 个分段")
            if full_text_parts:
                logger.info(f"文本总长度: {len(''.join(full_text_parts))} 字符")
            else:
                logger.warning("所有分段文本为空")

            duration = info.duration

            result = {
                'text': '\n'.join(full_text_parts),
                'segments': segments_list,
                'duration': duration,
            }

            logger.info(f"识别完成，时长: {duration:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"语音识别失败: {audio_file}, 错误: {e}")
            return None


class BilibiliAudioExtractor:
    """B站音频提取器"""

    def __init__(self):
        """初始化音频提取器"""
        try:
            import yt_dlp
            self.yt_dlp = yt_dlp
        except ImportError:
            raise ImportError("请安装 yt-dlp: pip install yt-dlp")

    def extract_audio(
        self,
        video_url: str,
        output_dir: Path,
        audio_format: str = 'mp3'
    ) -> Optional[Path]:
        """
        从视频 URL 提取音频

        Args:
            video_url: B站视频 URL
            output_dir: 输出目录
            audio_format: 音频格式

        Returns:
            音频文件路径，提取失败返回 None
        """
        from utils import extract_bvid

        bvid = extract_bvid(video_url)
        if not bvid:
            logger.error(f"无法提取 BV 号: {video_url}")
            return None

        output_template = str(output_dir / f'{bvid}.%(ext)s')

        # 查找 ffmpeg 路径
        ffmpeg_path = None
        possible_paths = [
            r'C:\Users\27970\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe',
            r'C:\Users\27970\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe',
        ]
        for path in possible_paths:
            if Path(path).exists():
                ffmpeg_path = path
                break

        ydl_opts = {
            'quiet': False,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': '192',
            }],
            'outtmpl': output_template,
            'overwrites': True,
        }

        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_path
            logger.info(f"使用 ffmpeg: {ffmpeg_path}")

        try:
            logger.info(f"正在提取音频: {video_url}")

            with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(video_url, download=True)

            # 查找提取的音频文件
            audio_file = self._find_audio_file(output_dir, bvid, audio_format)

            if audio_file and audio_file.exists():
                logger.info(f"音频提取成功: {audio_file}")
                return audio_file

            logger.warning(f"未找到音频文件: {bvid}")
            return None

        except Exception as e:
            logger.error(f"提取音频失败: {video_url}, 错误: {e}")
            return None

    def _find_audio_file(
        self,
        directory: Path,
        bvid: str,
        audio_format: str
    ) -> Optional[Path]:
        """
        查找音频文件

        Args:
            directory: 搜索目录
            bvid: 视频 BV 号
            audio_format: 音频格式

        Returns:
            音频文件路径，如果未找到返回 None
        """
        audio_file = directory / f'{bvid}.{audio_format}'

        if audio_file.exists():
            return audio_file

        # 搜索所有以 BV 号开头的音频文件
        for filepath in directory.iterdir():
            if filepath.is_file() and filepath.stem.startswith(bvid):
                if filepath.suffix.lower() == f'.{audio_format}':
                    return filepath

        return None


def transcribe_video(
    video_url: str,
    output_dir: Path,
    asr_engine: ASREngine,
    keep_audio: bool = False
) -> Optional[Dict]:
    """
    转写视频音频

    Args:
        video_url: B站视频 URL
        output_dir: 输出目录
        asr_engine: ASR 引擎实例
        keep_audio: 是否保留音频文件

    Returns:
        转写结果，转写失败返回 None
    """
    extractor = BilibiliAudioExtractor()

    # 提取音频
    audio_file = extractor.extract_audio(video_url, output_dir)

    if not audio_file:
        return None

    try:
        # 识别音频
        result = asr_engine.transcribe_audio(audio_file)

        # 删除音频文件
        if not keep_audio:
            try:
                audio_file.unlink()
                logger.info(f"已删除音频文件: {audio_file}")
            except Exception as e:
                logger.warning(f"删除音频文件失败: {e}")

        return result

    except Exception as e:
        logger.error(f"转写视频失败: {video_url}, 错误: {e}")
        return None
