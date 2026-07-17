---
name: article-to-video
version: "1.0.0"
description: 把一篇已完成的公众号文章（含插图、封面、播客 TTS 音频）转成横版 16:9 长视频。画面用文章插图做 Ken Burns 缩放平移，字幕烧录，FFmpeg 合成。直接复用已有的播客音频做旁白——不重新改写、不重新 TTS。5 阶段流水线：字幕对齐（复用 Whisper + caption_align）→ 分镜规划（插图↔口播段落对齐）→ Ken Burns 渲染（ffmpeg zoompan）→ 字幕转换（ASS）→ 合成（concat + 音轨 + 字幕烧录）。**触发场景**：用户提到"文章转视频""把文章做成视频""article to video""公众号文章转成视频""文章配图做视频""图文成视频"时使用。
metadata:
  platforms: []
---

# 公众号文章转视频

本文件是本 skill 的**唯一流程真源**。

把一篇**已完成的公众号文章**转成横版 16:9 长视频。文章插图做 Ken Burns 画面，播客 TTS 音频做旁白，字幕烧录。FFmpeg 全本地合成，零云服务依赖。

## 关联 Skills / 资产（只读复用，不改动）

- **whisper-transcribe**：`scripts/transcribe-faster-whisper.py`——对播客 TTS 音频做 word-level 转录，产出 `whisper_segments.json`。subprocess 调用。
- ~~**highlight-render-hyperframes**~~（已归档至 `_backup/skills/highlight-render-hyperframes`）：原只读复用其 `scripts/lib/caption_align.py`（字幕对齐核心库）、`scripts/lib/utils.py`（JSON/ffprobe 工具）、`scripts/generate-timeline-captions.py`（底层对齐编排函数）。**现已内化至本 skill `scripts/lib/` + `scripts/generate-timeline-captions.py`**。importlib + sys.path 复用。
- **article-to-duo-podcast**：消费其产物（`公众号_文章.md` + `imgs/` + `公众号_封面.png` + `播客_TTS.mp3` + `播客_脚本.txt`）。如果文章目录缺播客音频/脚本，引导用户先跑 `article-to-duo-podcast`。上游公众号文章/插图/封面由编排器（如 ai-news-digest）及下游 article-studio / article-illustrator / article-cover-image-generator 产出。

## 流程概览

```text
文章目录(文章.md + imgs/ + 封面.png + 播客_TTS.mp3 + 播客_脚本.txt)
  → 字幕对齐(Whisper转录 → caption_align对齐 → timeline_captions.json)
  → 分镜规划(插图引用↔口播段落文本匹配 → scenes.json)
  → Ken Burns 渲染(每图 zoompan → segments/scene_NNN.mp4)
  → 字幕转换(timeline_captions.json → subtitles.ass)
  → 合成(concat片段 + 播客音轨 + 字幕烧录 → 公众号_视频.mp4)
```

## 关键规则

**状态与缓存**
1. **断点续跑 + 即时持久化**：`_video/state.json` 跟踪每阶段状态，已完成跳过；每步完成立即回写。
2. **不污染原文**：所有产物写入 `<文章目录>/_video/`，不修改文章 MD、插图、封面、播客音频等源文件。

**复用约束**
3. **不修改现有 skill**：只读复用 whisper-transcribe 脚本（caption_align/utils/gtc 已内化至本 skill）。
4. **importlib 加载**：`generate-timeline-captions.py` 文件名带连字符，不能直接 import，用 `importlib.util.spec_from_file_location` 加载。

**产物**
5. 输出目录 = `<文章目录>/_video/`。`temp/` 存中间件（whisper、timeline），`segments/` 存视频片段，最终产物 `公众号_视频.mp4` 在 `_video/` 根。

**输入要求**
6. 文章目录必须已含：`公众号_文章.md`（含 `![](imgs/NN-xxx.png)` 插图引用）、`imgs/` 目录（插图 PNG）、`公众号_封面.png`、`播客_TTS.mp3`、`播客_脚本.txt`。播客音频/脚本优先从 `_podcast/` 子目录读（`article-to-duo-podcast` 的 canonical 输出位），根目录作向后兼容；两者都缺时引导用户先跑 `article-to-duo-podcast`。路径解析统一走 `lib/utils.py` 的 `resolve_podcast_path`。

## 环境配置

`<py>` = 插件解析的 Python（`AINews_PYTHON` 环境变量 → `config.environment.conda_python` → `python`）；`<scripts>` = 本 skill 的 `scripts/`。ffmpeg/ffprobe 在 PATH（或 `AINews_FFMPEG`/`AINews_FFPROBE` 环境变量）。Whisper 需 CUDA GPU（推荐，Faster Whisper 加速）；CPU 可用但慢。

## 状态与产物布局

状态机：`initialized → aligned → planned → rendered → captioned → composed → completed`。`state.json` 的 `phaseN` 键：简单 phase 存 `"completed"` 字符串。

产物（`<文章目录>/_video/`；全局总览见 [docs/article-manifest.md](../../../docs/article-manifest.md)）：
```
_video/
  ├── state.json                    # 状态机
  ├── temp/
  │   ├── whisper_segments.json     # Whisper 转录（word-level）
  │   ├── timeline_captions.json    # 字幕时间轴
  │   └── sections_timeline.json    # [SECTION:N] 分节时间轴（有分节标记时生成）
  ├── scenes.json                   # 分镜表
  ├── segments/                     # 各场景视频片段（无音频）
  │   ├── cover.mp4
  │   ├── scene_000.mp4
  │   └── ...
  ├── subtitles.ass                 # ASS 字幕
  └── 公众号_视频.mp4               # 最终产物
```

## 执行步骤

每阶段先查 `_video/state.json`，已完成则跳过。

| Phase | 跳过条件 | 负责 | 检查点 |
|-------|---------|------|--------|
| 0 初始化 | `state.json` 存在且 `state != initialized` | 主 agent | 建 `_video/` + `temp/` + `segments/` + `state.json`；读 config；校验输入文件齐全 |
| 1 字幕对齐 | `phase1==completed` | `scripts/align_captions.py` | `temp/timeline_captions.json` 非空，`captions` 数组 >0，`audio_duration_seconds` 合理；若播客带 `[SECTION:N]` 标记则额外产 `temp/sections_timeline.json` |
| 2 分镜规划 | `phase2==completed` | `scripts/plan_scenes.py` | `scenes.json` 非空，`scenes` 数组 >0，每场景有 `image`/`start_ms`/`end_ms`/`ken_burns`。**优先读 `sections_timeline.json` 按分节切场景（每节配对应插图）；无则回退文本匹配** |
| 3 Ken Burns 渲染 | `phase3==completed` | `scripts/render_kenburns.py` | `segments/` 下每个场景对应 mp4 存在且非空，ffprobe 时长匹配场景时长 |
| 4 字幕转换 | `phase4==completed` | `scripts/captions_to_ass.py` | `subtitles.ass` 非空，含 `[Events]` 和 `Dialogue:` 行 |
| 5 合成 | `phase5==completed` | `scripts/compose_video.py` | `公众号_视频.mp4` 存在，ffprobe 校验含 video+audio 流，时长 ≈ 封面+音频时长 |
| 6 完成检查 | — | 主 agent | 回查所有产物，报告视频路径/时长/大小 |

### 脚本调用示例

```powershell
# Phase 1 字幕对齐
<py> <scripts>/align_captions.py --article-dir "<文章目录>" --force

# Phase 2 分镜规划
<py> <scripts>/plan_scenes.py --article-dir "<文章目录>"

# Phase 3 Ken Burns 渲染
<py> <scripts>/render_kenburns.py --article-dir "<文章目录>"

# Phase 4 字幕转换
<py> <scripts>/captions_to_ass.py --article-dir "<文章目录>"

# Phase 5 合成
<py> <scripts>/compose_video.py --article-dir "<文章目录>"
```

## 确认规则

- 全流程按 config 默认执行，不单独询问。
- 不自动发布。产出视频后，如需发布到各平台，由用户另行操作或用 `browser-publisher`。

## 脚本目录

| 脚本 | 用途 |
|------|------|
| `scripts/align_captions.py` | 阶段 1：Whisper 转录 + caption_align 对齐 → `timeline_captions.json` |
| `scripts/plan_scenes.py` | 阶段 2：插图引用↔口播段落对齐 → `scenes.json` |
| `scripts/render_kenburns.py` | 阶段 3：每图 ffmpeg zoompan → `segments/scene_NNN.mp4` |
| `scripts/captions_to_ass.py` | 阶段 4：timeline_captions.json → `subtitles.ass` |
| `scripts/compose_video.py` | 阶段 5：concat + 音轨 + 字幕烧录 → `公众号_视频.mp4` |

## 按需读取

| 文件 | 用途 |
|------|------|
| `config.json` | 视频/封面/Ken Burns/字幕/Whisper/环境参数 |

## 完成检查

`state.json` 全 phase `completed` 后回查：
1. `_video/公众号_视频.mp4` 存在，ffprobe 校验含 video+audio 流。
2. 视频时长 ≈ `config.cover.duration_sec` + 播客音频时长（误差 < 1 秒）。
3. 画面分辨率 1920×1080，30fps，H.264 + AAC。
4. 字幕在视频中可读、不遮挡画面主体。
5. 报告视频路径、时长、文件大小。
