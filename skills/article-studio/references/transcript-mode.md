# Transcript 模式（`source_mode: transcript`）

> 当 `source_mode == "transcript"` 时加载本文件。researcher / article-writer / content-editor（内容主编）/ reader（读者代表）在 transcript 模式下都按本文件覆盖各自默认（联网取材）流程。
>
> **动机**：被编排器（如 `ai-news-digest`）调用时，输入不是"主题+立场"，而是一段**口语转录文本**（如录音 Whisper 转录）。转录是唯一权威源——零联网、零外部事实，与编排器"内容只从源转录派生"的原则一致。

> **news 清单分支**（`source_mode: transcript` + `article_type: news` + `config.news_digest_format.enabled`）：输入不是口语转录，而是编排器（如 `ai-news-digest`）产出的**结构化资讯素材**（按主题 `##` 分组、每条带信源+日期的 bullet 列表）。此时 writer **不走口语转书面改写**，改为**轻包装清单排版**——直接把素材条目排成可扫读的资讯清单。详见下文「news 清单分支」段。

## 与 stance_research 模式的核心区别

| 维度 | `stance_research`（默认） | `transcript`（本文件） |
|------|---------------------------|------------------------|
| 输入 | `topic` + `stance` + `article_type` | `source_file`（转录文本）+ `article_type`（+可选 `topic`/`title_hint`） |
| 取材 | WebSearch + webReader 联网检索 | **短路跳过联网**，转录文本直接落 `_research/事实素材与来源.md` |
| 事实真源 | 联网检索结果（每条带信源 URL） | **转录文本**（无外部 URL） |
| 主题/标题 | 用户给 `topic` | writer 从转录**派生**（除非编排器传 `title_hint`） |
| 反杜撰锚点 | 事实须可在检索结果中回溯 | 事实须可在**转录文本**中回溯 |
| `require_source_url` | true（每条 bullet 带 URL） | false（转录无外部 URL，信源标"源转录"） |
| 红线 6（AI 声明+时效） | 文末列参考来源 URL | 文末声明"本文由录音转录改写，AI 辅助生成"（无 URL，转录为内部源） |

## 输入字段（transcript 模式）

| 字段 | 必需 | 说明 |
|------|------|------|
| `source_mode` | ✓ | `"transcript"` |
| `source_file` | ✓ | 转录文本路径（编排器转录阶段产出的 `temp/转录文本.txt` 或等价文件） |
| `article_type` | ✓ | 6 类枚举；编排器传或默认 `opinion` |
| `output_dir` | ✓ | 项目目录 `articles/{YYYY-MM-DD}_{标题}/` |
| `topic` | 可选 | 编排器可能已从转录提取了主题；不传则 writer 派生 |
| `title_hint` | 可选 | 编排器可能建议的标题；不传则 writer 派生 |

> **标题/目录名**：若编排器传了 `topic`/`title_hint`，主 agent 据此定目录名；否则主 agent 先让 researcher 读转录给出一句话主题，再据此定目录名（仍走 `AskUserQuestion` 确认，或被编排时用结构化输入）。

## researcher 流程（transcript 模式 → 短路）

`agents/researcher.md` 在 transcript 模式下**跳过**步骤 1-4（拆 query / WebSearch / webReader / 多源交叉），改为：

1. **读 `source_file`**（完整转录文本）。
2. **把转录文本整段落盘**为 `_research/事实素材与来源.md`，格式：
   ```markdown
   # 事实素材与来源（源转录，{YYYY-MM-DD}）

   > 本文是 {article_type 中文名} 类公众号文章。以下事实底座来自一段录音的口语转录文本（源转录），非联网检索。
   > 写作时只引用下列内容，不杜撰转录外的信息，不引入外部网络事实。

   ## 转录原文（权威源）

   {转录文本逐段保留——可做最小清理：去掉 Whisper 的时间戳行/重复段标，但不改写语义、不补全模糊处}

   ## 写作锚点（researcher 从转录提炼，非外部补充）

   ### 核心观点（researcher 摘要，每个都须能在转录原文找到）
   - {观点1，标注大致出处段}
   - {观点2}

   ### 口语特征（保留个人声音用）
   - {有个人特色的真实表达，2-4 个}
   - {原文的不确定性/认知转折，如有}
   ```
3. **反杜撰**：`## 写作锚点` 区只**提炼**转录里已有的观点，**绝不补充**转录外的数据/工具名/结果/经历。
4. `gap_blocked` 在 transcript 模式下**恒为 false**（转录就是全部素材，不存在"检索未果"的缺口——转录没说的就是不能写的）。
5. 返回值 `source_count = 1`（单一源=转录）、`gaps = []`、`gap_blocked = false`。

> researcher 不得在 transcript 模式下调用 `WebSearch` / `webReader`——转录是唯一权威源。

## article-writer 流程（transcript 模式 → 口语转书面）

> **news 清单分支优先判断**：若 `article_type == "news"` 且 `config.news_digest_format.enabled == true`，走下文「news 清单分支」，**不**走本段的口语转书面改写。其余 `article_type`（opinion/howto/story/profile/review）继续走本段。

### news 清单分支（`article_type: news` + `news_digest_format.enabled`）

输入的 `RESEARCH_FILE`（`_research/事实素材与来源.md`）已是结构化资讯列表（编排器 `build_research_md.py` 产出）：按主题 `##` 分组，每条 bullet 含 `ai_summary`（一句话事实）+ 信源名 + 信源 URL + 事件日期 + 采集日期。writer 的任务不是改写，而是**轻包装清单排版**。

#### 必须做

- **开头**（≤ `intro_max_chars`，默认 80 字）：1-2 句，数据冲击式点明今日条数/重点/时间范围。如"今日精选 8 条 AI 要闻，涵盖模型发布、融资、政策三大方向。"**不写散文钩子，不写"随着 AI 的发展"。**
- **主体**：保留素材的 `##` 主题分组结构；每个主题组下，把 bullet 资讯条目提升为 `### 条目标题`（用原标题或事实提炼），条目内：
  - 一句话核心事实（取自 `ai_summary`，可微调措辞但**不改语义**）
  - `[信源名](url) · 日期`（信源 URL **照搬**，日期取事件日期，缺失标"具体日期未公布"）
  - 可选 `点评：`（一句话主观判断，红线 1 要求明示是观点；无把握可省略）
- **结尾**（≤ `outro_max_chars`，默认 120 字）：1-2 句追更 CTA（"关注追更明日日报"）。**不做趋势归纳长段。**
- **插图占位符**：在适合配图的主题组后插入 `<!-- illustration -->` 占位符（`config.transcript_mode.illustration_placeholders` 范围，默认 2-4 个），占位符独占一行。
- **派生标题**：数字+时间型（"2026-07-16 AI 日报：今日 N 条要闻"），15-30 字，前 22 字含核心信息。
- **首行 `# 标题`**；文末 AI 生成声明用 `>` 引用块（如"> 本文资讯由 RSS 采集，AI 辅助整理排版。"）；同步写 `公众号_摘要.txt`（≤120 字）。

#### 不得做

- **不得添加素材外的事实**（零外部事实，反杜撰红线）。
- **不得改写/截断信源 URL**（照搬）。
- **不得编造事件日期**（缺失标"具体日期未公布"）。
- **不得把素材的模糊表述改为精确表述**。
- **不得写连接性散文/过渡长段/趋势归纳**（清单文体要短、可扫读）。
- **不得添加 AI 腔**（"综上所述""值得一提的是"等，blocklist 见 brand-config.md）。
- **不得用纯 bullet 无 `##` 主题组**（下游 build_segments/conductor 依赖 `##` 切分）。

#### 格式

- 字数：`body_min_chars`-`body_max_chars`（清单模式 body_min 降到 400）；小节数（`##` 主题组）2-8 个。
- 单段 ≤120 字（bullet 本就短句）。
- 层级：`# 标题` → `## 主题组` → `### 条目` → bullet。

> FIX 模式同：按主编 `fix_directives` 定向改（如补信源、修日期、删编造点评），但事实保真锚点仍是素材文件——主编要求补的事实若素材没有，必须用模糊措辞或删去，不可编造。

---

### 口语转书面改写（非 news，或 news 清单模式关闭时）

`agents/article-writer.md` DRAFT 模式在 transcript 模式下（非 news 清单分支），`RESEARCH_FILE` 的 `## 转录原文` 区是事实真源，写作本质是**口语转书面化改写**（沿用编排器既有的 transcript-optimizer 写作工艺）：

### 必须做
- **去口语化**：去除口头禅和语气词（"嗯""就是说""然后呢""对吧""你知道吗"），修正语病、啰嗦重复和逻辑跳跃。
- **重组结构**：重新组织段落，加合理过渡，加 `##` 小标题（2-4 个，好奇驱动，非总结型）。
- **保留核心观点**：转录里所有核心观点/关键事实/个人见解必须保留，不得丢失——即使表达不完善也保留核心。
- **保留真实声音**：从转录提取 2-4 个有个人特色的真实表达自然嵌入，不制造转录没有的口头禅。
- **保留不确定性**：转录里"可能""不确定""说不准"等表述必须保留，不改为肯定句。
- **保留认知转折**：转录里"但后来我发现""不对，也不全是"等认知变化保留进文章。
- **插图占位符**：在适合配图的段落间插入 `<!-- illustration -->` 占位符（`config.transcript_mode.illustration_placeholders` 范围，默认 2-4 个），占位符独占一行。
- **派生标题**：15-30 字，前 22 字含核心钩子，只用转录里存在的具体信息。优先"具体+反差/痛点+方案/数字+疑问/反常识/经历+悬念"；禁"关于...""几点思考""我的心得"。若编排器传了 `title_hint`，参考它但仍须落在转录事实内。

### 不得做
- **不得添加转录外的事实/数据/观点**（零外部事实，反杜撰红线）。
- **不得删除核心观点**。
- **不得把转录的模糊表述改为精确表述**（原文模糊就保持模糊）。
- **不得添加 AI 腔**（"综上所述""值得一提的是"等，blocklist 见 brand-config.md）。
- **不写规避检测/绕过平台**的说辞。

### 格式（沿用 type-profile + 通用工艺，但默认随笔调性）
- 第一人称随笔，主线贯穿；段落长短交替，不连续三段超 180 字。
- 默认 900-2000 字（或 `type_content_overrides` 覆盖）；2-4 个 `##` 小节。
- 每 250-350 字有一个新兴趣点（具体数字/反常识/自我推翻/转折/可视化场景）。
- 至少 1 句值得截图分享的句子，自然嵌入不标注"金句"。
- 首行 `# 标题`；不写 `>` 引用块；同步写 `公众号_摘要.txt`（≤120 字，不用"本文探讨了"）。

> FIX 模式同：按主编 `fix_directives` 定向改，但事实保真锚点仍是转录——主编要求补的事实若转录没有，必须用模糊措辞或删去，不可编造。

## content-editor 流程（transcript 模式 → 锚点改转录）

> **news 清单分支**（`article_type: news` + `news_digest_format.enabled`）：审查锚点改为对照 `RESEARCH_FILE` 的资讯条目列表（非口语转录）：
> - 每条资讯是否有信源链接+日期？信源 URL 是否照搬未改写？
> - 事实是否照搬素材（`ai_summary` 语义未变）？有无编造素材外事实/夸大模糊表述？
> - 点评部分是否明示为观点（红线 1，必须用"点评："前缀或明确的主观措辞）？
> - 时效标注是否完整（红线 6，news 最重）？
> - `voice` 维度按"极简播报"评（事实零感情色彩、点评克制），**不要求散文连贯性/金句/记忆点**——清单文体不该按散文标准扣分。
> - `engagement`/`reading_experience` 按"扫读效率 + 信息密度"评，不按"钩子/金句"评（清单的 engagement 来自信息密度而非叙事钩子）。
> - 红线 6 信源标注：清单模式每条已带信源链接，AI 声明仍**必须**有（文末 `>` 引用块）。

`agents/content-editor.md`（内容主编）审查时（非 news 清单分支），步骤 2（对照事实真源）改为对照 `RESEARCH_FILE` 的 `## 转录原文` 区：

- 文中每个事实/数字/工具名/结果/经历，须能在**转录原文**找到对应。
- 超出转录的"补全"细节 = `FIDELITY_VIOLATION`（编造）。
- 把转录的模糊表述写成了精确表述 = `FIDELITY_VIOLATION`（夸大）。
- **不引入转录之外的外部知识判断对错**——只对照转录，不自己 fact-check 外部世界。
- 红线 6（AI 声明+时效）的"信源标注"降级为：文末声明"本文由录音转录改写，AI 辅助生成"即可（转录为内部源，无 URL）；但 AI 生成声明仍**必须**有。

## reader 流程（transcript 模式 → 不变，但 news 清单分支例外）

`agents/reader.md`（读者代表）在 transcript 模式下**职责不变**——仍是手机端读者视角审阅读体验/获得感/读得下去。读者代表不读 `RESEARCH_FILE`、不查事实，所以转录模式对它无特殊覆盖。口语转书面改写稿的阅读体验标准与 stance_research 模式一致（对照 [writing-craft.md](writing-craft.md)）。

> **news 清单分支例外**（`article_type: news` + `news_digest_format.enabled`）：清单不是"口语转书面改写稿"，是结构化资讯列表。reader.md 已为此新增清单分支（见 `agents/reader.md` 步骤 2/4 的 news 清单分支）：engagement 改按"扫读效率+信息密度"评（不按钩子/金句），且**清单模式下 engagement 不触发 hard_block**（清单的吸引力来自信息密度而非叙事钩子）。reading_experience 仍按扫读排版评并保留 hard_block。

## 状态机

transcript 模式下 phase 仍走 `initialized → researched → written → editor_passed`：
- `researched`：researcher 落盘转录派生的 `_research` 后立即置（无需联网）。
- 其余不变。

`state.json` 新增字段 `source_mode`（`"stance_research"` | `"transcript"`），transcript 模式下额外记 `source_file`（转录路径）。
