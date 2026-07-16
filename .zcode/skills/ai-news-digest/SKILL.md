---
name: ai-news-digest
version: "1.0.0"
description: >
  AI 资讯日报编排器。从 bestblogs 信源表（RSS）每日采集最新 AI 资讯，规则预筛 +
  主模型打分排序生成当日榜单，整理成带信源的事实素材，委派 article-studio（news 类型）
  写一篇公众号日报文章，并把文章转成播客音频和横版视频，最后以草稿形式发布到三平台——
  公众号通过 API 上传草稿、喜马拉雅上传播客、抖音上传视频。一键 `/ai-news-digest` 跑完
  采集→打分→写作→播客→视频→发布全流程。**触发场景**：用户提到"AI 日报""今日 AI 资讯"
  "今天 AI 有什么新闻""生成 AI 日报""AI 资讯发三平台""每日 AI digest"，或想从 RSS 信源
  生成当日 AI 资讯并产出文章/播客/视频时使用。
metadata:
  orchestrator: true
  platforms: [gongzhonghao, boker, douyin]
  source: rss
---

# AI News Digest — AI 资讯日报编排器

把 RSS 信源 → 当日 AI 资讯榜单 → 公众号文章 + 播客 + 视频 → 三平台草稿发布，串成一条端到端流水线。

本 skill 是**纯编排器**（`metadata.orchestrator: true`）——它本身不生产内容，只负责：RSS 采集归一化、规则预筛、AI 打分、事实素材生成、按序委派下游 skill、归档校验、发布。

## 关联 Skills

| Skill | 职责 | 调用方式 |
|-------|------|---------|
| —（本 skill 内置） | Phase 1-5 采集/预筛/打分/榜单/事实素材 | `scripts/poll_feeds.py` 等 5 个脚本 |
| `article-studio` | 事实素材 → 公众号日报文章（news 类型，transcript 模式） | skill 委派（结构化字段） |
| `article-cover-image-generator` | 公众号封面图（900x383） | skill 委派（结构化字段） |
| `article-illustrator` | 文章插图（两步：prepare + render） | skill 委派（结构化字段） |
| `article-to-solo-podcast` | 文章 → 播客音频（单人独白 + TTS） | skill 委派（结构化字段） |
| `article-to-video` | 文章+插图+播客 → 横版视频（Ken Burns + 字幕） | 顺序 CLI 脚本 |
| `browser-publisher` | 三平台草稿发布（公众号 API / 喜马拉雅浏览器 / 抖音浏览器） | skill 委派 |

## 命令约定

- **`<py>`** = `config.environment.conda_python`（`D:\Development\miniconda3\python.exe`）。**绝不要假设 PATH 上的 `python` 是对的**，始终用 `<py>`。
- **`<scripts>`** = `.zcode/skills/ai-news-digest/scripts`。
- **`<a2s_scripts>`** = `.zcode/skills/audio-to-social/scripts`（复用脚本）。
- **`<a2v_scripts>`** = `.zcode/skills/article-to-video/scripts`。
- 子 skill 脚本用各自 config 的 python 路径。

## 核心原则

1. **信源驱动，禁止虚构**。日报内容只能来自当日 RSS 采集的真实资讯条目，每条引用带信源链接。不编造新闻。
2. **榜单与沉淀解耦**。榜单（digest.md）是轻量"扫一眼"视野；事实素材文件（_research/事实素材与来源.md）才是文章写作的唯一权威源。
3. **article-studio transcript 模式**：把抓取的资讯整理成带信源的事实素材文件，作为 article-studio 的唯一权威源（零外部事实）。article-studio 不再重新联网检索。
4. **状态机 + 断点续跑**。`state.json` 是状态机唯一真源，每步完成即回写；恢复时跳过已完成步骤。
5. **发布逻辑全部复用** `browser-publisher`，本 skill 不重写任何发布代码。
6. **集号单一来源**：`audio-to-social/config.json` 的 `platforms.boker_next_episode`（与 audio-to-social 共享，同一天只跑一个）。

## 流程概览

```text
/ai-news-digest
   ▼
[Phase 0] 初始化：读 config → 建 articles/{YYYY-MM-DD}_AI日报/ → 写 state.json
   ▼
[Phase 1] 采集：RSS 并发轮询 → 候选列表（poll_feeds.py）
   ▼
[Phase 2] 预筛：去重 + 源质量加权 + 截 top（prefilter.py）
   ▼
[Phase 3] AI 打分：生成 prompt → 主模型逐条打分 + 一句话摘要 → 排序取 top 20（merge_scores.py）
   ▼
[Phase 4] 榜单：生成 digest.md（build_digest.py digest）
   ▼
[Phase 4.5] 榜单审核：主 agent 按 agents/digest-reviewer.md 复核 4 维度 → apply_review.py 修正 [review_enabled]
   ▼
[Phase 5] 事实素材：digest_ranked.json → _research/事实素材与来源.md（build_research_md.py）
   ▼
[Phase 6] 文章：委派 article-studio（news 类型 + transcript 模式 + AI 小周人设）→ 公众号_文章.md
   ▼
[Phase 7] 多格式（按 config.media 开关并行委派，默认开封面+播客，关插图+视频）：
   ├─ 7a 封面：article-cover-image-generator → 公众号_封面.png          [cover_enabled]
   ├─ 7b 插图：article-illustrator（prepare → render，回写文章）        [illustrations_enabled, 默认关]
   ├─ 7c 播客：article-to-solo-podcast（fast_fallback）→ _podcast/播客_TTS.mp3（占集号）[tts_podcast_enabled]
   └─ 7d 视频：article-to-video（7b 回写 + 7c 音频完成后）→ _video/公众号_视频.mp4 [video_enabled, 默认关]
   ▼
[Phase 8] 归档：校验产物 + 图片压缩 + reconcile 一致性
   ▼
[Phase 9] 发布（可选，草稿模式）：
   ├─ 公众号：API 建草稿（browser-publisher）
   ├─ 喜马拉雅：浏览器上传播客（browser-publisher）+ 递增集号
   └─ 抖音：浏览器上传视频（browser-publisher，可定时）
```

## 状态机

状态机串（详见 [references/state-schema.md](references/state-schema.md)）：

```
normalize → fetch → prefilter → score → digest → review → research → article → media → podcast → video → archive → (publish)
```

每 stage 完成立即写 `state.json.stages.{stage}.status="completed"` + 产物路径。重入时若该 stage 已 completed 直接跳过；若下游 skill 自己的 state（`_podcast/state.json`、`_video/state.json`）显示其内部已完成，也视为本阶段完成。

## 入口协议

1. **读 config.json** 确定 storage_root、信源表、平台开关、日期（默认今天）。
2. **建项目目录**：`{storage_root}/articles/{YYYY-MM-DD}_AI日报/`（YYYY-MM-DD 取当日，标题固定"AI日报"，article-studio 写作时会生成真实标题但目录名不变）。
3. **初始化 state.json**（结构见 [references/state-schema.md](references/state-schema.md)），`stages.normalize.status="completed"`。
4. **判断恢复**：若项目目录已存在且 state.json 存在，读 state 跳过已完成阶段。

## 各阶段详解

### Phase 1 — RSS 采集（status: `fetch`）

并发轮询信源表里所有 ARTICLE 类（可按 category 过滤到 Artificial_Intelligence）的 feed，按时间窗口 + last_seen_link 游标双重过滤取近 N 小时新条目。

```bash
<py> <scripts>/poll_feeds.py \
  --sources configs/bestblogs-sources/sources.json \
  --state configs/ai-news-digest/state.json \
  --output "<article_dir>/temp/candidates_raw.json" \
  --hours 24 --concurrency 20 --timeout 15 \
  --types ARTICLE --categories Artificial_Intelligence
```

- **增量游标**：`configs/ai-news-digest/state.json` 记录每源 `last_seen_link`，时间窗口兜底 + 游标优先过滤
- **时间过滤**：默认只取近 24h 条目（`config.sources.hours_window`）
- **产出**：`temp/candidates_raw.json`（含 title/link/published/summary/source_name 等）
- 完成 → `stages.fetch.status="completed"`，记 source_count / candidate_count

### Phase 2 — 预筛（status: `prefilter`）

纯规则打分，零 AI 成本。

```bash
<py> <scripts>/prefilter.py \
  --candidates "<article_dir>/temp/candidates_raw.json" \
  --sources configs/bestblogs-sources/sources.json \
  --output "<article_dir>/temp/candidates_prefiltered.json" \
  --config .zcode/skills/ai-news-digest/config.json
```

- 按 subscriberCount 归一化打源质量分；标题含推广关键词剔除（词表从 config 读）；同源封顶（防刷屏）
- 截取 top（`config.scoring.prefilter_top`，默认 80）
- 完成 → `stages.prefilter.status="completed"`

### Phase 3 — AI 打分（status: `score`）

用**主对话模型**对预筛后的候选跨文章打分排序。两步：

1. **生成打分 prompt**：
   ```bash
   <py> <scripts>/build_digest.py prompt \
     --candidates "<article_dir>/temp/candidates_prefiltered.json" \
     --output "<article_dir>/prompts/scoring_prompt.md" --top 50
   ```
2. **主 agent 打分**：读 `prompts/scoring_prompt.md`，在对话里对候选逐条打分（1-10）+ 一句话摘要，输出 JSON 数组写入 `prompts/scoring_result.json`：
   ```json
   [{"index": 1, "score": 8, "summary": "OpenAI 发布 GPT-5..."}, ...]
   ```
3. **合并排序**：
   ```bash
   <py> <scripts>/merge_scores.py \
     --candidates "<article_dir>/temp/candidates_prefiltered.json" \
     --scores "<article_dir>/prompts/scoring_result.json" \
     --output "<article_dir>/temp/digest_ranked.json" --top 20
   ```
- 完成 → `stages.score.status="completed"`

### Phase 4 — 生成榜单（status: `digest`）

```bash
<py> <scripts>/build_digest.py digest \
  --ranked "<article_dir>/temp/digest_ranked.json" \
  --output "<article_dir>/temp/digest.md"
```

- 产出 Markdown 表格榜单（标题/来源/分类/AI分/信源分/链接），给人扫一眼
- 完成 → `stages.digest.status="completed"`

### Phase 4.5 — 榜单审核（status: `review`）

**自动化质量把关**，替代之前的"Phase 4 后人工确认 gate"——不再停下来等用户确认榜单，由主 agent 扮演榜单审核员做机械复核后自动继续。

主对话 agent **按 [agents/digest-reviewer.md](agents/digest-reviewer.md) 契约行事**（与 Phase 3 打分一致的"主 agent 直接做"模式，不 dispatch 子 agent），复核 4 个维度：

1. **AI 相关度复核**：揪出被误标 `ai_related=true` 的非 AI 条目（Phase 3 硬过滤可能漏网）→ drop
2. **排序与重要性**：高分条目（≥8）是否名副其实；明显高估 → demote 降分
3. **摘要忠实度**（反虚构 #4）：`ai_summary` 是否只概括 `summary`、不添加 → **仅记录报告**（由 Phase 5 忠实转写兜底）
4. **榜单卫生**：重复/同事件多源、推广词漏网、同源超额、24h 窗口外 → drop

流程：
1. 主 agent 读 `temp/digest_ranked.json`，按契约 4 维度复核
2. 确定性问题写 `temp/review_actions.json`（drop/demote 指令），全部发现写 `temp/review-report-1.json`
3. 若有 actions（`actions_count > 0`）：
   ```bash
   <py> <scripts>/apply_review.py \
     --ranked "<article_dir>/temp/digest_ranked.json" \
     --actions "<article_dir>/temp/review_actions.json" \
     --digest-md "<article_dir>/temp/digest.md"
   ```
   脚本删条目/降分/重排/同步统计字段/重生成 `digest.md`（幂等，断点续跑安全）。无 actions 跳过此步。
4. 完成 → `stages.review.status="completed"`，自动进入 Phase 5

> **审核纪律**（见 `agents/digest-reviewer.md`）：只删不改增（绝不补充新闻，反虚构约束 #1）；只在"明显且可机械判定"的问题上动手，拿不准的不动；只操作 `temp/` 下的榜单，不碰 `_research/事实素材与来源.md`。
> `config.scoring.review_enabled: false` 时 `stages.review.status="skipped"`，跳过审核直接进 Phase 5。

### Phase 5 — 生成事实素材（status: `research`）

**衔接 article-studio 的关键胶水**。

```bash
<py> <scripts>/build_research_md.py \
  --ranked "<article_dir>/temp/digest_ranked.json" \
  --output "<article_dir>/_research/事实素材与来源.md" \
  --persona AI小周
```

把打分排序后的资讯转写成 article-studio transcript 模式期望的格式：
- 顶部声明：RSS 采集日期 + news 类型说明 + AI 小周人设
- 按 source_category 自动分 `##` 主题节
- 每条事实 bullet：AI 摘要 + 来源名 + 原文链接 + 事件日期 + 采集日期
- 文末 `## 写作立场/素材` 区：AI 小周人设 + news 盘点锚点 + 反虚构硬约束提醒

**反虚构硬约束**：文章内容只能来自本文件内的资讯条目，不编造榜单外新闻。
- 完成 → `stages.research.status="completed"`

### Phase 6 — 写文章（status: `article`）

委派 `article-studio`（**transcript 模式 + news 类型**），传结构化字段：

| 字段 | 值 | 说明 |
|------|----|----|
| `source_mode` | `"transcript"` | 触发 transcript 模式（跳过联网检索，事实素材为唯一权威源） |
| `source_file` | `<article_dir>/_research/事实素材与来源.md` | Phase 5 产出 |
| `article_type` | `news` | 资讯/盘点类型（重信息密度、每条带日期+信源） |
| `output_dir` | `<article_dir>`（已存在） | article-studio 直接在此目录产出 |
| `persona` | `AI小周` | AI 日报人设（区别于个人随笔的第一人称） |

article-studio 走双主编并行审查门禁（内容主编 5 维度 + 读者代表 3 维度），news 类型红线子集（1/2/6，时效标注最重）。

**产出**：`公众号_文章.md` + `公众号_摘要.txt`。**委派后立即校验**：read_file 验证文件存在且非空，失败带上下文重试 1 次。
- 完成 → `stages.article.status="completed"`

### Phase 7 — 多格式（按 `config.media` 开关并行委派）

文章完成后，按 [references/delegation-contracts.md](references/delegation-contracts.md) 的并行时序委派。**各资产由 `config.media.{asset}_enabled` 开关控制**：

| 资产 | 开关 | 默认 | 说明 |
|------|------|------|------|
| 7a 封面 | `cover_enabled` | ✅ 开 | 微信草稿 API 需要；900x383 |
| 7b 插图 | `illustrations_enabled` | ❌ 关 | 清单是可扫读文本，插图增益低；每张图需 Gaoding 浏览器自动化，成本高 |
| 7c 播客 | `tts_podcast_enabled` | ✅ 开 | 资讯口播有分发价值；委派说明指示走 fast_fallback 单写手（双人播客后续做） |
| 7d 视频 | `video_enabled` | ❌ 关 | 5 阶段 ffmpeg + Whisper 重转录，对清单价值最低；依赖插图做画面 |

> 用户可在启动前通过 `config.media.{asset}_enabled` 开关或对话显式开启任意资产。

**默认链路（插图/视频关）**——封面 + 播客并行，互不阻塞：
```
Phase 6（文章）完成
        │
        ├─▶ 7a 封面（article-cover-image-generator → 公众号_封面.png）
        │
        └─▶ 7c 播客（article-to-solo-podcast, fast_fallback → _podcast/播客_TTS.mp3）
             （插图关闭时无 segments.json 依赖，播客直接启动）
```

**全量链路（插图/视频开）**——照搬 audio-to-social 时序：
```
Phase 6（文章）完成
        │
        ▼
   ┌────┴────┬────────────┐
   ▼         ▼            ▼
 7a 封面   7b 插图       7c 播客     （7a/7b-prepare/7c 并行委派）
   │      (prepare)        │
   │         │            │
   │      7b-render ───────┤ （7b-render 与 7c 并行）
   │         │            │
   └────┬────┴────────────┘
        ▼ （三者全完成，尤其 7b 回写 + 7c 音频）
     7d 视频（顺序 CLI）
```

- **7a 封面**：委派 `article-cover-image-generator` → `公众号_封面.png`（900x383）
- **7b-prepare 插图**（仅 `illustrations_enabled`）：委派 `article-illustrator`（prompt_only）→ `imgs/segments.json`
- **7c 播客**（`tts_podcast_enabled`）：委派 `article-to-solo-podcast`，**在委派说明里指示下游 agent 走 fast_fallback**（覆写其 config 的 `studio.enabled` 默认，走 solo-scriptwriter 单写手）→ `_podcast/播客_TTS.mp3`（**占集号**，从 audio-to-social config 读 `boker_next_episode`）。插图关闭时无需等 7b-prepare（无 segments.json 依赖）。
- **7b-render 插图**（仅 `illustrations_enabled`，与 7c 并行）：生图 + 回写文章
- **7d 视频**（仅 `video_enabled`，7b-render + 7c 完成后）：顺序调 `article-to-video` 的 5 个 CLI 脚本 → `_video/公众号_视频.mp4`

### Phase 8 — 归档（status: `archive`）

内联：
- 校验所有产物存在（文章/摘要/封面/插图/播客/视频）
- 图片压缩（复用 `<a2s_scripts>/compress_images.py`）
- reconcile 一致性检查（复用 `<a2s_scripts>/reconcile_media.py`）
- 完成 → `stages.archive.status="completed"`

### Phase 9 — 发布（可选，草稿模式）

详见 [references/publishing.md](references/publishing.md)。委派 `browser-publisher`：

- **公众号草稿**（API，不需浏览器）：`wechat-mp-draft.py`，建草稿后 `draft/get` 回读验证
- **喜马拉雅**（浏览器）：上传播客，发布后递增集号（`<a2s_scripts>/bump_episode.py`）
- **抖音**（浏览器，可定时）：上传视频

**发布前必须截图确认**（三平台）。完成 → `publish.tracks.{platform}.status="published"`。

## 确认规则

- **Phase 9 发布前必须截图确认**（公众号草稿箱 / 喜马拉雅上传页 / 抖音发布页）。这是整个流水线唯一的人工确认点。
- 公众号发表（非草稿）需用户明确同意并扫码。
- 其余阶段默认直跑，失败不自动重试，报告 `last_failed_step` + `error_message` 让用户决定。

## 产物布局

```
articles/{YYYY-MM-DD}_AI日报/           ← 本 skill Phase 0 建（标题固定，article-studio 不改目录名）
├── 公众号_文章.md                        ← Phase 6（article-studio），含插图占位符 → Phase 7b 回写 ![]()
├── 公众号_摘要.txt                       ← Phase 6
├── 公众号_封面.png                       ← Phase 7a（cover-generator）
├── _research/
│   └── 事实素材与来源.md                 ← Phase 5（build_research_md.py，article-studio 的权威源）
├── imgs/                                ← Phase 7b（illustrator）
│   ├── outline.md
│   ├── segments.json                    ← 7b-prepare，Phase 7c 播客的前置
│   ├── prompts/*.md
│   └── NN-{type}-{slug}.png
├── _podcast/                            ← Phase 7c（article-to-solo-podcast）
│   ├── 播客_脚本.txt
│   ├── 播客_标题与描述.txt
│   ├── 播客_TTS.mp3
│   └── state.json
├── _video/                              ← Phase 7d（article-to-video）
│   ├── 公众号_视频.mp4
│   └── state.json
├── temp/                                ← Phase 1-4 中间产物
│   ├── candidates_raw.json
│   ├── candidates_prefiltered.json
│   ├── digest_ranked.json
│   └── digest.md
├── prompts/                             ← Phase 3 打分 prompt + 结果
│   ├── scoring_prompt.md
│   └── scoring_result.json
└── state.json                           ← 编排器状态机（单一来源）
```

## 按需加载

| 文件 | 用途 | 加载时机 |
|------|------|---------|
| [references/delegation-contracts.md](references/delegation-contracts.md) | 下游 skill 委派契约（输入/输出/并行） | Phase 6-9 |
| [references/state-schema.md](references/state-schema.md) | state.json 完整 schema | 启动/每阶段回写 |
| [references/preferences-schema.md](references/preferences-schema.md) | config.json 字段说明 | 初始化 |
| [references/publishing.md](references/publishing.md) | 三平台草稿发布细节 | Phase 9 |
| `agents/_shared.md` | 路径常量/返回格式/反虚构/错误码（若用子 agent） | 子 agent 委派时 |
| [agents/digest-reviewer.md](agents/digest-reviewer.md) | 榜单审核 agent 契约（4 维度/动作/落盘 schema） | Phase 4.5 |
| [scripts/apply_review.py](scripts/apply_review.py) | 把审核修正指令落地（删条目/降分/重排/重生成榜单） | Phase 4.5 |

## 配置来源

- **本 skill `config.json`**：`sources`（信源/窗口/并发）、`scoring`（截取数/推广词/字数）、`article`（类型/人设）、`media`（各产物开关）、`platforms`（三平台开关）、`environment`（python/ffmpeg/key 引用名）。
- **`audio-to-social/config.json`（只读复用）**：`brand`、`cover`、`image`、`tts`、`platforms.boker_next_episode`（集号单一来源）。
- **`configs/bestblogs-sources/sources.json`**：信源表（1686 条，AI 类 170+，详见 `configs/bestblogs-sources/sources.md`）。
