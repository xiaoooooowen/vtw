# Copilot Instructions for VTW Project

Welcome to the VTW project! This document provides essential guidelines for AI coding agents to effectively contribute to this codebase. Please follow the instructions below to ensure consistency and maintainability.

## Project Overview

VTW is a tool designed to convert Bilibili videos into Markdown documents for learning and knowledge organization. Key features include:
- Dual-mode text extraction: prioritizing subtitles, falling back to speech recognition.
- Local speech recognition using `faster-whisper`.
- Optional validation with large language models (LLMs) like DeepSeek or OpenAI.
- Batch processing of videos.
- Markdown output with structured formatting.

## Codebase Structure

The project is organized as follows:

```
vtw/
├── src/
│   ├── vtw.py           # Main entry point
│   ├── config.py        # Configuration management
│   ├── subtitle.py      # Subtitle processing
│   ├── asr.py           # Speech recognition
│   ├── verifier.py      # LLM-based validation
│   └── utils.py         # Utility functions
├── output/              # Generated Markdown files
├── models/              # Whisper model cache
├── config.json          # Configuration file
├── requirements.txt     # Python dependencies
└── README.md            # Project documentation
```

## Key Patterns and Conventions

1. **Configuration Management**:
   - All configurations are centralized in `config.json`.
   - Use `config.py` to load and validate configurations.

2. **Speech Recognition**:
   - Implemented in `asr.py` using `faster-whisper`.
   - Supports multiple models (`tiny`, `base`, `small`, etc.) and devices (`cpu`, `cuda`).

3. **Subtitle Processing**:
   - Handled in `subtitle.py`.
   - Extracts and formats subtitles for Markdown output.

4. **Validation with LLMs**:
   - Optional step implemented in `verifier.py`.
   - Supports multiple providers (DeepSeek, OpenAI) via API.

5. **Output Format**:
   - Markdown files follow a consistent structure with metadata (e.g., video link, duration) and transcribed content.

## Developer Workflows

### Installation

Install dependencies using:
```bash
pip install -r requirements.txt
```

### Running the Tool

Examples:
```bash
# Process all videos from a Bilibili user
python src/vtw.py https://space.bilibili.com/123456

# Process a single video
python src/vtw.py https://www.bilibili.com/video/BV1xx411c7mD
```

### Testing and Debugging

- Use verbose mode (`-v`) for detailed logs.
- Modify `config.json` to test different configurations.

### Common Issues

- **Model download issues**: Use a mirror for Hugging Face models.
- **Slow processing**: Use smaller models or enable GPU acceleration.

## External Dependencies

- `faster-whisper`: For local speech recognition.
- `yt-dlp`: For downloading videos and subtitles.
- Optional: DeepSeek/OpenAI APIs for validation.

## Contribution Guidelines

- Follow the existing project structure and patterns.
- Document any new modules or significant changes in the `README.md`.
- Ensure all configurations are managed via `config.json`.

---

For more details, refer to the `README.md` file or the source code in the `src/` directory.