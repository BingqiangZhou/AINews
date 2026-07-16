---
name: audio-to-social
version: "5.0.0"
description: >
  录音/URL/YouTube/Markdown 一键转社交媒体内容包（**纯编排器**）。本 skill 只做「输入归一化 + Whisper 转录 +
  编排委派 + 归档 + 发布」，内容生产全部委派给下游 skill：article-studio（transcript 模式出文章）、
  article-to-solo-podcast（出播客音频）、article-cover-image-generator / article-illustrator（出封面+插图）、
  article-to-video（出视频）。**触发场景**：用户提到"录音转文章""音频转社交媒体""口播录音处理""生成公众号/播客内容"
  "把录音变成文章""录音笔记整理""录音发公众号""口播内容一键分发""把这段录音发出去"，或想把一段录音变成多平台内容时使用。
metadata:
  platforms: [gongzhonghao, boker]
  orchestrator: true
---

# 录音转社交媒体内容包（纯编排器）

本文档是本 skill 的**唯一流程真源**。本 skill 是**纯编排器**——它本身不生产内容，只负责：输入归一化、Whisper 转录、按序委派下游 skill、归档校验、发布。所有内容生产（文章/播客/封面/插图/视频）都委派给专门 skill。

## 关联 Skills（委派目标）

| 阶段 | 下游 skill | 职责 | 调用方式 |
|------|-----------|------|---------|
| Phase 1 转录 | `whisper-transcribe` | faster-whisper + CUDA 转录 | `scripts/transcribe_via_ingest.py` 委托其 `transcribe-faster-whisper.py` |
| Phase 2 文章 | `article-studio`（**transcript 模式**） | 转录 → 书面公众号文章（零联网、零外部事实、主编审查门禁） | skill 委派，传 `source_mode: transcript` + `source_file` + `article_type` |
| Phase 3 封面 | `article-cover-image-generator`（**全量模式**） | 标题+核心论点 → 公众号封面（900x383，内部再委派 image-generator） | skill 委派，传 `content_context` + `target_size` + `output_path` + `visual_preset` |
| Phase 3b-prepare 插图（分段） | `article-illustrator`（**prompt_only**） | 文章 → 插图 prompt + outline + segments.json（含 illustration_meta） | skill 委派，传文章路径 + `visual_preset` + density + `prompt_only=true` |
| Phase 3b-render 插图（生图） | `article-illustrator`（续跑）/ `article-cover-image-generator` | prompt → PNG + 回写 `![]()` 到文章 | 续跑 illustrator 或批量委派 cover-generator |
| Phase 4 播客 | `article-to-solo-podcast` | 文章 → 播客脚本+TTS 音频（10 维 rubric + 集号） | skill 委派，传 `--input 公众号_文章.md`，输出嵌套 `_podcast/`。**前置：Phase 3b-prepare 完成**（conductor 读 segments.json） |
| Phase 5 视频 | `article-to-video` | 文章+插图+封面+播客音频 → 16:9 视频（Ken Burns + 字幕） | 顺序调 5 个 CLI 脚本，各带 `--article-dir` |
| Phase 7 发布 | `browser-publisher` | 浏览器自动化发布公众号/喜马拉雅 | skill 委派（用户显式触发） |

> **Phase 时序**（消除隐藏竞态）：Phase 3b 拆成两步——3b-prepare（prompt_only，产出 segments.json）先跑；**Phase 4 前置 3b-prepare**（播客 conductor 依赖 segments.json 的 illustration_meta 对齐图内容）；3b-render（生图+回写）与 Phase 4 **并行**。Phase 3a（封面）与 3b-prepare 并行。Phase 5 等三者（尤其插图回写 + 播客音频）都完成。

## 流程概览

```text
audio/URL/YT/MD → [Phase 0 归一化, 内联] → [Phase 1 转录, 内联]
                                          │ temp/转录文本.txt
                                          ▼
              [Phase 2 文章, 委派 article-studio transcript 模式]
                                          │ 公众号_文章.md + 摘要 + <文章目录>
                                          ▼
        ┌──────────────┬──────────────────┐  ← 并行
        ▼              ▼                  
  [Phase 3a 封面]  [Phase 3b-prepare 插图（prompt_only）]
  cover-generator  illustrator
  → 公众号_封面.png → imgs/{prompts/,outline.md,segments.json}
                          │ segments.json 就绪（含 illustration_meta）
        ┌─────────────────┴──────────────┐  ← 并行
        ▼                                ▼
  [Phase 3b-render 插图（生图）]   [Phase 4 播客]
  illustrator 续跑 / cover-gen    article-to-solo-podcast
  → imgs/*.png + 回写![]()        conductor 读 segments.json
                                   → _podcast/{脚本,标题描述,TTS.mp3}
        └──────────────┴──────────────────┘
                          │ (文章含插图引用 + 播客音频 + 封面 就绪)
                          ▼
              [Phase 5 视频, 委派 article-to-video]
                          → _video/公众号_视频.mp4
                          │
                          ▼
              [Phase 6 归档, 内联] reconcile + compress + 终检
                          │
                          ▼
              [Phase 7 发布, 用户显式触发] browser-publisher + bump_episode
```

## 关键规则

**状态与缓存**
1. **断点续跑 + 即时持久化**：`state.json` 跟踪每阶段完成状态（`stages.{stage}.status`），已完成步骤自动跳过；每步完成立即回写，避免崩溃丢失。
2. **可复用缓存**：转录有可追溯缓存；同一音频可复用缓存跳过 Whisper。
3. **下游 skill 各有断点账本**：`_podcast/state.json`、`_video/state.json`、article-studio `state.json` 是它们自己的续跑账本。本编排器只在 `stages.*.status` 上追踪委派是否成功，不复制其内部字段——重入时若下游 state 显示已完成，直接跳过该阶段。

**内容生成（全部委派）**
4. **转录是唯一事实源**：Phase 2 文章严格从转录派生（article-studio transcript 模式零联网、零外部事实）。
5. **目录统一**：项目根用 article-studio 原生布局 `articles/{YYYY-MM-DD}_{标题}/`，下游 skill 的 `_podcast/`、`_video/`、`imgs/` 自然嵌套，零胶水。
6. **集号单一来源**：`config.platforms.boker_next_episode` 统一管理播客集号，article-to-solo-podcast 与 `bump_episode.py` 都从这里读。

**平台选择**
7. **按需生成**：支持 `target_platforms`，默认全平台（文章+播客+视频）；用户明确只要某平台时跳过对应阶段。

**操作约定**（详情见 [agents/_shared.md](agents/_shared.md)）：覆盖前备份（`scripts/backup_file.py`，最多 3 份）；统一配置源 `config.json`；子 agent 返回后立即验证输出非空、失败重试 1 次。

## 环境配置

路径和参数在 `config.json` 中定义（首次运行引导式生成）。下文 `<py>` 代表插件解析的 Python（`AINews_PYTHON` → `config.environment.conda_python` → `python`），`<scripts>` 代表 `skills/audio-to-social/scripts`。

## 状态与产物布局

状态机：`normalize → transcribe → article → media → podcast → video → archive → (publish)`

- 每阶段写 `state.json.stages.{stage}.status`（`pending` / `completed` / `failed`）。完整 schema 见 [state-schema](references/state-schema.md)。
- 产物布局（`articles/{YYYY-MM-DD}_{标题}/`；全局总览见 [docs/article-manifest.md](../../../docs/article-manifest.md)）：

```
articles/{YYYY-MM-DD}_{标题}/          ← 唯一项目根（Phase 0 决定标题，Phase 2 建目录）
├── 公众号_文章.md                       ← Phase 2（article-studio，含插图占位符 → Phase 3b 回写 ![]()）
├── 公众号_摘要.txt                      ← Phase 2
├── 公众号_封面.png                      ← Phase 3a（cover-generator 全量模式）
├── imgs/                               ← Phase 3b（illustrator 全量模式：outline.md + prompts/ + NN-*.png）
├── _podcast/                           ← Phase 4（article-to-solo-podcast）
│   ├── 播客_脚本.txt
│   ├── 播客_标题与描述.txt
│   └── 播客_TTS.mp3
├── _video/                             ← Phase 5（article-to-video）
│   └── 公众号_视频.mp4
├── state.json                          ← 编排器状态机（单一来源）
├── cache/                              ← Whisper 缓存（captions.json / transcribe_metadata.json）
├── temp/                               ← 转录文本.txt 等中间物
└── prompts/                            ← 封面 prompt 等（如保留）
```

## 执行步骤

每阶段先查 `state.json.stages`，已完成则跳过。委派契约（输入/输出/并行规则）集中见 [delegation-contracts](references/delegation-contracts.md)。

| Stage | 跳过条件 | 委派目标 | 检查点 |
|-------|---------|---------|--------|
| 0 归一化 | `stages.normalize.status==completed` | 主 agent 内联 | output_dir 决定、输入归一化、cache_key 算出 |
| 1 转录 | `stages.transcribe.status==completed` | `whisper-transcribe`（经 `scripts/transcribe_via_ingest.py`） | `temp/转录文本.txt` 存在且非空 |
| 2 文章 | `stages.article.status==completed` | `article-studio`（transcript 模式） | `公众号_文章.md` + `公众号_摘要.txt` 存在；拿到 `article_dir` |
| 3 媒体 | `stages.media.status==completed` | `article-cover-image-generator` ‖ `article-illustrator`（并行） | `公众号_封面.png` + `imgs/*.png` 存在；文章已回写插图引用 |
| 4 播客 | `stages.podcast.status==completed` | `article-to-solo-podcast` | `_podcast/播客_脚本.txt` + `_podcast/播客_TTS.mp3` 存在 |
| 5 视频 | `stages.video.status==completed` | `article-to-video`（5 个 CLI 脚本顺序） | `_video/公众号_视频.mp4` 存在 |
| 6 归档 | `stages.archive.status==completed` | 主 agent 内联（`scripts/reconcile_media.py` ‖ `scripts/compress_images.py`） | reconcile 无 error |
| 7 发布 | 用户明确要求 | `browser-publisher` + `scripts/bump_episode.py` | `publish.tracks.{platform}.status=completed` |

### 各阶段要点

**Phase 0 — 归一化（内联）**：详见 [phase0-initialization](references/phase0-initialization.md)。加载 config、确定主题/标题、算 `cache_key`、把 URL/YouTube/Markdown 输入归一化到 `temp/source_assets/`（audio 输入直接复制到 `temp/`）。本阶段**不建项目目录**——目录由 Phase 2 的 article-studio 按 `{storage_root}/{YYYY-MM-DD}_{标题}/` 建。

**Phase 1 — 转录（内联，委托 whisper-transcribe）**：详见 [phase0-initialization](references/phase0-initialization.md) 转录段。`scripts/transcribe_via_ingest.py` 调 whisper-transcribe 转录 + 内置 `extract-plain-text.py` 提取纯文本到 `temp/转录文本.txt`。可复用 cache 跳过 Whisper。

**Phase 2 — 文章（委派 article-studio transcript 模式）**：传 `source_mode: transcript` + `source_file=<temp/转录文本.txt>` + `article_type`（默认 `opinion`）+ `output_dir` 的 storage_root。article-studio 跳过联网检索、转录为唯一权威源、主编审查门禁。返回 `公众号_文章.md`（含 `<!-- illustration -->` 占位符）+ `公众号_摘要.txt`。**拿到 article-studio 建的 `article_dir`**，后续所有阶段在此目录下操作。

**Phase 3 — 媒体**：文章就绪后分步委派（消除 conductor 与 segments.json 的隐藏竞态）：
- **3a 封面** → `article-cover-image-generator` 全量模式：`content_context`（标题+核心论点）、`target_size=900x383`、`output_path=<article_dir>/公众号_封面.png`、`visual_preset`。与 3b-prepare 并行。
- **3b-prepare 插图（分段）** → `article-illustrator` **prompt_only 模式**：文章路径 + `visual_preset` + density + `prompt_only=true`。产出 `imgs/prompts/*.md` + `imgs/outline.md` + `imgs/segments.json`（含 illustration_meta）。**这是 Phase 4 的前置**——segments.json 就绪后立即委派 Phase 4。
- **3b-render 插图（生图）** → `article-illustrator` 续跑（从 prompt_only 断点继续 Step 5.2-6）或批量委派 `article-cover-image-generator`。生成 PNG + 回写 `![](imgs/NN-xxx.png)` 到 `公众号_文章.md`。**与 Phase 4 并行**（播客不依赖 PNG，只依赖 segments.json 的 meta 信息）。

**Phase 4 — 播客（委派 article-to-solo-podcast）**：**前置：Phase 3b-prepare 完成**（segments.json 就绪）。传 `--input <article_dir>/公众号_文章.md`。conductor 读 `imgs/segments.json` 按 segment 分组要点 + 据 illustration_meta 对齐图内容。它读 `config.platforms.boker_next_episode` 做集号、`voice_ref.wav` 做 TTS 克隆、`tts-generation` 做 MiMo 合成。输出嵌套 `<article_dir>/_podcast/`。与 Phase 3b-render 并行。

**Phase 5 — 视频（委派 article-to-video）**：等 Phase 3（插图回写）+ Phase 4（播客音频）完成后，顺序调 5 个脚本（各带 `--article-dir "<article_dir>"`，阶段间读 `_video/state.json` 续跑）：
```bash
<py> <a2v_scripts>/align_captions.py --article-dir "<dir>" --force
<py> <a2v_scripts>/plan_scenes.py     --article-dir "<dir>"
<py> <a2v_scripts>/render_kenburns.py --article-dir "<dir>"
<py> <a2v_scripts>/captions_to_ass.py --article-dir "<dir>"
<py> <a2v_scripts>/compose_video.py   --article-dir "<dir>"
```
其中 `<a2v_scripts>` = `skills/article-to-video/scripts`。产 `<article_dir>/_video/公众号_视频.mp4`。

**Phase 6 — 归档（内联）**：详见 [phase7-verify-archive](references/phase7-verify-archive.md)。`scripts/reconcile_media.py`（校验封面+插图+引用一致性，路径适配新布局）与 `scripts/compress_images.py` 并行。终检所有产物存在且非空。

**Phase 7 — 发布（用户显式触发）**：详见 [phase8-publishing](references/phase8-publishing.md)。pre-flight → `browser-publisher` 发公众号/喜马拉雅 → `scripts/bump_episode.py` 递增集号。

## 确认规则

- Phase 7（发布）需要用户明确要求才会执行。
- 发布 pre-flight 通过后，除非用户在当前会话明确确认，不点击任何发布/提交按钮。
- 用户说"直接生成"/"不用确认"/"跳过确认"时，跳过所有非昂贵确认；**媒体生成（Phase 3/4/5）按 config 默认后端直接执行，不单独询问**；只有**发布（Phase 7）始终需要确认**，除非明确说"直接发布"。

## 脚本目录

| 脚本 / 资源 | 用途 | 调用阶段 |
|------|------|---------|
| `scripts/transcribe_via_ingest.py` | Whisper 转录包装（委托 whisper-transcribe + 内置 extract-plain-text） | Phase 1 |
| `scripts/extract-plain-text.py` | captions.json → 纯文本（transcribe_via_ingest 内部调） | Phase 1 |
| `scripts/cache_key.py` | 计算转录缓存键 | Phase 0 |
| `scripts/validate_content_quality.py` | 机器质量检查（被 article-studio 复用） | Phase 2（下游） |
| `scripts/backup_file.py` | 文件备份（多 skill 共享） | 覆盖前 |
| `scripts/reconcile_media.py` | 校验封面/插图/引用一致性（PNG 权威格式） | Phase 6 / 7 pre-flight |
| `scripts/compress_images.py` | 图片压缩 | Phase 6 |
| `scripts/markdown_to_wechat_html.py` | Markdown 转公众号 HTML（委派 browser-publisher xiaohu） | Phase 7 |
| `scripts/bump_episode.py` | 发布后递增 `boker_next_episode` + 清 `episode_number_claimed` | Phase 7 |
| `scripts/voice_ref.wav` | TTS 参考音频（被 article-to-solo-podcast 读取） | Phase 4（下游） |
| `scripts/test_e2e_structure.py` | 结构性自检（pytest） | 开发期自检 |

> 旧的内联内容生产脚本/agent 已归档至 `_backup/skills/audio-to-social-4.4.0/`（transcript-optimizer、boker-optimizer、quality-gate、cover/illustration-prompt-agent、image-batch-generator、insert_illustration_refs）。

## 按需读取

| 文件 | 用途 |
|------|------|
| `config.json` | 环境配置、工具路径、模型、API 环境变量、集号计数器 |
| [delegation-contracts](references/delegation-contracts.md) | **4 个下游 skill 的委派契约（输入/输出/并行规则）** |
| [state-schema](references/state-schema.md) | state.json v4 结构 |
| [preferences-schema](references/preferences-schema.md) | config.json 字段说明 |
| [brand-config](references/brand-config.md) | 品牌声音和目录结构 |
| [phase0-initialization](references/phase0-initialization.md) | Phase 0 归一化 + Phase 1 转录 |
| [phase7-verify-archive](references/phase7-verify-archive.md) | Phase 6 归档 |
| [phase8-publishing](references/phase8-publishing.md) | Phase 7 发布 |
| [publish-playbook](references/publish-playbook.md) | 跨 skill 发布协作 |
| [visual-presets](references/visual-presets.md) | 视觉预设（传给 cover-generator/illustrator） |
| [baoyu-integration](references/baoyu-integration.md) | Baoyu skills 输入归一化边界 |

子代理合约：[agents/_shared.md](agents/_shared.md)（共享规则）、`agents/audio-engineer.md`（Phase 1 转录编排）。

## 完成检查

当 `state.json.stages.archive.status == "completed"` 时，逐 stage 回查各 checkpoint。重点确认：
1. `公众号_文章.md`（含插图引用）、`公众号_封面.png`、`imgs/*.png`、`_podcast/播客_TTS.mp3`、`_video/公众号_视频.mp4` 均存在且非空。
2. `state.json.stages` 各阶段均为 `completed`。
