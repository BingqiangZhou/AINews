---
name: article-studio
version: "2.1.0"
description: >
  写**任意类型公众号文章**——给一个主题、你的口述立场/素材，先选文章类型（观点/时评、干货/教程、故事/叙事、
  资讯/盘点、人物/访谈、种草/测评），skill 联网检索建立事实底座（带信源 URL），按该类型的结构骨架写正文，
  再用**双主编并行审查**（内容主编 5 维度+红线卡事实/分寸，读者代表 3 维度卡阅读体验/获得感），
  输出通过审查的公众号_文章.md。**触发场景**：用户说"写一篇公众号文章"、给主题+立场/素材要写公众号、
  或需要"有主编把关"的文章时使用。本 skill 按类型路由写带声音的公众号文（止步审查通过）。
  **不编排**配图/封面/发布/播客（由用户后续手动调 article-illustrator / article-cover-image-generator /
  browser-publisher / article-to-solo-podcast）。
  **transcript 模式**：被编排器（如 ai-news-digest）调用时，输入可是一段录音转录文本（`source_mode: transcript`），
  此时跳过联网检索、转录为唯一权威源、零外部事实，把口语转录改写为书面公众号文。
metadata:
  supported_types: [opinion, howto, story, news, profile, review]
  default_type: opinion
  source_modes: [stance_research, transcript]
  research_mode: 联网（WebSearch + webReader）/ transcript 模式跳过联网
  review: 双主编并行（内容主编 5 维度+红线 / 读者代表 3 维度阅读体验）
  output: 公众号_文章.md（到双主编审查通过为止）
---

# Article Studio

写**任意类型公众号文章**。**选类型 → 联网取材 → 按类型骨架写作（叠加强化写作工艺）→ 双主编并行审查（内容主编卡事实/分寸，读者代表卡阅读体验）**，输出通过审查的 `公众号_文章.md`。

## 文章类型（Phase 0 第一件事）

本 skill 按文章类型路由，6 类全覆盖（详见 [type-profiles.md](references/type-profiles.md)）：

| `article_type` | 中文名 | 一句话定位 | 典型触发语 |
|---------------|--------|----------|-----------|
| `opinion` | 观点/时评 | 带明确立场的论证文，重说服力与分寸 | "写篇观点文/时评/评论" |
| `howto` | 干货/教程 | 传可复现方法，重步骤清晰与可照做 | "写篇教程/干货/怎么做X" |
| `story` | 故事/叙事（含情感） | 用故事传递观点或情绪，重代入感 | "写个故事/案例/情感文" |
| `news` | 资讯/盘点 | 高效传递时效信息，重信息密度 | "做个盘点/资讯汇总/周报" |
| `profile` | 人物/访谈 | 呈现人物立体形象，重借人讲事 | "写人物/访谈/Q&A" |
| `review` | 种草/测评 | 用证据建立信任，重证据链与适用性判断 | "做个测评/种草/横评" |

**类型决定**：结构骨架、声音强度、CTA 强弱、标题套路、字数阈值、取材重点、**启用哪些分寸红线**（opinion/review 全量 6 条；howto/news/profile 用通用子集 1/2/6；story 用最小子集 1/6）。

类型选不准时用 `config.json` 的 `default_article_type`（默认 `opinion`）。

## 源模式（`source_mode`，Phase 0 第二件事）

本 skill 支持两种事实来源模式（`config.source_modes`）：

| `source_mode` | 输入 | 事实真源 | 触发场景 |
|---------------|------|---------|---------|
| `stance_research`（默认） | `topic` + `stance` + `article_type` | 联网检索结果（每条带信源 URL） | 用户直接给主题+立场写文章 |
| `transcript` | `source_file`（转录文本）+ `article_type` | **转录文本**（零联网、零外部事实） | 被编排器（如 ai-news-digest）调用，输入是录音转录 |

**transcript 模式**（详见 [transcript-mode.md](references/transcript-mode.md)）：researcher 短路跳过联网检索，把转录文本落盘为 `_research/事实素材与来源.md`；writer 把口语转录改写为书面公众号文（保留核心观点与个人声音、插 `<!-- illustration -->` 占位符）；editor 的事实核查锚点改为对照转录原文。反杜撰不变量：转录里没有的事实一律不写。

被编排调用时（`source_mode: transcript`）从结构化输入接收 `source_file` 等；用户直接触发时默认 `stance_research`。

## 与相邻 skill 的边界

**本 skill 不编排**：配图/封面/草稿上传/播客/喜马拉雅。审查通过后，用户手动调对应 skill：
- 配图/封面 → `article-illustrator` / `article-cover-image-generator`
- 公众号草稿上传 → `browser-publisher`
- 播客 → `article-to-solo-podcast`

## 工作流（4 phase 状态机）

```text
initialized → researched → written →[ Phase 2 审查 ]→ editor_passed → (完成)
                  ↑                        │            │
                  └──── gap_blocked ────────┘            │
                                           ↑            │
                                   ┌── revise ──────────┘
                                   ↓
                              （≤ max_fix_rounds 轮）
```

状态机断点续跑：每个 phase 完成后写 `state.json`（含 `article_type`），重入时跳过已完成 phase。

### Phase 0 — 联网取材（`agents/researcher.md`）

> **先定 `source_mode`**（见上文"源模式"）：用户直接触发默认 `stance_research`；被编排器调用传 `source_mode: transcript` 时走 transcript 模式（详见 [transcript-mode.md](references/transcript-mode.md)）。

1. 通过 `AskUserQuestion` 收集（transcript 模式下从结构化输入接收，省略联网相关项）：
   - `topic`（主题）— transcript 模式下可选，writer 可从转录派生
   - `article_type`（文章类型，6 选 1；选不准用默认 `opinion`）
   - `stance`/`素材`（作者的立场/口述素材/经历，按类型含义不同：opinion 给立场，story 给经历，howto 给要教的点，review 给体验过的产品等）— transcript 模式下无此项，改收 `source_file`（转录文本路径）
2. **transcript 模式**：researcher 短路跳过联网，把转录落盘为 `_research`，`gap_blocked` 恒 false（转录没说的就是不能写的）。**stance_research 模式**继续下述联网流程：
3. 按 `article_type` 的 `research_focus`（见 [type-profiles.md](references/type-profiles.md)）调整检索 query 偏好
4. 拆检索关键词 → `WebSearch` 找候选 → `webReader`（mcp__web_reader__webReader）读全文
5. 产 `_research/事实素材与来源.md`：
   - 按主题 `##` 分节，每条事实 bullet 末尾带信源 URL + 检索日期
   - 文末独立 `## 写作立场/素材` 区存 `stance`（主观意图与检索事实分区）
6. **反虚构硬约束**：写作只能引用本文件内事实，禁止编造素材外信息
7. 关键事实缺口 → 标记 `gap_blocked`，补检索后重跑

→ 详见 [phase0-research.md](references/phase0-research.md)

### Phase 1 — 写作（`agents/article-writer.md`，DRAFT 模式）

1. 输入：`_research/事实素材与来源.md` + `stance`/素材（transcript 模式下无 stance，转录即素材）+ `article_type`
2. **加载 `article_type` 对应的 profile**（[type-profiles.md](references/type-profiles.md)）：按 `profile.structure` 骨架写，叠加 [phase1-writing.md](references/phase1-writing.md) 通用工艺底线
3. **叠加 [writing-craft.md](references/writing-craft.md) 写作工艺强化**：开头钩子（6 种模式按类型选）+ 软 AI 腔自查 + 阅读节奏排版（长短句/加粗克制/列表化）+ 每 200-300 字一个金句/记忆点
4. 声音强度 / CTA 强弱 / 标题套路均按 profile 走
5. **transcript 模式**：本质是口语转书面化改写——保留核心观点与个人声音、保留不确定性/认知转折、插 `<!-- illustration -->` 占位符（2-4 个），详见 [transcript-mode.md](references/transcript-mode.md)
6. 输出 `公众号_文章.md`（首行 `# 标题`，标题 `title_min_chars`-`title_max_chars` 字，或 profile 的 `content_overrides`）
7. 文末 AI 生成声明用 `>` 引用块样式（如 `> 本文由作者手写初稿，AI 辅助改写。`，详见 [redlines.md](references/redlines.md) 红线 6）

### Phase 2 — 双主编并行审查门禁（`agents/content-editor.md` + `agents/reader.md`）

**三层**（详见 [phase2-editor-review.md](references/phase2-editor-review.md)）：

- **2a 机器预检**（复用 `article-studio/scripts/validate_content_quality.py --platform gongzhonghao`）：标题/摘要/正文字数、小节数、AI 腔。error 必须清零才进 2b。
- **2b 双主编并行评分**（两个子 agent **同时并行**审查同一稿，互不依赖）：
  - **内容主编**（`agents/content-editor.md`，5 维度 × 1-10，详见 [editor-rubric.md](references/editor-rubric.md)）：`structure` / `accuracy` / `voice` / `format` / `honesty` + 红线（按类型启用子集）。**卡事实/逻辑/结构/分寸**。落盘 `scorecards/content-round-N.json`。
  - **读者代表**（`agents/reader.md`，3 维度 × 1-10）：`reading_experience`（阅读体验）/ `takeaway`（获得感）/ `engagement`（读得下去），标准对照 [writing-craft.md](references/writing-craft.md)。**卡阅读体验，不查事实/红线**。落盘 `scorecards/reader-round-N.json`。
- **2c 汇总判定**（主 agent 读两家 scorecard）：
  - **hard_block**（触发即 revise，不准放行）：内容主编 hard_block（[redlines.md](references/redlines.md) 中**该类型启用的红线子集**违反 / 事实编造夸大 / 任一维度 < `pass_bar.min_per_dimension`）**或** 读者代表 hard_block（`reading_experience` 或 `engagement` < 门槛；`takeaway` 低分不 block）
  - **pass**：两家都无 hard_block
  - **pass with notes**：第 `max_fix_rounds` 轮仍 hard_block，带保留意见放行

### Phase 3 — 修正循环（≤ `max_fix_rounds` 轮，默认 3）

- hard_block（任一家）→ `article-writer.md` 切 **FIX 模式**，传**两家合并后的 fix_directives**（内容主编的红线/事实指令优先，读者代表的阅读体验指令随后，建议性 takeaway 指令最后）
- 备份旧稿（复用 `ai-news-digest/scripts/backup_file.py`）→ 覆盖 → 重跑 2a+2b（双主编并行）出 round-(N+1)
- 达上限仍不过 → `pass with notes` 或阻塞由用户决定

### Phase 4 — 完成

- 两家都 pass → 输出最终 `公众号_文章.md` + `公众号_摘要.txt`
- 打印报告：文章类型、审查轮次、**两家**各维度分数轨迹、最终 verdict
- **明确告知**后续步骤需手动调其他 skill（贴出 skill 名）

## 输入输出

**输入**（`stance_research` 模式运行时 `AskUserQuestion` 收集；`transcript` 模式从结构化输入接收）：
- `source_mode`：`stance_research`（默认）| `transcript`
- `topic`：主题（一句话）— transcript 模式下可选，writer 可从转录派生
- `article_type`：文章类型（6 选 1，选不准用 `default_article_type`）
- `stance`/素材：作者的立场/口述素材/经历（按类型含义不同）— 仅 stance_research 模式
- `source_file`：转录文本路径 — 仅 transcript 模式

**产物目录**（`articles/{YYYY-MM-DD}_{标题}/`，无系列/序号层；全局总览见 [docs/article-manifest.md](../../../docs/article-manifest.md)；命名细则见 [article-conventions.md](references/article-conventions.md)）：

```
articles/{YYYY-MM-DD}_{标题}/
├── 公众号_文章.md              # 终稿（通过主编审查）
├── 公众号_摘要.txt             # 一句话摘要
├── _research/
│   └── 事实素材与来源.md        # 事实底座（stance_research=联网检索带 URL；transcript=转录原文，无 URL）
├── prompts/                    # 审查标准、写作 prompt 备份（含 content-editor/reader 两家）
├── imgs/ + imgs/prompts/       # 预留给后续 article-illustrator（本 skill 不填）
├── scorecards/
│   ├── content-round-N.json    # 内容主编审查 traceability（5 维度 + 红线）
│   └── reader-round-N.json     # 读者代表审查 traceability（3 维度阅读体验）
├── temp/                       # 中间产物
└── state.json                  # 状态机断点续跑（含 article_type + source_mode）
```

## 配置来源

- **本 skill 的 `config.json`**：`content`（字数/段落/小节默认阈值）、`article_types`（6 类枚举 + per-type 覆盖）、`default_article_type`、`source_modes` + `transcript_mode`、`evaluation`（修正轮数/门槛/**reviewers 双主编配置**/红线开关）、`environment`（复用脚本路径）。
- **`references/type-profiles.md`**：6 类 profile（结构骨架/rubric_focus/红线子集/voice/CTA/标题套路/字数覆盖/取材重点）。
- **`references/writing-craft.md`**：写手写作工艺强化（开头钩子/去AI腔口语化/阅读节奏/金句记忆点），读者代表按此评分。
- **本 skill 的 `references/brand-config.md`**：禁用 AI 腔短语 blocklist，`validate_content_quality.py` 运行时解析（品牌配置与内容质量校验脚本已随资产重分配迁入本 skill）。

`<py>` = 插件解析的 Python（`AINews_PYTHON` → `config.environment.conda_python` → `python`）；`<scripts>` = 本 skill 的 `scripts/`（validate_content_quality.py 已随资产重分配迁入）。

## 关联 Skills

- **article-to-solo-podcast**：本 skill 的"评分+修正循环"机制参照它的 Phase 3（market_ready + hard_block + scorecard）。
- **ai-news-digest**：编排器，只读复用本 skill 的 `validate_content_quality.py` / `brand-config.md`，并通过 `backup_file.py`（迁入 ai-news-digest）覆盖前备份；编排器在 transcript 模式下委派本 skill 产出文章。
- **browser-publisher**：审查通过后，用户手动调它上传公众号草稿。

## 按需加载

| 文件 | 用途 | 加载时机 |
|------|------|---------|
| `agents/_shared.md` | 路径常量/返回格式/反虚构/红线/错误码 | 所有 agent 先读 |
| `agents/researcher.md` | 联网取材 agent 合约 | Phase 0 |
| `agents/article-writer.md` | 写作 agent 合约（DRAFT/FIX，按类型，叠加强化写作工艺） | Phase 1/3 |
| `agents/content-editor.md` | **内容主编**审查 agent 合约（5 维度 + 红线，按类型评） | Phase 2 |
| `agents/reader.md` | **读者代表**审查 agent 合约（3 维度阅读体验） | Phase 2 |
| `references/type-profiles.md` | **6 类文章 profile（核心）** | Phase 0/1/2 全程 |
| `references/phase0-research.md` | 取材流程详解（stance_research 模式） | Phase 0 |
| `references/transcript-mode.md` | transcript 模式流程（researcher 短路 / writer 口语转书面 / 两家主编锚点改转录） | Phase 0-2（仅 `source_mode: transcript`） |
| `references/phase1-writing.md` | 通用写作工艺底线（跨类型） | Phase 1 |
| `references/writing-craft.md` | **写作工艺强化**（开头钩子/去AI腔/阅读节奏/金句记忆点） | Phase 1（writer）/ Phase 2（reader 评分） |
| `references/phase2-editor-review.md` | 双主编并行审查门禁 + 两类 scorecard schema | Phase 2 |
| `references/editor-rubric.md` | 内容主编 5 维度评分细则（按类型锚点） | Phase 2 |
| `references/redlines.md` | 6 类分寸红线（分级：通用/立场类） | Phase 2/3 |
| `references/article-conventions.md` | 归档目录约定 | 初始化/Phase 4 |
