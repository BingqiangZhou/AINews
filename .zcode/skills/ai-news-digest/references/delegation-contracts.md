# 委派契约（下游 skill 输入/输出/并行规则）

> 本编排器把内容生产委派给 6 个下游 skill。本文件是**唯一的委派契约真源**——每个 skill 的精确输入字段、输出产物、调用方式、断点续跑语义、并行关系都在此定义。

通用约定：
- **项目根**：`articles/{YYYY-MM-DD}_AI日报/`（Phase 0 由本 skill 建立，与 audio-to-social 不同——audio-to-social 让 article-studio 建目录，本 skill 因采集阶段需先落中间产物故自建）。下文 `<article_dir>` = 该路径。
- **`<py>`** = `config.environment.conda_python`（`D:\Development\miniconda3\python.exe`）。
- **`<scripts>`** = `.zcode/skills/ai-news-digest/scripts`。
- **`<a2s_scripts>`** = `.zcode/skills/audio-to-social/scripts`（复用脚本）。
- **`<a2v_scripts>`** = `.zcode/skills/article-to-video/scripts`。
- **委派后立即校验**：返回后 read_file 验证输出产物存在且非空；失败带上下文重试 1 次，仍失败记 `stages.{stage}.status="failed"` 并跳过。
- **断点续跑**：每阶段完成立即写 `state.json.stages.{stage}.status="completed"` + 产物路径。重入时若该 stage 已 completed 直接跳过；若下游 skill 自己的 state（如 `_podcast/state.json`）显示其内部已完成，也视为本阶段完成。

---

## Phase 6 — 文章：委派 `article-studio`（transcript 模式 + news 类型）

**职责**：事实素材文件 → 书面公众号日报文章（news 类型）。零联网、事实素材为唯一权威源，双主编审查门禁。

### 输入（结构化，传给 article-studio）

| 字段 | 值 | 说明 |
|------|----|----|
| `source_mode` | `"transcript"` | 触发 transcript 模式（跳过联网检索，事实素材为权威源） |
| `source_file` | `<article_dir>/_research/事实素材与来源.md` | Phase 5 产出（build_research_md.py） |
| `article_type` | `news` | 资讯/盘点类型（重信息密度、每条带日期+信源，`max_sections: 8`） |
| `output_dir` | `<article_dir>`（已存在） | article-studio 直接在此目录产出（不新建目录） |
| `persona` | `AI小周` | AI 日报人设（事实素材文件文末已声明，article-studio writer 据此调整口吻） |

> **注意**：本 skill 已在 Phase 0 建好 `<article_dir>`。article-studio transcript 模式检测到 output_dir 已存在时直接使用，不重建。若 article-studio 行为不符，把 source_file 路径明确传入，由 article-studio 在该目录产出。

### 输出（article-studio 产出）

| 文件 | 路径 | 说明 |
|------|------|------|
| 文章 | `<article_dir>/公众号_文章.md` | 首行 `# 标题`，含 `<!-- illustration -->` 占位符（2-4 个，供 Phase 7b 回写） |
| 摘要 | `<article_dir>/公众号_摘要.txt` | ≤120 字 |
| article-studio state | `<article_dir>/state.json` | `phase: "editor_passed"`，`source_mode: "transcript"`，`article_type: "news"` |

### 关键约定
- **反杜撰不变量**：article-studio transcript 模式保证零外部事实（详见 `article-studio/references/transcript-mode.md`）。事实素材文件里没有的资讯一律不写。
- **news 类型红线**：article-studio 双主编会按 news 类型启用红线 1/2/6（时效标注最重），与事实素材文件文末的"news 类型红线提醒"一致。
- **AI 小周人设**：事实素材文件文末已声明 AI 小周人设 + 日报视角锚点，article-studio writer 据此写客观简洁的盘点口吻（区别于个人随笔的第一人称）。

---

## Phase 7a — 封面：委派 `article-cover-image-generator`（全量模式）

**职责**：标题+核心论点 → 公众号封面（900x383）。全量模式内部再委派 `image-generator` 出图（Gaoding 后端）。

### 输入（结构化）

| 字段 | 值 | 说明 |
|------|----|----|
| `content_context` | 文章标题 + 核心论点/主题关键词 | 从 `公众号_文章.md` 提取（标题 + 摘要或首段） |
| `target_size` | `"900x383"` | 公众号封面尺寸（audio-to-social config `image.cover_size`） |
| `output_path` | `<article_dir>/公众号_封面.png` | 固定文件名（browser-publisher 契约） |
| `output_dir` | `<article_dir>` | prompts/ 与产物落此处 |
| `visual_preset` | `auto` | auto-mapping（仅影响封面 type/mood；封面 palette/rendering/font 已固定为 hand-drawn-edu 预设 + 手写字体，见 article-cover-image-generator 规则 #14） |
| `cover_provider` | `gaoding` | gaoding / jimeng / agnes；默认 Gaoding，不回退 Agnes（audio-to-social config `cover.provider`） |

### 输出

| 文件 | 路径 |
|------|------|
| 封面 | `<article_dir>/公众号_封面.png` |

### 并行
可与 Phase 7b（插图）、Phase 7c（播客）**并行**委派。

---

## Phase 7b — 插图：委派 `article-illustrator`（两步：prepare + render）

**职责**：决定插图位置+内容并生成图片。拆成两步委派，消除 conductor 与 segments.json 的隐藏竞态（Phase 7c 的 conductor 依赖 segments.json）。

### Phase 7b-prepare（prompt_only 模式，先跑）

**职责**：分析文章 + 切段 + 产出 prompt 文件 + segments.json（含 illustration_meta）。

| 字段 | 值 | 说明 |
|------|----|----|
| 文章路径 | `<article_dir>/公众号_文章.md` | illustrator 读 `<!-- illustration -->` 占位符位置 |
| `visual_preset` | `auto` | auto-mapping 到 illustrator preset |
| `density` | `balanced`（3-5 张） | 可按文章长度调 |
| `prompt_only` | `true` | 产出 prompt + segments.json 后返回，不生图 |
| output dir | `<article_dir>/imgs/` | illustrator 原生产物目录 |

### 输出（7b-prepare）

| 文件 | 路径 | 说明 |
|------|------|------|
| outline | `<article_dir>/imgs/outline.md` | 插图大纲 |
| prompts | `<article_dir>/imgs/prompts/*.md` | 每张插图的 prompt |
| segments | `<article_dir>/imgs/segments.json` | 章节→插图分段 + illustration_meta（**Phase 7c conductor 的前置**） |

### Phase 7b-render（生图+回写，与 Phase 7c 并行）

**职责**：从 7b-prepare 的断点续跑，生成 PNG + 回写文章。

- **方式 A**（推荐）：再次委派 `article-illustrator`，它检测到 prompt 文件已存在则续跑（生图 + 回写）。
- **方式 B**：批量委派 `article-cover-image-generator` 生成所有 PNG，再由 illustrator 回写。

### 输出（7b-render）

| 文件 | 路径 | 说明 |
|------|------|------|
| 插图 | `<article_dir>/imgs/NN-{type}-{slug}.png` | PNG（WeChat 不接受 webp） |
| 文章（回写） | `<article_dir>/公众号_文章.md` | 占位符被替换为 `![](imgs/NN-xxx.png)` |

### 关键约定
- 7b-prepare 必须先于 Phase 7c 完成（segments.json 是 conductor 的前置）。
- 7b-render 与 Phase 7c 并行（播客不依赖 PNG）。

---

## Phase 7c — 播客：委派 `article-to-solo-podcast`

**职责**：文章 → 播客脚本 + TTS 音频（10 维 rubric + 集号管理）。已原生支持文章输入，输出嵌套 `_podcast/`。

### 前置条件
- **Phase 7b-prepare 完成**：`<article_dir>/imgs/segments.json` 就绪。conductor 读它来按 segment 分组要点 + 据 illustration_meta 让播客要点和图内容对齐。无 segments.json 时 conductor 退回平铺要点（向下兼容）。

### 输入

| 字段 | 值 | 说明 |
|------|----|----|
| `--input` | `<article_dir>/公众号_文章.md` | 文章（含插图引用无妨，ingest_article.py 会清洗） |

article-to-solo-podcast 自动读：
- `<article_dir>/imgs/segments.json`（Phase 7b-prepare 产出）
- `audio-to-social/config.json` 的 `platforms.boker_next_episode`（集号，**与 audio-to-social 共享单一来源**）
- `audio-to-social/scripts/voice_ref.wav`（TTS 克隆参考音频）
- `tts-generation` skill（MiMo 合成）

### 输出

| 文件 | 路径 |
|------|------|
| 脚本 | `<article_dir>/_podcast/播客_脚本.txt` |
| 标题描述 | `<article_dir>/_podcast/播客_标题与描述.txt` |
| 音频 | `<article_dir>/_podcast/播客_TTS.mp3`（320k, -16 LUFS, 8-12 min） |
| state | `<article_dir>/_podcast/state.json`（其内部续跑账本） |

### 并行与集号
与 Phase 7b-render（生图）**并行**委派（播客不依赖 PNG，只读文章和 segments.json）。
**集号 claiming**：article-to-solo-podcast 会读集号；本编排器在 Phase 9 发布成功后才调 `bump_episode.py` 递增，期间集号不变。**与 audio-to-social 共享同一集号源，同一天不要同时跑两者**。

---

## Phase 7d — 视频：委派 `article-to-video`（顺序 CLI）

**职责**：文章+插图+封面+播客音频 → 16:9 视频（Ken Burns + 烧录字幕）。无 agents、无交互，纯 5 阶段 CLI。

### 前置条件（必须全部就绪）
- `公众号_文章.md`（含 `![](imgs/NN-xxx.png)` 插图引用） ← Phase 7b-render 回写后
- `imgs/*.png` ← Phase 7b-render
- `公众号_封面.png` ← Phase 7a
- `_podcast/播客_TTS.mp3` ← Phase 7c（用作旁白音频，不重新 TTS）
- `_podcast/播客_脚本.txt` ← Phase 7c（字幕对齐用）

### 调用（顺序，各带 `--article-dir`，阶段间读 `_video/state.json` 续跑）

```bash
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

## Phase 8 — 归档（内联，无委派）

**职责**：校验所有产物存在、图片压缩、一致性检查。纯内联操作，复用 audio-to-social 脚本。

### 步骤

1. **产物完整性校验**：检查 `公众号_文章.md` / `公众号_摘要.txt` / `公众号_封面.png` / `imgs/*.png` / `_podcast/播客_TTS.mp3` / `_video/公众号_视频.mp4`（按 `config.media.*_enabled` 开关，关闭的产物不校验）。
2. **图片压缩**（复用）：
   ```bash
   <py> <a2s_scripts>/compress_images.py --files "<article_dir>/公众号_封面.png" "<article_dir>/imgs/*.png" --quality 80
   ```
3. **reconcile 一致性检查**（复用）：
   ```bash
   <py> <a2s_scripts>/reconcile_media.py --output-dir "<article_dir>" --require-cover --require-illustrations --cover-size 900x383 --report "<article_dir>/temp/reconcile-report.json"
   ```
   - 校验：封面尺寸、插图引用与文件一致、`<!-- illustration -->` 占位符已全部回写。

---

## Phase 9 — 发布：委派 `browser-publisher`（草稿模式）

详见 [publishing.md](publishing.md)。三平台草稿发布。

### 9a 公众号草稿（API，不需浏览器）
```bash
<py> .zcode/skills/browser-publisher/scripts/wechat-mp-draft.py --project-dir "<article_dir>"
```
- 前置：`WECHAT_MP_APPID`/`WECHAT_MP_APPSECRET` 环境变量 + IP 白名单
- 草稿创建后**必须**用 `draft/get` 回读验证（标题/图片/无转义）
- 默认只建草稿（`config.platforms.gongzhonghao.mode = "draft_only"`），发表需用户确认扫码

### 9b 喜马拉雅（浏览器）
- 委派 `browser-publisher`，按 `browser-publisher/references/ximalaya.md` 步骤：导航上传页 → 选专辑 → 上传 `_podcast/播客_TTS.mp3` → 填标题(含集号) → 标记 AI 合成 → 填简介/标签 → 确认发布
- 发布后递增集号：
  ```bash
  <py> <a2s_scripts>/bump_episode.py --config .zcode/skills/audio-to-social/config.json --state "<article_dir>/state.json" --bump
  ```

### 9c 抖音（浏览器，可定时）
- 委派 `browser-publisher`，按 `browser-publisher/references/douyin.md` 步骤上传 `_video/公众号_视频.mp4`
- 支持 `publish_mode: timed` + `scheduled_at`（窗口 now+2h~+14d）

每平台发布后更新 `state.json.publish.tracks.{platform}`。**发布前必须截图确认**。

---

## 并行编排总览

```
Phase 6（文章）完成，拿到终稿公众号_文章.md
        │
        ▼
   ┌────┴────┬────────────┐
   ▼         ▼            ▼
 7a 封面   7b 插图       7c 播客      （7a/7b-prepare/7c 并行委派）
   │      (prepare)        │
   │         │            │
   │      7b-render ───────┤ （7b-render 与 7c 并行）
   │         │            │
   └────┬────┴────────────┘
        ▼ （三者全完成，尤其 7b 回写 + 7c 音频）
     Phase 7d 视频（顺序 CLI）
        │
        ▼
     Phase 8 归档（内联）
        │
        ▼
     Phase 9 发布（草稿模式，可选）
```

> **依赖**：Phase 7d 依赖 Phase 7b（插图引用回写）+ Phase 7c（播客音频）。Phase 7a（封面）只被 Phase 7d 和 Phase 8/9 需要，不阻塞 7b/7c，故可纯并行。
