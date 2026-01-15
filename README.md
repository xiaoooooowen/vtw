# VTW - Bilibili 视频转文字工具

批量将 Bilibili UP 主视频转换为 Markdown 文档，方便学习记录和知识整理。

## 功能特性

- **双模式文字提取**：优先下载 B站字幕，无字幕时使用语音识别
- **本地语音识别**：使用 faster-whisper，免费、准确
- **繁体转简体**：自动将繁体字转换为简体字（可配置）
- **智能段落排版**：基于语音停顿智能组织段落（可配置）
- **大模型校验**（可选）：支持 DeepSeek、OpenAI 等大模型 API 优化识别结果
- **批量处理**：支持获取 UP 主所有视频并批量转换
- **智能命名**：自动清理文件名，避免冲突
- **Markdown 格式**：生成格式规范的 Markdown 文档

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

编辑 `config.json` 文件，根据需要配置：

```json
{
  "output_dir": "output",
  "whisper": {
    "model": "base",
    "device": "cpu",
    "compute_type": "int8"
  },
  "llm": {
    "enabled": false,
    "provider": "deepseek",
    "api_key": "your-api-key"
  },
  "markdown": {
    "include_metadata": true,
    "sanitize_filename": true,
    "convert_to_simplified": true,
    "format_paragraphs": true
  }
}
```

### Markdown 配置说明

- **繁体转简体**：自动将繁体字转换为简体字
- **智能段落排版**：基于语音停顿智能组织段落（保留换行，提高可读性）
- 可通过配置文件控制是否启用此功能

### 使用示例

```bash
# 处理 UP 主的所有视频
python src/vtw.py https://space.bilibili.com/123456

# 处理单个视频
python src/vtw.py https://www.bilibili.com/video/BV1xx411c7mD

# 限制处理最近 10 个视频
python src/vtw.py https://space.bilibili.com/123456 -l 10

# 强制使用语音识别
python src/vtw.py https://www.bilibili.com/video/BV1xx411c7mD --asr
```

## 配置说明

### Whisper 配置

| 参数 | 说明 | 可选值 |
|------|------|--------|
| model | 模型大小 | tiny/base/small/medium/large |
| device | 运行设备 | cpu/cuda |
| compute_type | 计算类型 | int8/float16 |

**模型性能对比**：

| 模型 | 大小 | CPU 处理 1 小时视频 |
|------|------|---------------------|
| tiny | 39MB | ~3-5 分钟 |
| base | 74MB | ~8-15 分钟 |
| small | 244MB | ~15-25 分钟 |

### 大模型校验配置

如需启用大模型校验，在 `config.json` 中设置：

```json
{
  "llm": {
    "enabled": true,
    "provider": "deepseek",
    "api_key": "sk-...",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat"
  }
}
```

支持的大模型：

- **DeepSeek**: 默认推荐，性价比高
- **OpenAI**: 设置 `base_url` 为 `https://api.openai.com/v1`
- 其他兼容 OpenAI API 的服务

## 输出格式

生成的 Markdown 文档结构：

```markdown
# 视频标题

## 视频信息

- **视频链接**: https://www.bilibili.com/video/BV...
- **上传时间**: 2024-01-15
- **时长**: 10:30
- **来源**: 字幕 / 语音识别（带简体转换和段落排版）
- **校验**: 已校验（可选）

## 转写文本

视频的文字内容...

---

本文档由 VTW 生成
```

## 命令行参数

| 参数 | 说明 |
|------|------|
| `url` | B站视频 URL 或 UP 主空间 URL |
| `-l, --limit` | 最多处理多少个视频（仅 UP 主模式） |
| `-o, --output` | 输出目录（覆盖配置文件） |
| `--asr` | 强制使用语音识别（不下载字幕） |
| `-v, --verbose` | 显示详细日志 |

## 项目结构

```
vtw/
├── src/
│   ├── vtw.py           # 主程序
│   ├── config.py        # 配置管理
│   ├── subtitle.py      # 字幕处理
│   ├── asr.py           # 语音识别
│   ├── verifier.py      # 大模型校验
│   └── utils.py         # 工具函数
├── output/              # 输出目录
├── models/              # Whisper 模型缓存
├── config.json          # 配置文件
├── requirements.txt     # 依赖列表
├── README.md           # 本文档
└── CHANGELOG.md        # 开发日志
```

## 开发日志

详细的开发过程、问题记录和解决方案请参考 [CHANGELOG.md](CHANGELOG.md)

## 常见问题

### 1. yt-dlp 下载失败？

确保安装了最新版本：

```bash
pip install --upgrade yt-dlp
```

### 2. Whisper 模型下载很慢？

模型会从 Hugging Face 下载，可以设置镜像：

```python
# models 目录下设置环境变量
export HF_ENDPOINT=https://hf-mirror.com
```

### 3. 语音识别太慢？

- 换用更小的模型（tiny 或 base）
- 使用多线程：设置 `max_workers`
- 有 GPU 的话设置 `device: "cuda"`

### 4. 大模型校验失败？

检查 API Key 是否正确，网络是否通畅。

### 5. 繁体字未转换为简体？

确保安装了 opencc 库：

```bash
pip install opencc
```

并在 `config.json` 中设置 `"convert_to_simplified": true`。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
