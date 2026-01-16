# 开发日志 / Changelog

本文档记录 VTW 项目的开发过程、遇到的问题以及解决方案。

## 2026-01-16 - 图形界面 + 配置修复

### 新增功能

1. **图形界面**（GUI）
   - 新增 `src/gui.py` Tkinter 图形化界面
   - 新增 `gui.bat` GUI 启动脚本（修复批处理编码问题）
   - 新增 `docs/GUI.md` GUI 使用文档

   **功能列表**：
   - URL 输入框（支持粘贴和清空）
   - 输出目录选择（支持自定义路径）
   - 处理选项：数量限制、强制 ASR
   - 快速配置：打开配置文件、输出目录
   - 预计时间显示（根据视频类型自动计算）
   - 进度条显示（实时处理进度）
   - 详细日志输出（可清空）
   - 多线程处理（后台处理，界面不卡顿）

2. **配置管理改进**
   - 新增 `config.set_output_dir()` 方法
   - 支持运行时动态修改输出目录
   - GUI 中的输出目录修改会自动更新配置

### 配置选项

在 `config.json` 中新增以下配置项：

```json
{
  "knowledge_mode": {
    "enabled": false,           // 是否启用知识模式
    "add_summary_at_top": true, // 是否在开头添加总体总结
    "show_chapter_summary": true,// 是否显示章节小结
    "chapter_numbering": true   // 是否为章节添加编号
  }
}
```

### 问题与解决方案

#### 问题 1：GUI 启动脚本编码问题

**现象**：
```
系统找不到指定的路径。
'敊璇?' 不是内部或外部命令...
```

**原因**：
Windows 批处理文件（`.bat`）默认使用系统编码，中文字符导致解析错误。

**解决方案**：
1. 移除所有中文注释，改用英文 REM 注释
2. 修复参数传递方式（使用 `%~1` 引用第一个参数）

#### 问题 2：config.output_dir 属性无法设置

**现象**：
```
AttributeError: property 'output_dir' of 'Config' object has no setter
```

**原因**：
`config.output_dir` 是只读属性（property），不支持直接赋值。

**解决方案**：
添加 `config.set_output_dir()` 方法：
```python
def set_output_dir(self, path: str):
    """设置输出目录"""
    self.set('output_dir', path)
```

### 技术细节

#### Tkinter 界面
- **框架**：Tkinter（Python 内置）
- **窗口尺寸**：900x700
- **样式**：微软雅黑字体，10 号
- **进度条**：最大 100，长度 400 像素

#### 时间估算逻辑
```python
def _estimate_time(self, url):
    """估算处理时间"""
    # 检查是否是 UP 主
    if '/video/' not in url and 'BV' not in url:
        # UP 主模式 - 假设 5 个视频
        return "~10-20 分钟"
    else:
        # 单个视频 - 根据是否有字幕估算
        return "8-15 分钟（有字幕）/ 15-20 分钟（语音识别）"
```

### 测试结果

| 测试内容 | 结果 |
|-----------|------|
| GUI 启动 | ✅ 成功 |
| 输出目录选择 | ✅ 成功 |
| 预计时间计算 | ✅ 成功 |
| GUI 界面显示 | ✅ 正确 |

---

## 2026-01-16 - 知识模式 + 项目结构优化

### 新增功能

1. **知识模式**（Knowledge Mode）
   - 新增 `KnowledgeVerifier` 类，使用大模型对视频内容进行 AI 结构化处理
   - 自动识别章节结构（3-8 个逻辑章节）
   - 为每个章节生成标题（简洁明了，8-15字）
   - 为每个章节写 1-2 句小结
   - 生成总体总结（3-5 句话，概括核心知识点和价值）
   - 输出格式支持：
     - 开头的"内容总结"部分
     - 编号的章节标题（### 1. 标题）
     - 引用格式的章节小结（> 小结内容）
     - 完整的章节内容

2. **配置模板文件**
   - 新增 `config.example.json` 模板文件
   - 用户可以复制为 `config.json` 填写配置
   - 避免将包含 API Key 的 `config.json` 提交到 Git

3. **项目文档目录结构优化**
   - 创建 `docs/` 目录统一管理文档
   - 移动 `需求分析.md` 和 `CHANGELOG.md` 到 `docs/`
   - 更新 `.gitignore`：
     - 移除 `CHANGELOG.md`（改为在 docs/ 目录下）
     - 添加 `config.json` 到忽略列表
     - 添加 `!config.example.json` 例外

### 配置选项

在 `config.json` 中新增以下配置项：

```json
{
  "knowledge_mode": {
    "enabled": false,           // 是否启用知识模式
    "add_summary_at_top": true, // 是否在开头添加总体总结
    "show_chapter_summary": true,// 是否显示章节小结
    "chapter_numbering": true   // 是否为章节添加编号
  }
}
```

### 问题与解决方案

#### 问题 1：KnowledgeVerifier 调用参数不匹配

**现象**：
```
ERROR: TextVerifier.verify_text() takes from 2 to 3 positional arguments but 4 were given
```

**原因**：
- `VideoProcessor.process_video()` 调用 `verify_text()` 时传入了 `video_description` 参数
- 原有的 `TextVerifier.verify_text()` 方法只接受 `text` 和 `video_title` 两个参数

**解决方案**：
更新 `TextVerifier.verify_text()` 方法签名，添加 `video_description` 参数（即使不使用）：
```python
def verify_text(
    self,
    text: str,
    video_title: str = "",
    video_description: str = ""  # 新增参数，保持兼容性
) -> Optional[Dict]:
```

### 测试结果

| 测试视频 | 测试项 | 结果 |
|---------|---------|------|
| 《食神》《济公》机械降神or真理降临？——拉康没有说的，去问周星驰吧 (15:53) | 知识模式章节识别 | ✅ 成功 - 6 个章节 |
| 《食神》《济公》机械降神or真理降临？——拉康没有说的，去问周星驰吧 (15:53) | 总体总结生成 | ✅ 成功 |
| 《食神》《济公》机械降神or真理降临？——拉康没有说的，去问周星驰吧 (15:53) | 章节小结生成 | ✅ 成功 |
| 《食神》《济公》机械降神or真理降临？——拉康没有说的，去问周星驰吧 (15:53) | 输出格式 | ✅ 正确 |

### 技术细节

#### 知识模式 Prompt 设计

```
这是关于「{title}」的教学/知识类视频转写内容。

视频描述：{description}

请对以下内容进行结构化整理，完成以下任务：
1. 将内容划分为 3-8 个逻辑章节
2. 为每个章节生成合适的标题（简洁明了，8-15字）
3. 为每个章节写 1-2 句小结
4. 生成总体总结（3-5 句话，概括核心知识点和价值）
```

#### JSON 解析增强

- 支持解析 markdown 代码块格式的 JSON（```json...```）
- 支持解析普通代码块格式的 JSON（```...```）
- 支持直接返回纯 JSON 格式

#### 依赖版本

```txt
openai>=1.0.0
```

---

## 2026-01-15 - 繁转简体 + 智能排版

### 新增功能

1. **繁体字转简体字**
   - 集成 `opencc` 库实现繁体到简体的转换
   - 自动将识别出的繁体字转换为简体字
   - 可通过配置文件控制是否启用此功能

2. **智能段落排版**
   - 基于 Whisper 的 segment timing 数据进行段落组织
   - 根据语音停顿（间隔 > 1.5 秒）自动分段
   - 限制段落最大长度（约 300 字符）避免段落过长
   - 保留换行以提高可读性，避免所有文字连在一起

### 配置选项

在 `config.json` 中新增以下配置项：

```json
{
  "markdown": {
    "include_metadata": true,
    "sanitize_filename": true,
    "convert_to_simplified": true,   // 新增：是否转换为简体中文
    "format_paragraphs": true          // 新增：是否格式化为段落
  }
}
```

### 问题与解决方案

#### 问题 1：ffprobe 和 ffmpeg 未找到

**现象**：
```
ffprobe and ffmpeg not found. Please install or provide a path using --ffmpeg-location
```

**原因**：
- FFmpeg 没有安装或不在系统 PATH 中
- yt-dlp 需要使用 ffmpeg 进行音频提取

**解决方案**：
1. 使用 winget 安装 FFmpeg：
   ```bash
   winget install ffmpeg --accept-package-agreements --accept-source-agreements
   ```

2. 在 `asr.py` 中添加自动路径检测，支持 Windows winget 安装路径：
   ```python
   possible_paths = [
       r'C:\Users\27970\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe',
       r'C:\Users\27970\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe',
   ]
   
   for path in possible_paths:
       if Path(path).exists():
           ffmpeg_path = path
           break
   
   if ffmpeg_path:
       ydl_opts['ffmpeg_location'] = ffmpeg_path
   ```

#### 问题 2：Hugging Face 模型下载超时

**现象**：
```
TimeoutError: Unable to reach Hugging Face Hub to download model
```

**原因**：
- Hugging Face 在国内访问速度慢或不稳定
- 模型下载频繁失败

**解决方案**：
在 `asr.py` 中设置环境变量使用国内镜像：
```python
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

#### 问题 3：VAD 滤波器过度过滤

**现象**：
```
VAD filter removed 100%+ of audio, resulting in empty text
```

**原因**：
- Whisper 的 VAD（Voice Activity Detection）滤波器过于激进
- 错误地将正常语音判定为静音而过滤掉

**解决方案**：
在 `transcribe_audio` 方法中禁用 VAD 滤波器：
```python
segments, info = self.model.transcribe(
    str(audio_file),
    language=self.language,
    beam_size=5,
    vad_filter=False,  # 禁用 VAD 滤波器
)
```

#### 问题 4：duration 格式化错误

**现象**：
```
ValueError: Unknown format code 'd' for object of type 'float'
```

**原因**：
- Whisper 返回的 duration 是 `float` 类型（如 212.31 秒）
- `format_duration()` 函数签名定义为 `def format_duration(seconds: int)`，只接受整数

**解决方案**：
修改函数签名接受 `float` 类型：
```python
def format_duration(seconds: float) -> str:  # Changed from int
    seconds = float(seconds)  # Ensure it's a float
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ...
```

#### 问题 5：Whisper 输出繁体字

**现象**：
识别出的文本中包含大量繁体字，如「我們」、「餘亮老師」等。

**原因**：
- Whisper 模型的训练数据包含繁体字
- 对于部分内容，模型更倾向于输出繁体形式

**解决方案**：
1. 安装 opencc 库：
   ```bash
   pip install opencc
   ```

2. 在 `utils.py` 中添加转换函数：
```python
def convert_to_simplified(text: str) -> str:
    if not OPENCC_AVAILABLE:
        return text
    try:
        converter = opencc.OpenCC('t2s')  # 繁体转简体
        return converter.convert(text)
    except Exception:
        return text
```

3. 在 `vtw.py` 中配置默认启用：
```python
self.convert_to_simplified = getattr(config, 'convert_to_simplified', True)
```

#### 问题 6：文本没有段落格式

**现象**：
识别出的文本是一行一行显示，所有内容连在一起，阅读困难。

**原因**：
- 原始实现使用 `'\n'.join()` 将所有 segments 合并为一个连续段落
- Whisper 的 segments 之间间隔很小（平均 1.3 秒），基于时间的分段无法生效

**解决方案**：
1. 保留换行格式，将多个 segments 合并为段落：
```python
def group_segments_to_paragraphs(segments, max_gap=1.5, paragraph_length=300):
    # 使用 '\n' 而不是 ' ' 连接
    paragraph = '\n'.join(current_lines)
```

2. 基于双重条件判断是否需要分段：
   - 时间间隔超过 1.5 秒（语音停顿）
   - 或者当前段落长度超过 300 字符（避免段落过长）

### 测试结果

| 测试视频 | 测试项 | 结果 |
|---------|---------|------|
| 斩杀线完整版 (51:12) | 繁转简体 | ✅ 成功 |
| 斩杀线完整版 (51:12) | 段落排版 | ✅ 成功 |

### 技术细节

#### Whisper 识别性能

- **模型**：faster-whisper base (74MB)
- **设备**：CPU
- **计算精度**：int8
- **处理速度**：约 10 分钟/小时视频（51 分钟视频约 6-8 分钟）
- **识别质量**：约 2258 个 segments，15431 个字符
- **语言检测**：中文（概率 1.00）

#### 依赖版本

```txt
faster-whisper==1.0.3
opencc==1.1.9
yt-dlp>=2024.0.0
```

### 待优化方向

1. **段落格式优化**：当前基于时间的分段可能不够准确，可以考虑：
   - 添加语言模型辅助判断话题转换
   - 识别说话人切换
   - 使用标点符号辅助分段

2. **GPU 加速**：如果有 GPU，可以大幅提升 ASR 速度（约 3-5 倍），是否考虑使用云服务器或者语音大模型

3. **更大的 Whisper 模型**：small/medium 模型可以提升识别准确率，但需要更多计算资源
