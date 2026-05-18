# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: for Traditional-to-Simplified Chinese conversion
pip install opencc

# Setup config (copy template, then edit config.json)
cp config.example.json config.json

# Run CLI — single video
python src/vtw.py https://www.bilibili.com/video/BV1xx411c7mD

# Run CLI — UP主 space (all videos), with limit
python src/vtw.py https://space.bilibili.com/123456 -l 10

# Run CLI — force ASR mode, verbose logging, custom output dir
python src/vtw.py <url> --asr -v -o ./my_output

# Run GUI
python src/gui.py
```

## Architecture

VTW is a three-stage pipeline for converting Bilibili videos to Markdown:

```
URL → [SubtitleDownloader] → text  (fast: seconds)
    ↓  (fallback if no subtitles)
    [ASREngine + BilibiliAudioExtractor] → text + segments  (slow: minutes)
    ↓  (optional, config-driven)
    [Verifier (TextVerifier | KnowledgeVerifier)] → refined text
    ↓
    [MarkdownGenerator] → .md file
```

**Stage 1 — Text extraction** (`subtitle.py` + `asr.py`):
- `SubtitleDownloader` uses yt-dlp to fetch Bilibili subtitles (JSON/SRT/VTT). This is the preferred path when subtitles exist.
- When subtitles are unavailable (or `--asr` flag is set), falls back to `ASREngine` (faster-whisper, default model: `base`, CPU, int8) via `BilibiliAudioExtractor` (yt-dlp extracts audio, ffmpeg converts it).

**Stage 2 — Optional LLM verification** (`verifier.py`):
- Only runs if `llm.enabled` is `true` in `config.json`.
- `TextVerifier`: basic text cleanup (typos, punctuation).
- `KnowledgeVerifier`: AI-powered structuring — auto-generates chapter titles, chapter summaries, and an overall summary. Uses OpenAI-compatible API (DeepSeek or OpenAI). The LLM returns JSON that is parsed and structured.

**Stage 3 — Markdown generation** (`vtw.py` → `MarkdownGenerator`):
- Three output layouts: standard mode (metadata + transcript), knowledge mode with summary at top, knowledge mode without summary.
- `utils.py` handles filename sanitization, Traditional-to-Simplified conversion (opencc), paragraph merging, and duration formatting.

**Two entry points, one core**:
- `vtw.py`: CLI entry. Contains `VideoProcessor` (orchestrator) and `MarkdownGenerator`. Argument parsing via argparse.
- `gui.py`: Tkinter GUI entry. Wraps `VideoProcessor` in a background thread with progress/status callbacks.
- Both share the same `VideoProcessor.process_video()` / `process_videos()` methods.

**URL detection**: `subtitle.py`'s `get_up_videos()` detects whether a URL is a single video or a UP主 space. For UP主 URLs, it resolves the UID (via API if a username is provided) and fetches all video entries.

## Configuration

`config.py` loads `config.json` as a singleton and exposes attributes via dot-notation keys (`llm.enabled`, `whisper.model`, etc.). Runtime overrides use `config.set(key, value)`. `config.json` is git-ignored (contains API keys); `config.example.json` is the tracked template.

Key config sections: `whisper`, `llm`, `knowledge_mode`, `bilibili`, `processing`, `markdown`.

## Environment

- Developed on Windows. The `.bat` launchers hardcode `C:\Users\27970\AppData\Local\Programs\Python\Python313\python.exe`.
- `asr.py` sets `HF_ENDPOINT=https://hf-mirror.com` for faster Whisper model downloads in China.
- No test suite, no linter config, no CI/CD.
