# Phase 0 — 联网取材流程

> 主 agent 加载本文件指导 researcher agent，或 researcher agent 自行加载。

## 目标

给一个主题（`topic`）+ 作者口述立场/素材（`stance`）+ 文章类型（`article_type`），**联网检索**建立结构化事实底座 `_research/事实素材与来源.md`，作为 Phase 1 写作的唯一事实真源。

## 与其他 skill 取材的区别

| skill | 取材方式 | 信源 |
|-------|---------|------|
| **本 skill** | WebSearch + webReader 任意主题检索（按 `article_type` 调偏好） | 全网（官方文档/权威媒体/社区） |
| ~~daily-digest~~（已归档至 `_backup/skills/daily-digest`，由 `ai-news-digest` 接替） | poll_feeds.py 拉 RSS | 配置的周刊 RSS 信源表 |

本 skill 用 **WebSearch + webReader**（任意主题 ad-hoc 检索），不是 RSS 闭环。检索偏好按 `article_type` 的 `research_focus` 调整（见 [type-profiles.md](type-profiles.md)）。

## 取材流程

### 0. story 纯虚构降级（仅 `article_type == "story"` 且 `stance` 声明纯虚构）

若本文为纯虚构创作，`_research` 可仅含 `## 写作立场/素材` 一节（AI 声明 + 主题/人物/基调/大纲），跳过外部事实检索，`require_source_url` 降级为 warning。故事里若引用真实背景元素（地名/历史事件），那些仍需带 URL。详见 `agents/researcher.md` §0。

### 1. 收集输入（主 agent 职责）

通过 `AskUserQuestion` 收集：
- `topic`：主题（一句话，如"阿里禁了 Claude Code，我迁到 ZCode"）
- `article_type`：文章类型（6 选 1，选不准用 `default_article_type`；详见 [type-profiles.md](type-profiles.md) 的类型选择指引）
- `stance`：作者口述立场/素材/经历（几句话；按类型含义不同——opinion 给立场，story 给经历，howto 给要教的点，review 给体验过的产品，news 给时间范围/视角，profile 给受访人物与议题）

主 agent 创建项目目录 `articles/{YYYY-MM-DD}_{标题}/`，初始化 `state.json`（含 `article_type`），委托 researcher。

### 2. 拆检索关键词（researcher）

从 `topic` + `stance` 提取：
- 实体（公司、产品、人名）
- 事件（禁用、迁移、发布、泄露）
- 限定词（版本号、日期、地区）

组合 5-10 个 query，中英文都试。例：
- topic="阿里禁了 Claude Code" → `阿里 禁用 Claude Code` / `Alibaba bans Claude Code` / `Claude Code 中国 封禁`
- stance 含"缓存失效" → `Claude Code cache miss third-party API` / `Claude Code sentinel attribution header`

### 3. WebSearch 找候选

用 `WebSearch` 逐个 query 搜索。每个 query 取 top 3-5 候选 URL。优先级排序：

1. **官方一手**：Anthropic 官方文档/公告、ZCode 官网、GitHub Issue/PR/Release
2. **权威媒体**：第一财经、观察者网、安全客、虎嗅、新浪财经、财联社
3. **社区深度**：知乎专栏、技术博客、Reddit/HackerNews 讨论

避免：内容农场、不明 aggregators、SEO 垃圾。

### 4. webReader 读全文

对高优候选用 `mcp__web_reader__webReader` 抓全文（`return_format=markdown`）。提取：
- **具体事实**：事件经过、数字、版本号、日期、引文（一字不改）
- **信源 URL**：原始链接（不要中转站/缓存）
- **检索日期**：今天

**多源交叉**：关键事实（尤其争议性的）至少 `config.research.max_sources_per_claim`（默认 3）个信源。单一信源的论断标注 `(单一来源)`。

### 5. 落盘 `_research/事实素材与来源.md`

格式见下方模板。**分节原则：按主题 `##` 分，不按信源分**。每条事实独立 bullet，末尾贴 URL + 检索日期。

### 6. 缺口处理

检索不到的事实：
- 标注 `{检索未果}`，**不编造**
- 写入返回值的 `gaps` 清单
- 如果是文章核心论据（缺了写不下去）→ `gap_blocked: true`，主 agent 提示用户补检索或调整主题

## `_research/事实素材与来源.md` 模板

```markdown
# 事实素材与来源（联网检索于 {YYYY-MM-DD}）

> 本文是 {article_type 中文名} 类公众号文章（非 wiki 引用型中立分析）。以下是从公开报道、官方文档、社区检索到的事实底座，关键数字/事件尽量标注出处。写作时只引用下列事实，不杜撰素材外信息。

## 一、{主题1（如：Anthropic 对中国用户的限制）}

- **{要点1}**：{描述，含数字/版本/日期}
  - {信源名}：{URL}
  - 事件/发布日期：{YYYY-MM-DD，即该事件发生或源文发布的日期；news 类型必填}
  - 检索日期：{YYYY-MM-DD，即你今天检索到的日期}
- **{要点2}**：{描述}
  - {信源名1}：{URL1}
  - {信源名2}：{URL2}（交叉验证）
  - 事件/发布日期：{YYYY-MM-DD}
  - 检索日期：{YYYY-MM-DD}

## 二、{主题2}
- ...

## {N}、{最后一个主题}
- ...

## 写作立场/素材（来自作者口述，非检索事实）

### 作者意图/写作锚点
- {stance 原文}
- 核心锚点（按类型提炼 1-3 个）：
  - opinion/review：核心论点 / 推荐立场
  - howto：要教的方法 / 已知避坑点
  - news：盘点视角 / 时间范围
  - profile：受访人物 + 核心议题
  - story：主题 / 情感基调 / 是否纯虚构（若纯虚构，在此声明）

### 时间线要点（防自相矛盾，按类型需要）
- {事件 A 发生在事件 B 之前/之后，避免写作时倒置}

### 立场分寸提醒（仅 opinion/review 等立场类类型需要）
- 对 {对象1}：{要留余地的原因，如"未经官方坐实，用'据报道'"}
- 对 {对象2}：{要承认的优点/不拉踩}
```

## 反虚构硬约束（researcher 必守）

- 每条 bullet 至少 1 个信源 URL（`config.research.require_source_url`）
- 引文用引号照搬原文，不改写
- 不确定的事实标"据报道/有报道称/据称"
- 严禁把 LLM 内置知识当作检索结果写入
- 信源矛盾时两边都收录，分别标注（写作时由 writer 按立场分寸处理）

## 状态机更新

Phase 0 成功 → `state.json.phase = "researched"`，记 `research_file` 路径、`source_count`、`gaps`。
缺口阻塞 → `state.json.phase = "gap_blocked"`，主 agent 提示补检索。
