# 委派契约（下游 skill 输入/输出/并行规则）

> 本编排器把内容生产委派给 4 个下游 skill。本文件是**唯一的委派契约真源**——每个 skill 的精确输入字段、输出产物、调用方式、断点续跑语义、并行关系都在此定义。

通用约定：
- **项目根**：`articles/{YYYY-MM-DD}_{标题}/`（Phase 2 由 article-studio 建立）。下文 `<article_dir>` = 该路径。
- **`<py>`** = `config.environment.conda_python`（`D:\Development\miniconda3\python.exe`）。
- **委派后立即校验**：返回后 read_file 验证输出产物存在且非空；失败带上下文重试 1 次，仍失败记 `stages.{stage}.status="failed"` 并跳过。
- **断点续跑**：每阶段完成立即写 `state.json.stages.{stage}.status="completed"` + 产物路径。重入时若该 stage 已 completed 直接跳过；若下游 skill 自己的 state（如 `_podcast/state.json`）显示其内部已完成，也视为本阶段完成。

---

## Phase 2 — 文章：委派 `article-studio`（transcript 模式）

**职责**：转录文本 → 书面公众号文章。零联网、零外部事实（转录为唯一权威源），主编 5 维度审查门禁。

### 输入（结构化，传给 article-studio）

| 字段 | 值 | 说明 |
|------|----|----|
| `source_mode` | `"transcript"` | 触发 transcript 模式（跳过联网检索） |
| `source_file` | `<article_dir>/temp/转录文本.txt` | Phase 1 产出（编排器先把转录放到 article_dir，或传原 temp 路径） |
| `article_type` | `config.content.default_article_type` 或 `opinion` | 6 类枚举；录音随笔默认 `opinion` |
| `output_dir` 的 storage_root | `config.brand.storage_root` | article-studio 在其下建 `articles/{YYYY-MM-DD}_{标题}/` |
| `topic`（可选） | 编排器从转录派生的一句话主题 | 不传则 article-studio writer 派生 |
| `title_hint`（可选） | 建议标题 | 不传则 writer 派生 |

### 输出（article-studio 产出）

| 文件 | 路径 | 说明 |
|------|------|------|
| 文章 | `<article_dir>/公众号_文章.md` | 首行 `# 标题`，含 `<!-- illustration -->` 占位符（2-4 个，供 Phase 3b 回写） |
| 摘要 | `<article_dir>/公众号_摘要.txt` | ≤120 字 |
| article-studio state | `<article_dir>/state.json` | `phase: "editor_passed"`，`source_mode: "transcript"` |

### 关键约定
- **拿到 `article_dir`**：article-studio 建目录后，编排器从其 state.json 读 `output_dir`，后续所有阶段在此目录下操作。
- **转录文本定位**：编排器 Phase 1 产出的转录可能暂存在临时位置；Phase 2 委派前应确保 `source_file` 路径可达（必要时复制进 `<article_dir>/temp/`）。但注意：article-studio 自己会建 `<article_dir>`，所以编排器可在 Phase 2 先把转录放到一个稳定的临时路径（如 Phase 0 的 temp 区），等 article-studio 建好目录后再视需要搬迁。
- **反杜撰不变量**：article-studio transcript 模式保证零外部事实（详见 `article-studio/references/transcript-mode.md`）。

---

## Phase 3a — 封面：委派 `article-cover-image-generator`（全量模式）

**职责**：标题+核心论点 → 公众号封面（900x383）。全量模式内部再委派 `image-generator` 出图（Gaoding 后端）。

### 输入（结构化）

| 字段 | 值 | 说明 |
|------|----|----|
| `content_context` | 文章标题 + 核心论点/主题关键词 | 从 `公众号_文章.md` 提取（标题 + 摘要或首段） |
| `target_size` | `"900x383"` | 公众号封面尺寸（`config.image.cover_size`） |
| `output_path` | `<article_dir>/公众号_封面.png` | 固定文件名（browser-publisher 契约） |
| `output_dir` | `<article_dir>` | prompts/ 与产物落此处 |
| `visual_preset` | `config.content.default_visual_preset` | auto-mapping（仅影响封面 type/mood；封面 palette/rendering/font 已固定为 hand-drawn-edu 预设 + 手写字体，见 article-cover-image-generator 规则 #14） |
| `cover_provider` | `config.cover.provider`（gaoding） | gaoding / jimeng / agnes；默认 Gaoding，不回退 Agnes |

### 输出

| 文件 | 路径 |
|------|------|
| 封面 | `<article_dir>/公众号_封面.png` |

### 并行
可与 Phase 3b（插图）、Phase 4（播客）**并行**委派。

---

## Phase 3b — 插图：委派 `article-illustrator`（两步：prepare + render）

**职责**：决定插图位置+内容并生成图片。拆成两步委派，消除 conductor 与 segments.json 的隐藏竞态（Phase 4 的 conductor 依赖 segments.json）。

### Phase 3b-prepare（prompt_only 模式，先跑）

**职责**：分析文章 + 切段 + 产出 prompt 文件 + segments.json（含 illustration_meta）。

### 输入（结构化）

| 字段 | 值 | 说明 |
|------|----|----|
| 文章路径 | `<article_dir>/公众号_文章.md` | illustrator 读 `<!-- illustration -->` 占位符位置 |
| `visual_preset` | `config.content.default_visual_preset` | auto-mapping 到 illustrator preset（knowledge-card→knowledge 等） |
| `density` | `balanced`（3-5 张） | 可按文章长度调 |
| `prompt_only` | `true` | 产出 prompt + segments.json 后返回，不生图 |
| output dir | `<article_dir>/imgs/` | illustrator 原生产物目录 |

### 输出（3b-prepare）

| 文件 | 路径 | 说明 |
|------|------|------|
| outline | `<article_dir>/imgs/outline.md` | 插图大纲（含 Segment/Title Text/Labels 字段） |
| prompts | `<article_dir>/imgs/prompts/*.md` | 每张插图的 prompt（frontmatter 含 title_text/labels） |
| segments | `<article_dir>/imgs/segments.json` | 章节→插图分段 + illustration_meta（**Phase 4 conductor 的前置**） |

返回 JSON 含 `segments_file` 字段——Phase 4 的 conductor 读它来按 segment 分组要点 + 对齐图内容。

### Phase 3b-render（生图+回写，与 Phase 4 并行）

**职责**：从 3b-prepare 的断点续跑，生成 PNG + 回写文章。

- **方式 A**（推荐）：再次委派 `article-illustrator`，它检测到 prompt 文件已存在则续跑 Step 5.2-6（生图 + 回写）。
- **方式 B**：批量委派 `article-cover-image-generator` 生成所有 PNG，再由 illustrator Step 6 回写。

### 输出（3b-render）

| 文件 | 路径 | 说明 |
|------|------|------|
| 插图 | `<article_dir>/imgs/NN-{type}-{slug}.png` | PNG（WeChat 不接受 webp） |
| 文章（回写） | `<article_dir>/公众号_文章.md` | 占位符被替换为 `![](imgs/NN-xxx.png)` |

### 关键约定
- 3b-prepare 必须先于 Phase 4 完成（segments.json 是 conductor 的前置）。
- 3b-render 与 Phase 4 并行（播客不依赖 PNG）。
- 回写后 `公众号_文章.md` 的 `<!-- illustration -->` 占位符应全部被替换（Phase 6 reconcile 会校验）。
- `image_backend`（`config.cover.provider`）在 3b-render 时映射到 cover_provider。

### 并行
- 3b-prepare 与 Phase 3a（封面）并行。
- 3b-render 与 Phase 4（播客）并行。

---

## Phase 4 — 播客：委派 `article-to-solo-podcast`

**职责**：文章 → 播客脚本 + TTS 音频（10 维 rubric + 集号管理）。已原生支持文章输入，输出嵌套 `_podcast/`。

### 前置条件
- **Phase 3b-prepare 完成**：`<article_dir>/imgs/segments.json` 就绪（含 illustration_meta）。conductor 读它来按 segment 分组要点 + 据 illustration_meta（type/title_text/labels）让播客要点和图内容对齐。无 segments.json 时 conductor 退回平铺要点（向下兼容，但失去图内容对齐）。

### 输入

| 字段 | 值 | 说明 |
|------|----|----|
| `--input` | `<article_dir>/公众号_文章.md` | 文章（含插图引用无妨，ingest_article.py 会清洗） |

article-to-solo-podcast 自动读：
- `<article_dir>/imgs/segments.json`（Phase 3b-prepare 产出，conductor 的分段+图信息来源）
- `config.platforms.boker_next_episode`（集号，经 `publishing.boker_episode_config` 指向本 config）
- `scripts/voice_ref.wav`（TTS 克隆参考音频）
- `tts-generation` skill（MiMo 合成）

### 输出

| 文件 | 路径 |
|------|------|
| 脚本 | `<article_dir>/_podcast/播客_脚本.txt` |
| 标题描述 | `<article_dir>/_podcast/播客_标题与描述.txt` |
| 音频 | `<article_dir>/_podcast/播客_TTS.mp3`（320k, -16 LUFS, 8-12 min） |
| state | `<article_dir>/_podcast/state.json`（其内部续跑账本） |

### 并行
与 Phase 3b-render（生图）**并行**委派（播客不依赖 PNG，只读文章和 segments.json）。**集号 claiming**：article-to-solo-podcast 会读集号；编排器在 Phase 7 发布成功后才 `bump_episode.py` 递增，期间集号不变。

---

## Phase 5 — 视频：委派 `article-to-video`（顺序 CLI）

**职责**：文章+插图+封面+播客音频 → 16:9 视频（Ken Burns + 烧录字幕）。无 agents、无交互，纯 5 阶段 CLI。

### 前置条件（必须全部就绪）
- `公众号_文章.md`（含 `![](imgs/NN-xxx.png)` 插图引用） ← Phase 3b-render 回写后
- `imgs/*.png` ← Phase 3b-render
- `公众号_封面.png` ← Phase 3a
- `_podcast/播客_TTS.mp3` ← Phase 4（用作旁白音频，不重新 TTS）
- `_podcast/播客_脚本.txt` ← Phase 4（字幕对齐用）

### 调用（顺序，各带 `--article-dir`，阶段间读 `_video/state.json` 续跑）

```bash
<a2v_scripts>=.zcode/skills/article-to-video/scripts

<py> <a2v_scripts>/align_captions.py --article-dir "<article_dir>" --force
<py> <a2v_scripts>/plan_scenes.py     --article-dir "<article_dir>"
<py> <a2v_scripts>/render_kenburns.py --article-dir "<article_dir>"
<py> <a2v_scripts>/captions_to_ass.py --article-dir "<article_dir>"
<py> <a2v_scripts>/compose_video.py   --article-dir "<article_dir>"
```

### 输出

| 文件 | 路径 |
|------|------|
| 视频 | `<article_dir>/_video/公众号_视频.mp4`（1920×1080, 30fps, H.264） |
| state | `<article_dir>/_video/state.json`（其内部续跑账本） |

### 断点续跑
article-to-video 的每个脚本读 `_video/state.json` 的 phase1-5 key，已完成则跳过。编排器在 `stages.video.status` 追踪整体是否完成。

---

## 并行编排总览

```
Phase 2（文章）完成，拿到 article_dir
        │
        ▼
   ┌────┴────┬────────────┐
   ▼         ▼            ▼
 3a 封面   3b 插图       4 播客      （三者并行委派）
   │         │            │
   └────┬────┴────────────┘
        ▼ （三者全完成，尤其 3b 回写 + 4 音频）
     Phase 5 视频（顺序 CLI）
        │
        ▼
     Phase 6 归档（内联）
```

> **依赖**：Phase 5 依赖 Phase 3b（插图引用回写）+ Phase 4（播客音频）。Phase 3a（封面）只被 Phase 5 和 Phase 6/7 需要，不阻塞 3b/4，故可纯并行。
