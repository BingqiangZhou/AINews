---
name: whisper-transcribe
version: "1.0.1"
description: Whisper 音频转录。使用 Faster Whisper 将音频转录为带时间戳的字幕 JSON。独立可调用，也可被编排 skill 调用。**触发场景**：用户提到"Whisper 转录""转录音频""whisper transcribe""音频转文字""语音转文字"，或需要将音频文件转录为文字时使用。
---

# Whisper Transcribe — 音频转录

使用 Faster Whisper 将音频转录为带时间戳的字幕 JSON。

## 输入/输出

**输入**：音频文件路径 + 项目目录

**输出产物**：
```
<project_dir>/
  captions/
    captions.json              # Whisper 转录结果（word-level 时间戳）
  transcribe_metadata.json     # 转录元数据（模型、语言、时长、设备）
```

**状态流转**：`downloaded → transcribing → transcribed`（失败写 `failed`）

## 执行步骤

前置：音频文件已就绪（由 media-download 下载或直接提供）。

### Step 1: Whisper 转录

```bash
<py> <scripts>/transcribe-faster-whisper.py "<audio_file_path>" \
  --output "<project_dir>/captions/captions.json" \
  --model large-v3-turbo \
  --metadata "<project_dir>/transcribe_metadata.json"
```

- 默认 `large-v3-turbo`，语言 `zh`，pipeline WhisperModel（无 VAD）
- 可选 `--vad` 或 `--pipeline batched`（更快但可能丢失 ~25% 语音）
- 脚本自动降级：`cuda → cpu`

**验证**：`captions.json` 中 `startMs/endMs` 单调递增。

## 恢复策略

- 检查 `captions/captions.json` 是否存在且 `startMs/endMs` 单调递增 → 跳过转录

## 配置

本 skill 的 `config.json` 可覆盖以下参数（未列出则使用 `scripts/lib/utils.py` 中的硬编码默认值）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `default_whisper_model` | large-v3-turbo | Whisper 模型 |
| `default_timeout` | 30 | 脚本执行超时 |
