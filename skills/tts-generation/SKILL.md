---
name: tts-generation
version: "1.1.0"
description: 文本转语音生成（TTS 后端执行器）。使用 MiMo TTS 将文本合成为 MP3 音频，支持内置音色与声音克隆。提供 `synthesize()` 供其他 skill 导入，也可独立 CLI 调用。**触发场景**：用户提到"TTS""文本转语音""语音合成""生成音频""文字转声音""text to speech"，或需要将文本内容转换为语音时使用。
---

# TTS Generation — 文本转语音

TTS 生成**后端执行器**。把文本丢给 MiMo-V2.5-TTS 合成音频文件——内置音色（苏打）或声音克隆（参考音频复刻特定人声）。本 skill 只负责"文本 → 可用 MP3"，不决定内容、不做字幕对齐。

## 两种调用方式

### 1. 作为库被导入（主用法）

下游 skill 直接导入 `synthesize()` 做单段合成。典型消费者：`article-to-solo-podcast/scripts/solo_tts.py`——单人专业资讯播客整段文本一次性合成（单音色冰糖，`clone=False`），调用 `extract_sections` 仅剥离 `[SECTION:N]` 标记（不切段、不拼接），输出 -16 LUFS 单段音频。

```python
# 定位 tts-generation/scripts
sys.path.insert(0, str(SKILLS_DIR / "tts-generation" / "scripts"))
from mimo_tts import synthesize

synthesize(
    text="要合成的文本",
    output_path="output.mp3",
    clone=True,                          # 克隆模式（False=内置音色）
    ref_audio="voice_ref.wav",           # 克隆参考音频（本 skill scripts/voice_ref.wav，单一源）
    model="mimo-v2.5-tts-voiceclone",    # 不传则按 clone 自动选择
    api_key=os.environ["MIMO_API_KEY"],
)
```

### 2. 作为 CLI 独立调用

```bash
# 内置音色（默认）
<py> <scripts>/mimo_tts.py --input text.txt --output audio.mp3

# 内联文本
<py> <scripts>/mimo_tts.py --text "要合成的文本" --output audio.mp3

# 声音克隆（默认参考音频用本 skill scripts/voice_ref.wav，单一源）
<py> <scripts>/mimo_tts.py --input text.txt --output audio.mp3 --clone

# 声音克隆 + 自定义参考音频
<py> <scripts>/mimo_tts.py --input text.txt --output audio.mp3 --clone --ref my_voice.wav
```

## synthesize() 签名

```python
def synthesize(
    text: str,
    output_path: str,
    *,
    voice: str = "苏打",           # 内置音色名（clone 模式下忽略）
    clone: bool = False,           # True=声音克隆，False=内置音色
    ref_audio: str | None = None,  # 克隆参考音频路径（默认: 本 skill scripts/voice_ref.wav，单一源）
    model: str | None = None,      # 模型 ID（不传按 clone 自动选：clone→mimo-v2.5-tts-voiceclone，内置→mimo-v2.5-tts）
    style: str | None = None,      # 风格指令（可选）
    api_key: str = "",             # 留空则 CLI 层从 MIMO_API_KEY 读取
    fmt: str = "mp3",              # 输出格式：mp3 / wav
    timeout: float = 120.0,        # 单次请求超时（客户端内置 max_retries=3 自动重试瞬态错误）
) -> str:                          # 返回 output_path
```

**实现要点**（详见 `scripts/mimo_tts.py`）：
- MiMo TTS 的非标准约定：目标文本放在 `role=assistant` 的 content 里，`user` 消息携带风格指令（无风格时发空串而非省略，兼容 OpenAI 兼容层）。
- 原子写盘：渲染到 `.tmp` 兄弟文件再 `os.replace`，崩溃或 ffmpeg 失败不留半写/损坏输出。
- MP3 模式先拿到 WAV 再用 ffmpeg 转码（`-f mp3` 强制 muxer，避免 `.tmp` 扩展名导致 ffmpeg 无法推断容器）。

## 配置

config.json（flat schema，`<this skill>/config.json`）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `python_executable` | `python` | Python 解释器（`<py>`；`AINews_PYTHON` 环境变量优先，其次此字段，最后 PATH 上的 `python`） |
| `ffmpeg_path` | `ffmpeg` | ffmpeg 可执行 |
| `tts_voice` | 苏打 | MiMo 内置语音名（clone 模式下忽略） |
| `tts_model` | mimo-v2.5-tts-voiceclone | 默认模型（clone 用 voiceclone，内置用 mimo-v2.5-tts） |
| `tts_clone` | true | 是否使用声音克隆模式 |
| `tts_voice_profile` | ziwojinhualun | 声音档案 ID，映射到 `assets/voices/<id>/ref.wav`（CLI 层据此传 `--ref`） |
| `tts_style` | default | 语音风格指令 |

环境变量：`MIMO_API_KEY` 必须设置。

## Voice Profiles（声音档案）

声音克隆模式通过参考音频复刻特定人的声音。每个声音档案存放在 `assets/voices/<id>/` 目录，包含 `ref.wav`（5-30 秒清晰人声录音）和 `metadata.json`（来源元数据）。

**已配置的声音档案**：

| Profile ID | 名称 | 参考音频 | 来源 |
|-----------|------|---------|------|
| `liufei` | 三五环 · 刘飞 | `assets/voices/liufei/ref.wav` | 三五环 No.214 |
| `ziwojinhualun` | 自我进化论 | `assets/voices/ziwojinhualun/ref.wav` | 自我进化论 |

**使用方式**：在 config.json 设置 `tts_voice_profile` 为对应 Profile ID；CLI 调用时由编排器据此拼 `--ref assets/voices/<id>/ref.wav`。库调用时直接传 `ref_audio=` 参数。

**添加新声音档案**：建 `assets/voices/<id>/` 目录，放入 `ref.wav` + `metadata.json`，然后在 config.json 设置 `tts_voice_profile` 为该 `<id>`。

## 依赖

- **API**：小米 MiMo TTS（`https://api.xiaomimimo.com/v1`），OpenAI 兼容接口。
- **ffmpeg**：MP3 转码（WAV 模式不依赖）。

> **注意：本 skill 只做 TTS 合成，不做字幕对齐。** 若需要从生成的音频获取逐字时间戳/字幕时间轴，那是 **whisper-transcribe**（Whisper 转录）+ **article-to-video**（`generate-timeline-captions.py` 字幕对齐）的职责，不在本 skill 范围内。
