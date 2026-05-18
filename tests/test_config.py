"""config.py 冒烟测试"""

import pytest
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import Config


class TestConfig:
    def make_config(self, tmp_path, data=None):
        """创建临时 config.json 并返回 Config 实例"""
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(data or {}), encoding='utf-8'
        )
        return Config(config_path=str(config_path))

    def test_defaults_when_no_file(self, tmp_path):
        cfg = Config(config_path=str(tmp_path / "nonexistent.json"))
        assert cfg.get('whisper.model', 'base') == 'base'
        assert cfg.get('llm.enabled', False) is False

    def test_reads_values_from_file(self, tmp_path):
        cfg = self.make_config(tmp_path, {"output_dir": "my_output"})
        assert cfg.get('output_dir') == 'my_output'

    def test_dot_notation_nested_keys(self, tmp_path):
        cfg = self.make_config(tmp_path, {"whisper": {"model": "tiny"}})
        assert cfg.get('whisper.model') == 'tiny'
        assert cfg.get('whisper.device', 'cpu') == 'cpu'

    def test_set_and_get_nested(self, tmp_path):
        cfg = self.make_config(tmp_path)
        cfg.set('whisper.model', 'large')
        assert cfg.get('whisper.model') == 'large'

    def test_whisper_config_property(self, tmp_path):
        cfg = self.make_config(tmp_path, {
            "whisper": {"model": "small", "device": "cuda"}
        })
        wc = cfg.whisper_config
        assert wc['model'] == 'small'
        assert wc['device'] == 'cuda'
        assert wc['language'] == 'zh'

    def test_llm_config_property(self, tmp_path):
        cfg = self.make_config(tmp_path, {
            "llm": {"provider": "openai", "api_key": "sk-test"}
        })
        lc = cfg.llm_config
        assert lc['provider'] == 'openai'
        assert lc['api_key'] == 'sk-test'

    def test_output_dir_creates_directory(self, tmp_path):
        output_dir = tmp_path / "custom_output"
        cfg = self.make_config(tmp_path, {"output_dir": str(output_dir)})
        assert cfg.output_dir == output_dir
        assert output_dir.exists()
