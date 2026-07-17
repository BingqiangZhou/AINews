---
name: article-to-video
version: "2.0.0"
description: 把一篇已完成的公众号文章（含插图、封面、播客 TTS 音频）转成横版 16:9 长视频。用 hyperframes（HTML 渲染）生成动态画面：背景插图 Ken Burns + section 标题卡 + 逐句字幕 + 品牌水印 + 入场动效，播客音频做旁白。字幕文本来自播客脚本原文（正确无错字），时间戳来自 Whisper（精准对齐口播）。4 阶段流水线：字幕对齐（复用 Whisper + caption_align）→ 脚本对齐（原文句子→Whisper word 时间戳）→ 构建 composition（生成 hyperframes HTML 项目）→ 渲染（npx hyperframes lint/check/render）。**触发场景**：用户提到"文章转视频""把文章做成视频""article to video""公众号文章转成视频""文章配图做视频""图文成视频"时使用。
metadata:
  platforms: []
---

# 公众号文章转视频（hyperframes）

本文件是本 skill 的**唯一流程真源**。

把一篇**已完成的公众号文章**转成横版 16:9 长视频。**hyperframes 把 HTML 渲染成视频**——画面是动态的：背景插图做 Ken Burns 缓慢推拉、每个 section 起始弹出标题卡（章节名 + 关键词 chips）、逐句字幕在底部随口播滚动、品牌水印全程显示，所有元素带入场动效。播客 TTS 音频做旁白（不重新 TTS、不重新改写）。字幕文本用播客脚本**原文**（正确，无 Whisper 错字），时间戳用 Whisper word-level 对齐（精准跟口播）。

## 关联 Skills / 资产（只读复用，不改动）

- **whisper-transcribe**：`scripts/transcribe-faster-whisper.py`——对播客 TTS 音频做 word-level 转录。subprocess 调用（经 `align_captions.py`）。
- **caption_align / utils（本 skill 内化）**：`scripts/lib/caption_align.py`（字符级 DP 对齐核心）、`scripts/lib/utils.py`（whisper-transcribe utils 的 re-export shim）。`align_script.py` 复用 `caption_align.align_sentences_to_words` 把播客脚本原文句子对齐到 Whisper word 时间戳。
- **hyperframes（外部 CLI）**：`npx hyperframes`——把 HTML composition 渲染成 MP4。需 Node.js ≥22 + FFmpeg + Chrome（首次自动下载 chrome-headless-shell）。`render_video.py` 封装 lint/check/render。
- **article-to-solo-podcast**：消费其产物（`公众号_文章.md` + `imgs/` + `公众号_封面.png` + `播客_TTS.mp3` + `播客_脚本.txt`）。如果文章目录缺播客音频/脚本，引导用户先跑 `article-to-solo-podcast`。

## 流程概览

```text
文章目录(文章.md + imgs/ + 封面.png + 播客_TTS.mp3 + 播客_脚本.txt)
  → [Phase 1] 字幕对齐 (Whisper word-level 转录 → caption_align → timeline_captions.json + whisper_segments.json + sections_timeline.json)
  → [Phase 2] 脚本对齐 (播客脚本原文按句切分 → align_sentences_to_words 对齐 Whisper word 时间戳 → captions_corrected.json，含 section 标题/时间戳/原文句子)
  → [Phase 2.5] 视觉设计 (主 agent 读 design_scenes_prompt.md，按 schema 为每个 section 提取关键数字/关键词/要点 → scenes_visual.json)
  → [Phase 3] 构建 composition (scenes_visual + captions_corrected + 播客音频 → hyperframes HTML 项目，视觉由文案驱动纯 CSS/GSAP 生成)
  → [Phase 4] 渲染 (npx hyperframes lint → check → render → 公众号_视频.mp4)
```

## 为什么用 hyperframes（替代旧 Ken Burns ffmpeg 流程）

旧流程（v1，5 阶段 ffmpeg）画面只是对静态插图做 zoompan 缓慢缩放，信息表达力弱、无动态排版。hyperframes 把 HTML 渲染成视频，**视觉由文案内容驱动**（不复用文章插图），为每个 section 生成数据可视化式画面：
- **hero_number**：超大数字 count-up 冲击动效 + 一句话说明（如「10 万小时」「80% token 空转」）。
- **stat_grid**：数据卡片网格对比（如「15 分钟 vs 6 小时」）。
- **keypoints**：要点列表逐条滑入。
- **keywords**：关键词 chips 网格错峰入场。
- **逐句字幕**：正确文本（脚本原文，无 Whisper 错字）按口播时间戳在底部滚动。
- **动态背景**：每个 section 一个主题色渐变 + radial-gradient 发光球缓慢漂移 + 科技网格底纹。
- **品牌水印**：左上角 AINews 角标 + 右上角日期，全程显示。

旧 5 阶段脚本（`plan_scenes.py`/`render_kenburns.py`/`captions_to_ass.py`/`compose_video.py`）保留为回退（`config.renderer: "ffmpeg"`），默认不再走。

## 关键规则

**状态与缓存**
1. **断点续跑**：`_video/state.json` 跟踪每阶段状态，已完成跳过；每步完成立即回写。
2. **不污染原文**：所有产物写入 `<文章目录>/_video/`，不修改文章 MD、插图、封面、播客音频等源文件。

**复用约束**
3. **不修改现有 skill**：只读复用 whisper-transcribe（caption_align/utils 已内化至本 skill `scripts/lib/`）。
4. **importlib 加载**：`generate-timeline-captions.py` 文件名带连字符，`align_captions.py` 用 `importlib.util.spec_from_file_location` 加载。

**产物**
5. 输出目录 = `<文章目录>/_video/`。`temp/` 存中间件（whisper、timeline、captions_corrected），`hyperframes_project/` 存 HTML composition + assets，最终产物 `公众号_视频.mp4` 在 `_video/` 根。

**hyperframes determinism 约束（build_composition 必须遵守）**
6. 单一 GSAP `paused: true` timeline，注册 `window.__timelines["<composition-id>"]`。
7. clip 元素可见性由框架按 `data-start`/`data-duration` 管理——**只做入场 `tl.fromTo(opacity:0→1)`，绝不手动 `tl.to(opacity:0)` 出场**（会触发 `gsap_exit_missing_hard_kill`，非线性 seek 后 stale 状态）。
8. 只动 opacity/transform（不动 display/visibility）。同轨 clip 不重叠（`overlapping_clips_same_track` lint error）。
9. `class="clip"` + `data-start`/`data-duration`/`data-track-index` 是 clip 三要素；`<audio>` 是 root 直接子元素。
10. `font-family` 必须有 `@font-face` 声明（系统字体用 `src: local()`）。

**输入要求**
11. 文章目录必须已含：`公众号_文章.md`、`imgs/`（插图 PNG + `segments.json`）、`公众号_封面.png`、`播客_TTS.mp3`、`播客_脚本.txt`。播客音频/脚本优先从 `_podcast/` 子目录读（`article-to-solo-podcast` canonical 输出位），根目录作向后兼容；两者都缺时引导用户先跑 `article-to-solo-podcast`。路径解析统一走 `lib/utils.py` 的 `resolve_podcast_path`。

## 环境配置

`<py>` = 插件解析的 Python（`AINews_PYTHON` → `config.environment.conda_python` → `python`）；`<scripts>` = 本 skill 的 `scripts/`。ffmpeg/ffprobe 在 PATH（或 `AINews_FFMPEG`/`AINews_FFPROBE`）。Whisper 需 CUDA GPU（推荐，Faster Whisper 加速）；CPU 可用但慢。

**hyperframes 额外依赖**：Node.js ≥22（`npx` 可用）+ FFmpeg。首次 `npx hyperframes` 自动拉 CLI（0.7.x）+ chrome-headless-shell。环境自检：`npx hyperframes doctor`。

## 状态与产物布局

状态机：`initialized → aligned → script_aligned → composed → rendered → completed`。

产物（`<文章目录>/_video/`）：
```
_video/
  ├── state.json                    # 状态机
  ├── temp/
  │   ├── whisper_segments.json     # Whisper 转录（word-level）[Phase 1]
  │   ├── timeline_captions.json    # 字幕时间轴（Whisper 文本）[Phase 1]
  │   ├── sections_timeline.json    # [SECTION:N] 分节时间轴 [Phase 1]
  │   ├── captions_corrected.json   # 脚本原文对齐 Whisper 时间戳 [Phase 2]
  │   └── hf_scenes.json            # hyperframes 场景规划（调试用）[Phase 3]
  ├── hyperframes_project/          # hyperframes HTML 项目 [Phase 3]
  │   ├── index.html                # composition（背景层+标题卡+字幕+水印+音频）
  │   ├── hyperframes.json
  │   ├── meta.json
  │   ├── package.json
  │   ├── assets/
  │   │   ├── narration.mp3         # 播客 TTS 音频（copy）
  │   │   └── imgs/*.png            # 文章插图（copy）
  │   └── snapshots/                # snapshot 抽帧（调试用，可删）
  └── 公众号_视频.mp4               # 最终产物 [Phase 4]
```

## 执行步骤

每阶段先查 `_video/state.json`，已完成则跳过。

| Phase | 跳过条件 | 负责 | 检查点 |
|-------|---------|------|--------|
| 0 初始化 | `state.json` 存在且 `state != initialized` | 主 agent | 建 `_video/` + `temp/` + `state.json`；读 config；校验输入文件齐全 |
| 1 字幕对齐 | `phase1==completed` | `scripts/align_captions.py`（带 `--force`） | `temp/whisper_segments.json` + `temp/timeline_captions.json` 非空；若播客带 `[SECTION:N]` 标记则额外产 `temp/sections_timeline.json` |
| 2 脚本对齐 | `phase2==completed` | `scripts/align_script.py` | `temp/captions_corrected.json` 非空，`captions` 数组 >0（正确文本+时间戳），`sections` 数组含每个 section 的标题/时间戳 |
| 2.5 视觉设计 | `phase2_5==completed` | `scripts/design_scenes.py` 生成 prompt → **主 agent** 读 prompt 按 schema 输出 `temp/scenes_visual.json` | `temp/scenes_visual.json` 存在，每个 section 有 kicker/title/visual_type + 对应视觉字段（hero_number/keypoints/stat_grid/keywords） |
| 3 构建 composition | `phase3==completed` | `scripts/build_composition.py` | `hyperframes_project/index.html` 存在，`assets/narration.mp3` 齐全；`npx hyperframes lint` 0 error |
| 4 渲染 | `phase4==completed` | `scripts/render_video.py` | `npx hyperframes check` 通过；`公众号_视频.mp4` 存在，ffprobe 校验含 video+audio 流，时长 ≈ 音频时长 |
| 5 完成检查 | — | 主 agent | 回查所有产物，报告视频路径/时长/大小 |

### 脚本调用示例

```bash
# Phase 1 字幕对齐（Whisper 转录 + caption_align 对齐）
<py> <scripts>/align_captions.py --article-dir "<文章目录>" --force

# Phase 2 脚本对齐（播客脚本原文 → Whisper word 时间戳）
<py> <scripts>/align_script.py --article-dir "<文章目录>"

# Phase 2.5 视觉设计（生成 prompt）
<py> <scripts>/design_scenes.py --article-dir "<文章目录>"
#   ↑ 然后主 agent 读 temp/design_scenes_prompt.md，按 schema 输出 temp/scenes_visual.json

# Phase 3 构建 hyperframes composition（读 scenes_visual.json）
<py> <scripts>/build_composition.py --article-dir "<文章目录>"

# Phase 4 渲染（lint + check + render）
<py> <scripts>/render_video.py --article-dir "<文章目录>" --quality standard
# 迭代时跳过 check 省时：
<py> <scripts>/render_video.py --article-dir "<文章目录>" --quality draft --skip-check
# 只抽帧看效果不渲染：
<py> <scripts>/render_video.py --article-dir "<文章目录>" --snapshot-only
```

## composition 结构（build_composition 生成）

单一 GSAP paused timeline（`window.__timelines["ainews-daily"]`），4 个 track 层。**视觉由文案驱动**（scenes_visual.json），纯 CSS/GSAP 生成，不复用文章插图：

| Track | 层 | 内容 | 时序 |
|-------|----|------|------|
| 0 | 背景 | 每 section 一个渐变背景 clip（主题色 linear-gradient + radial-gradient 发光球缓慢漂移 + 科技网格底纹），z-index 递增 | section 时间戳连续化（首尾相接），同轨不重叠 |
| 1 | 字幕 | 逐句字幕 clip（正确文本，半透明深色背景框） | 按 Whisper 对齐时间戳，同轨顺序不重叠 |
| 2 | 视觉内容 | section 数据可视化 clip，按 `visual_type` 渲染：hero_number（大数字 count-up）/ stat_grid（数据卡片网格）/ keypoints（要点列表）/ keywords（chips 网格） | section start + 0.4s 起，duration = section 时长 - 0.6s |
| 3 | 水印 | AINews 角标 + 日期，全程 | data-start=0, duration=总时长 |
| 10 | 音频 | 播客 TTS `<audio>`，框架管理播放 | data-start=0 |

入场动效（opacity/transform，无出场——clip 到点自动隐藏）：背景淡入 + 发光球 sine.inOut 漂移；kicker back.out 弹入 → title 淡入 → 主体内容错峰（大数字 back.out 冲击 / 卡片逐个弹入 / 要点逐条滑入 / chips stagger）。**禁用 `filter:blur` 和过量 `backdrop-filter`/`radial-gradient`**（hyperframes heavy_overlay 堆积会导致渲染前半段黑屏）。

## 确认规则

- 全流程按 config 默认执行，不单独询问。
- 不自动发布。产出视频后，如需发布到各平台，由用户另行操作或用 `browser-publisher`。

## 脚本目录

| 脚本 | 用途 |
|------|------|
| `scripts/align_captions.py` | 阶段 1：Whisper 转录 + caption_align 对齐 → `timeline_captions.json`（新旧流程共用） |
| `scripts/align_script.py` | 阶段 2：播客脚本原文句子 → `align_sentences_to_words` 对齐 Whisper word 时间戳 → `captions_corrected.json`（**新流程**）。**section 时间戳**用每个 section 首句在 captions 里查实际口播时间（权威），不依赖 Phase 1 的 `sections_timeline.json`（后者 char 偏移在 DEEPDIVE/ENDING 等节会严重错位导致音画不同步）。 |
| `scripts/design_scenes.py` | 阶段 2.5：生成视觉设计 prompt；主 agent 读 prompt 按 schema 输出 `scenes_visual.json`（**新流程**） |
| `scripts/build_composition.py` | 阶段 3：读 scenes_visual + captions_corrected + 音频 → 生成 hyperframes HTML 项目（视觉纯 CSS/GSAP，**新流程**） |
| `scripts/render_video.py` | 阶段 4：封装 `npx hyperframes lint/check/render`（含磁盘 cache 重定向） → `公众号_视频.mp4`（**新流程**） |
| `scripts/plan_scenes.py` | （旧 ffmpeg 流程）分镜规划 |
| `scripts/render_kenburns.py` | （旧 ffmpeg 流程）Ken Burns 渲染 |
| `scripts/captions_to_ass.py` | （旧 ffmpeg 流程）字幕转 ASS |
| `scripts/compose_video.py` | （旧 ffmpeg 流程）合成 |

## 按需读取

| 文件 | 用途 |
|------|------|
| `config.json` | 视频/hyperframes/封面/Ken Burns/字幕/Whisper/环境参数 |

## 完成检查

`state.json` 全 phase `completed` 后回查：
1. `_video/公众号_视频.mp4` 存在，ffprobe 校验含 video+audio 流。
2. 视频时长 ≈ 播客音频时长（误差 < 1 秒）。
3. 画面分辨率 1920×1080。
4. 字幕在视频中可读、不遮挡画面主体、文本正确（无 Whisper 错字）。
5. section 标题卡在对应章节起始正确显示。
6. 报告视频路径、时长、文件大小。
