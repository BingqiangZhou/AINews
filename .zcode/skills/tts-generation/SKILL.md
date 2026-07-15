---
name: tts-generation
version: "1.0.2"
description: 文本转语音生成。使用 MiMo TTS 将文本高光转换为带时间戳的音频文件。支持单段和批量 TTS，输出 MP3 音频和合成字幕时间轴。独立可调用，也可被编排 skill 调用。**触发场景**：用户提到"TTS""文本转语音""语音合成""生成音频""文字转声音""text to speech"，或需要将文本内容转换为语音时使用。
---

# TTS Generation — 文本转语音

将文本高光转换为带时间戳的音频片段，为渲染 skill 提供音频输入。TTS 生成音频后使用 Whisper 转录获取精确时间戳。

## 输入/输出

**输入**：
- `highlights/final_highlights.json` — 高光列表（每条含 `tts_script` 和/或 `text` 字段）
- 或直接提供分段文本列表

**文本源优先级**：TTS 合成时，优先使用高光的 `tts_script` 字段；若 `tts_script` 不存在或为空，则回退到 `text` 字段。即：`tts_script` > `text`。

**输出**：
```
<project_dir>/clips/
  clip_000.mp3              # TTS 生成的音频
  clip_001.mp3
  ...
  clips.json                # 片段清单

<project_dir>/video/highlight_NNN/
  audio/
    clip.mp3                # 同 clips/clip_NNN.mp3 的副本
    whisper_segments.json   # Whisper 转录结果（word-level 时间戳，中间产物）
    words.json              # 逐字数据（generate-timeline-captions.py 副产物，供 AI 分句使用）
    timeline_captions.json  # 字幕时间轴（优先 whisper_aligned，回退 tts_synthetic）
```

**状态流转**：`rewritten → tts_generating → tts_generated`（失败写 `failed`）

> **目录职责说明**：本 skill 负责创建 `video/highlight_NNN/{audio,code,output}` 目录结构，以及 `audio/` 下的 `clip.mp3` 和 `timeline_captions.json`。`code/` 和 `output/` 下的文件由渲染 skill 负责。

## 执行步骤

前置：`highlights/final_highlights.json` 存在，每条高光的 `tts_script` 已生成（编排器在 `rewritten` 状态后调用）。

### Per-Highlight TTS 循环

对每条高光执行：

#### 1. 创建目录

```bash
mkdir -p "<project_dir>/video/highlight_<id>"/{audio,code,output}
```

#### 2. TTS 合成

```bash
<py> <scripts>/mimo_tts.py \
  --text "<tts_text>" \
  --output "<project_dir>/clips/clip_<NNN>.mp3" \
  <mode-flags> \
  --model "<tts_model>"
```

模式由 config.json 的 `tts_clone` 字段决定，`<mode-flags>` 取值：

| `tts_clone` | `tts_voice_profile` | `<mode-flags>` |
|-------------|---------------------|----------------|
| `true` | 已设置（如 `liufei`） | `--clone --ref "assets/voices/<tts_voice_profile>/ref.wav"` |
| `true` | 未设置 | `--clone`（用脚本内置默认参考音频 `voice_ref.wav`） |
| `false` / 未设置 | — | `--voice "<tts_voice>"`（克隆模式下忽略） |

`<tts_text>` 优先级：`highlight.tts_script`（非空时使用）> `highlight.text`（兜底）。`--text` 内联文本（与 `--input` 文件路径二选一，本流程固定用 `--text`）。

#### 3. 复制音频到高光目录

```bash
cp "<project_dir>/clips/clip_<NNN>.mp3" "<project_dir>/video/highlight_<id>/audio/clip.mp3"
```

#### 4. 生成 timeline_captions（Whisper 对齐，失败回退合成）

先用 Whisper 转录 TTS 音频获取逐字时间戳，再生成精确的字幕时间轴。Whisper 失败时回退到合成模式。

> **跨 skill 调用**：Whisper 脚本来自 whisper-transcribe skill，timeline 脚本来自 article-to-video skill（原 highlight-render-hyperframes，已内化归档）

**4a. Whisper 转录**（跳过已存在的 `whisper_segments.json`）：

```bash
if [ ! -f "<project_dir>/video/highlight_<id>/audio/whisper_segments.json" ]; then
  <py> .zcode/skills/whisper-transcribe/scripts/transcribe-faster-whisper.py \
    "<project_dir>/video/highlight_<id>/audio/clip.mp3" \
    --output "<project_dir>/video/highlight_<id>/audio/whisper_segments.json" \
    --model "{config.whisper_model}" --lang zh --initial-prompt "<该高光 tts_script 开头片段>"
fi
```

- `--model`：取 `config.whisper_model`（默认 `large-v3-turbo`，字级时间戳更准，提高后续字幕对齐 coverage、减少回退）。GPU 显存不足时 transcribe 脚本自动回退 `small`，不硬失败。
- `--initial-prompt`：取该高光 `tts_script` 开头片段（≤120 字，截到首个句末标点 `。！？；`），引导 Whisper 文字贴近 tts_script，进一步提升对齐 coverage。
- 已有 `whisper_segments.json` 时跳过。

**4b. 用 Whisper 时间戳生成 timeline_captions**（首选）：

```bash
if [ -f "<project_dir>/video/highlight_<id>/audio/whisper_segments.json" ]; then
  <py> .zcode/skills/article-to-video/scripts/generate-timeline-captions.py \
    --project-dir "<project_dir>" \
    --highlight-id <id> \
    --whisper-json "<project_dir>/video/highlight_<id>/audio/whisper_segments.json"
else
  # 4c. Fallback: 合成模式
  echo "WARNING: Whisper transcription failed, falling back to synthetic timing"
  <py> .zcode/skills/article-to-video/scripts/generate-timeline-captions.py \
    --project-dir "<project_dir>" \
    --highlight-id <id> \
    --synthetic-timing
fi
```

`--whisper-json` 模式读取 Whisper 逐字时间戳。**默认优先用该高光 `tts_script` 的标点定分句边界、用 Whisper 字时间戳做字符级对齐**（`timing_source`=`tts_script_aligned`，字幕文字为干净的 tts_script 原文，规避 ASR 错字）；当 `tts_script` 缺失或对齐 coverage<0.95 时，回退到 gap smoothing + boundary scoring 纯算法（`timing_source`=`whisper_aligned`）。加 `--no-tts-script-align` 可强制只用纯算法对照。回退到 `--synthetic-timing`（Whisper 完全失败）时标记为 `tts_synthetic`。

> **副产物**：`generate-timeline-captions.py` 在生成 `timeline_captions.json` 的同时会输出 `words.json`（包含 `raw_text` 和逐字时间戳），作为逐字时间轴的调试与备用分析副产物（AI 字幕分句已禁用，详见 `_backup/skills/highlight-render-hyperframes/references/troubleshooting.md`）。

#### 5. 写入 clips.json

所有高光写入一个 `clips.json`（JSON 数组，累积写入）：
```json
[
  {"id": 1, "path": "clip_000.mp3", "duration_ms": 30000, "text": "<original_text>"},
  {"id": 2, "path": "clip_001.mp3", "duration_ms": 25000, "text": "<original_text>"}
]
```

## 恢复策略

- 检查 `clips.json` 中每条 clip 文件是否存在
- 缺失的 clip 重新 TTS 生成
- 已生成的 clip 跳过

## 配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `tts_voice` | 苏打 | MiMo TTS 内置语音名（clone 模式下忽略） |
| `tts_model` | mimo-v2.5-tts-voiceclone | TTS 模型（clone 用 mimo-v2.5-tts-voiceclone，内置用 mimo-v2.5-tts） |
| `tts_clone` | true | 是否使用语音克隆模式 |
| `tts_voice_profile` | — | 声音档案 ID，映射到 `assets/voices/<id>/ref.wav`。未设置时使用脚本内置默认参考音频 |
| `tts_style` | default | 语音风格 |
| `whisper_model` | large-v3-turbo | Step 4a Whisper 转录模型（与 whisper-transcribe 默认值一致；GPU 显存不足时脚本自动回退 small） |

环境变量：`MIMO_API_KEY` 必须设置。

## Voice Profiles（声音档案）

语音克隆模式通过参考音频复制特定人的声音。每个声音档案存放在 `assets/voices/<id>/` 目录中，包含 `ref.wav` 参考音频和 `metadata.json` 元数据。

**已配置的声音档案**：

| Profile ID | 名称 | 参考音频 | 来源播客 |
|-----------|------|---------|---------|
| `liufei` | 三五环 · 刘飞 | `assets/voices/liufei/ref.wav` | 三五环 No.214 |
| `ziwojinhualun` | 自我进化论 | `assets/voices/ziwojinhualun/ref.wav` | 自我进化论 |

**使用方式**：在 config.json 中设置 `tts_voice_profile` 为对应的 Profile ID。TTS 合成时会自动传递 `--ref assets/voices/<id>/ref.wav`。

**添加新声音档案**：建 `assets/voices/<id>/` 目录，放入 `ref.wav`（5-30 秒清晰人声录音）+ `metadata.json`（来源信息），然后在 config.json 设置 `tts_voice_profile` 为该 `<id>`。
