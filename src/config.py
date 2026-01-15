"""
配置管理模块
负责加载和管理应用程序配置
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """配置管理类"""

    def __init__(self, config_path: str = "config.json"):
        """
        初始化配置

        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            return {}

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键，支持点号分隔的嵌套键，如 "whisper.model"
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        设置配置项

        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self):
        """保存配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    @property
    def output_dir(self) -> Path:
        """获取输出目录"""
        dir_path = Path(self.get('output_dir', 'output'))
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    @property
    def models_dir(self) -> Path:
        """获取模型缓存目录"""
        dir_path = Path('models')
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    @property
    def whisper_config(self) -> Dict[str, Any]:
        """获取 Whisper 配置"""
        return {
            'model': self.get('whisper.model', 'base'),
            'device': self.get('whisper.device', 'cpu'),
            'compute_type': self.get('whisper.compute_type', 'int8'),
            'language': self.get('whisper.language', 'zh'),
        }

    @property
    def llm_enabled(self) -> bool:
        """检查是否启用大模型校验"""
        return self.get('llm.enabled', False)

    @property
    def llm_config(self) -> Dict[str, Any]:
        """获取大模型配置"""
        return {
            'provider': self.get('llm.provider', 'deepseek'),
            'api_key': self.get('llm.api_key', ''),
            'base_url': self.get('llm.base_url', 'https://api.deepseek.com/v1'),
            'model': self.get('llm.model', 'deepseek-chat'),
        }

    @property
    def bilibili_cookies(self) -> str:
        """获取 B站 Cookies"""
        return self.get('bilibili.cookies', '')

    @property
    def max_workers(self) -> int:
        """获取最大并发数"""
        return self.get('processing.max_workers', 1)

    @property
    def retry_count(self) -> int:
        """获取重试次数"""
        return self.get('processing.retry_count', 3)

    @property
    def delay_between_requests(self) -> float:
        """获取请求间隔（秒）"""
        return self.get('processing.delay_between_requests', 1.0)

    @property
    def include_metadata(self) -> bool:
        """是否包含元数据"""
        return self.get('markdown.include_metadata', True)

    @property
    def sanitize_filename(self) -> bool:
        """是否清理文件名"""
        return self.get('markdown.sanitize_filename', True)

    @property
    def convert_to_simplified(self) -> bool:
        """是否转换为简体中文"""
        return self.get('markdown.convert_to_simplified', True)

    @property
    def format_paragraphs(self) -> bool:
        """是否格式化为段落"""
        return self.get('markdown.format_paragraphs', True)


# 全局配置实例
config = Config()
