"""utils.py 冒烟测试"""

import pytest
from pathlib import Path

# 确保 src 在 path 中
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import (
    sanitize_filename,
    extract_bvid,
    extract_uid,
    format_duration,
    format_date,
    generate_unique_filepath,
    is_single_video_url,
    is_up_space_url,
)


class TestSanitizeFilename:
    def test_removes_invalid_chars(self):
        result = sanitize_filename('test<file>:name?.txt')
        assert '<' not in result
        assert ':' not in result
        assert '?' not in result

    def test_strips_dots_and_spaces(self):
        assert sanitize_filename('  hello  ') == 'hello'
        assert sanitize_filename('...test...') == 'test'

    def test_handles_all_invalid_chars(self):
        # 所有非法字符被替换为 _，结果不为空所以不触发 'unnamed'
        assert sanitize_filename('<:>') == '___'

    def test_fallback_to_unnamed(self):
        # 只有空格和点，去掉后为空，fallback 为 'unnamed'
        assert sanitize_filename('  .  ') == 'unnamed'

    def test_truncates_long_name(self):
        long_name = 'a' * 250
        result = sanitize_filename(long_name, max_length=200)
        assert len(result) == 200


class TestExtractBvid:
    def test_extracts_bv_from_url(self):
        url = 'https://www.bilibili.com/video/BV1xx411c7mD'
        assert extract_bvid(url) == 'BV1xx411c7mD'

    def test_extracts_bv_with_params(self):
        url = 'https://www.bilibili.com/video/BV1xx411c7mD?p=1&t=100'
        assert extract_bvid(url) == 'BV1xx411c7mD'

    def test_returns_none_for_no_bv(self):
        assert extract_bvid('https://www.bilibili.com/') is None

    def test_bv_format_is_exact(self):
        assert extract_bvid('BV1aA2bB3cC4') == 'BV1aA2bB3cC4'
        assert extract_bvid('BV1') is None


class TestExtractUid:
    def test_extracts_numeric_uid(self):
        url = 'https://space.bilibili.com/123456'
        assert extract_uid(url) == '123456'

    def test_extracts_trailing_digits(self):
        assert extract_uid('https://example.com/789') == '789'

    def test_returns_none_for_no_match(self):
        assert extract_uid('https://example.com/abc') is None


class TestFormatDuration:
    def test_minutes_only(self):
        assert format_duration(125) == '2:05'

    def test_hours_minutes_seconds(self):
        assert format_duration(3661) == '1:01:01'

    def test_zero_seconds(self):
        assert format_duration(0) == '0:00'


class TestFormatDate:
    def test_formats_valid_date(self):
        assert format_date('20240115') == '2024-01-15'

    def test_passes_through_invalid(self):
        assert format_date('abc') == 'abc'
        assert format_date('') == ''


class TestGenerateUniqueFilepath:
    def test_returns_original_if_not_exists(self, tmp_path):
        result = generate_unique_filepath(tmp_path, 'test.md')
        assert result == tmp_path / 'test.md'

    def test_adds_suffix_if_exists(self, tmp_path):
        (tmp_path / 'test.md').write_text('existing')
        (tmp_path / 'test_1.md').write_text('existing')
        result = generate_unique_filepath(tmp_path, 'test.md')
        assert result == tmp_path / 'test_2.md'


class TestUrlDetection:
    def test_single_video_url(self):
        assert is_single_video_url('https://www.bilibili.com/video/BV1xx411c7mD')
        assert is_single_video_url('https://b23.tv/BV1xx411c7mD')

    def test_up_space_url(self):
        assert is_up_space_url('https://space.bilibili.com/123456')
        assert is_up_space_url('https://space.bilibili.com/@username')
