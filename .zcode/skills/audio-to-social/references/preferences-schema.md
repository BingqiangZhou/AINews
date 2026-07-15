# audio-to-social Config Schema

> 本文件是 config.json 字段说明，由主 agent 初始化时按需加载。

`config.json` 是唯一配置源，包含环境和偏好配置。

## Lookup Priority

1. Current user request or CLI-style arguments
2. `config.json` 中的对应字段
3. Skill defaults

## Sections

### brand

| Key | Values | Default | Purpose |
|-----|--------|---------|---------|
| `name` | text | required | Brand/account voice used in content and media |
| `storage_root` | path | required | Output root and global cache root |

### platforms

| Key | Values | Default | Purpose |
|-----|--------|---------|---------|
| `default_target` | array of platform ids | `["gongzhonghao", "boker"]` | Default platforms |
| `boker_next_episode` | integer | empty | Episode number prefix source for Ximalaya podcast |

### content

| Key | Values | Default | Purpose |
|-----|--------|---------|---------|
| `default_style` | `auto` / `deep_analysis` / `casual_chat` / `inspirational` | `auto` | Text style baseline |
| `default_visual_preset` | `auto` / `knowledge-card` / `cozy-story` / `bold-warning` / `minimal-opinion` | `auto` | Visual baseline |

### source

| Key | Values | Default | Purpose |
|-----|--------|---------|---------|
| `fetcher` | `baoyu-url-to-markdown` / `native` | `baoyu-url-to-markdown` | URL/公众号/网页素材归一化方式 |
| `youtube_transcript_languages` | array of language codes | `["zh", "en"]` | YouTube 字幕优先语言 |
| `download_source_media` | `ask` / `true` / `false` | `ask` | URL 抓取时是否下载图片/视频素材 |

### tts

| Key | Values | Default | Purpose |
|-----|--------|---------|---------|
| `provider` | `mimo` | `mimo` | TTS backend |
| `voice` | voice name | `苏打` | TTS voice |
| `model` | model id | `mimo-v2.5-tts-voiceclone` | TTS model (clone mode uses mimo-v2.5-tts-voiceclone, builtin uses mimo-v2.5-tts) |
| `clone` | `true` / `false` | `false` | Enable voice clone mode |
| `style` | text or null | null | Optional TTS style prompt |
| `ref_audio` | path or null | null | Voice-clone reference audio; null = use bundled `scripts/voice_ref.wav` |

### cover

| Key | Values | Default | Purpose |
|-----|--------|---------|---------|
| `provider` | `agnes` / `gaoding` | `gaoding` | Cover image backend（audio-to-social 固定 `gaoding`，不回退 agnes） |
| `model` | Agnes 模型 id，如 `agnes-image-2.1-flash` | `agnes-image-2.1-flash` | Agnes 回退时用的模型 id（audio-to-social 禁用 Agnes 回退，基本不触发） |
| `gaoding_model` | 稿定模型名，如 `万相2.7` / `智能图像` | `万相2.7` | 稿定生图模型（万相2.7 印刷级中文文字渲染，含文字图必选；智能图像中文会乱码）。封面/插图默认走此模型 |
| `type` | `auto` / cover type | `auto` | Baoyu cover-image type dimension |
| `palette` | `auto` / palette name | `auto` | Baoyu cover-image palette dimension |
| `rendering` | `auto` / rendering name | `auto` | Baoyu cover-image rendering dimension |
| `text` | `none` / `title-only` | `none` | Whether generated cover may contain text |
| `mood` | `auto` / `subtle` / `balanced` / `bold` | `auto` | Baoyu cover-image mood dimension |

### image

| Key | Values | Default | Purpose |
|-----|--------|---------|---------|
| `output_format` | `webp` / `png` / `jpeg` | `webp` | Compressed image output format |
| `quality` | integer 1-100 | `80` | Compression quality |
| `cover_size` | WxH | `900x383` | 公众号封面目标尺寸（reconcile 校验与 prompt-agent 取值来源） |
| `illustration_size` | WxH | `1920x1080` | 插图目标尺寸（reconcile 校验与 prompt-agent 取值来源） |

### publishing

| Key | Values | Default | Purpose |
|-----|--------|---------|---------|
| `wechat_account` | alias or empty | empty | Browser publisher account alias |
| `boker_account` | alias or empty | empty | Browser publisher account alias for Ximalaya |
| `preflight_always` | `true` / `false` | `true` | Always run publish pre-flight |
| `html_theme` | theme name | `default` | Markdown to WeChat-compatible HTML theme |

### environment

| Key | Values | Default | Purpose |
|-----|--------|---------|---------|
| `conda_python` | path | required | Python executable path |
| `ffmpeg` | path or command | `ffmpeg` | FFmpeg executable |
| `font` | path | platform default (Windows: msyh.ttc, macOS: PingFang.ttc) | Font file for image rendering |
| `mimo_api_key_env` | env var name | `MIMO_API_KEY` | MiMo API key environment variable |
| `whisper_model` | model name | `large-v3-turbo` | Whisper model |
| `whisper_batch_size` | integer | `16` | Whisper batch size |
| `whisper_language` | language code | `zh` | Whisper transcription language |
| `whisper_initial_prompt` | text | `以下是普通话的句子。` | Whisper initial prompt |
| `max_factcheck_rewrites` | integer | `2` | Max quality-gate rewrite rounds |

## Config Migration

Phase 0 detects old flat config.json (with top-level `brand_name`/`storage_root`) and auto-migrates to new grouped format. Migration is idempotent.
