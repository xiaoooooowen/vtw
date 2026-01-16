# VTW - Bilibili 视频转文字工具

批量将 Bilibili UP 主视频转换为 Markdown 文档，方便学习记录和知识整理。

## 功能特性

| 特性 | 说明 |
|------|------|
| **双模式提取** | 优先下载 B站字幕，无字幕时使用语音识别 |
| **本地识别** | 使用 faster-whisper，免费、准确 |
| **繁简转换** | 自动将繁体字转换为简体字 |
| **智能排版** | 基于语音停顿智能组织段落 |
| **知识模式** | AI 结构化处理，自动生成章节标题、小结和总体总结 |
| **大模型校验** | 支持 DeepSeek、OpenAI 等大模型 API 优化结果 |
| **批量处理** | 支持获取 UP 主所有视频并批量转换 |
| **智能命名** | 自动清理文件名，避免冲突 |
| **图形界面** | 提供 Tkinter GUI，操作直观便捷 |

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置文件

复制配置模板并编辑：

```bash
cp config.example.json config.json
```

**配置示例**：

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
    "api_key": "your-api-key",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat"
  },
  "knowledge_mode": {
    "enabled": false,
    "add_summary_at_top": true,
    "show_chapter_summary": true,
    "chapter_numbering": true
  },
  "markdown": {
    "include_metadata": true,
    "sanitize_filename": true,
    "convert_to_simplified": true,
    "format_paragraphs": true
  }
}
```

### 使用方式

#### 图形界面（推荐）

双击 `gui.bat` 文件启动，或运行：

```bash
python src/gui.py
```

详细使用说明请参考 [docs/GUI.md](docs/GUI.md)

#### 命令行

```bash
# Windows 使用启动脚本
run.bat https://www.bilibili.com/video/BV1xx411c7mD

# 使用完整 Python 路径
python src/vtw.py https://www.bilibili.com/video/BV1xx411c7mD

# 处理 UP 主的所有视频
python src/vtw.py https://space.bilibili.com/123456

# 限制处理最近 10 个视频
python src/vtw.py https://space.bilibili.com/123456 -l 10

# 强制使用语音识别
python src/vtw.py https://www.bilibili.com/video/BV1xx411c7mD --asr
```

#### 处理模式

- **标准模式**：生成原始转写文本，内容保持原样
- **知识模式**：AI 自动生成章节结构、章节小结和总体总结（需在配置中启用 `llm` 和 `knowledge_mode`）

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

支持的大模型：
- **DeepSeek**：默认推荐，性价比高
- **OpenAI**：设置 `base_url` 为 `https://api.openai.com/v1`
- 其他兼容 OpenAI API 的服务

### 知识模式配置

| 选项 | 说明 |
|------|------|
| `add_summary_at_top` | 在文档开头添加总体总结 |
| `show_chapter_summary` | 为每个章节添加小结（引用格式） |
| `chapter_numbering` | 为章节添加编号（如 "### 1. 章节标题"） |

**知识模式输出示例**：

```markdown
## 内容总结

本教程全面介绍了 Python 数据分析的核心技术...

## 视频信息
- **视频链接**: https://www.bilibili.com/video/BV...
- **处理模式**: 知识模式

## 详细内容

### 1. 环境准备与基础语法

> 本章介绍 Python 开发环境的搭建和基础语法。

首先需要安装 Python 3.8+ 版本...
```

### Markdown 配置

| 选项 | 说明 |
|------|------|
| `include_metadata` | 包含视频元数据信息 |
| `sanitize_filename` | 清理文件名中的特殊字符 |
| `convert_to_simplified` | 自动将繁体字转换为简体字 |
| `format_paragraphs` | 基于语音停顿智能组织段落 |

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
├── src/                    # 源代码
│   ├── vtw.py           # 主程序
│   ├── config.py        # 配置管理
│   ├── subtitle.py      # 字幕处理
│   ├── asr.py           # 语音识别
│   ├── verifier.py      # 大模型校验 & 知识模式
│   ├── gui.py           # 图形界面
│   └── utils.py         # 工具函数
├── output/              # 输出目录（生成的 Markdown 文件）
├── models/              # Whisper 模型缓存目录
├── config.example.json  # 配置模板
├── config.json          # 配置文件（不提交到 Git）
├── requirements.txt     # 依赖列表
├── run.bat             # 命令行启动脚本
├── gui.bat             # 图形界面启动脚本
└── README.md           # 使用说明
```

## 常见问题

### yt-dlp 下载失败？

确保安装了最新版本：

```bash
pip install --upgrade yt-dlp
```

### Whisper 模型下载很慢？

模型从 Hugging Face 下载，可以设置镜像：

```python
# models 目录下设置环境变量
export HF_ENDPOINT=https://hf-mirror.com
```

### 语音识别太慢？

- 换用更小的模型（tiny 或 base）
- 使用多线程：设置 `max_workers`
- 有 GPU 的话设置 `device: "cuda"`

### 大模型校验失败？

检查 API Key 是否正确，网络是否通畅。

### 繁体字未转换为简体？

确保安装了 opencc 库：

```bash
pip install opencc
```

并在 `config.json` 中设置 `"convert_to_simplified": true`。

## 安装

### 从源码安装

```bash
git clone https://github.com/xiaoooooowen/vtw.git
cd vtw
pip install -e .
```

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
