# Workflow（illustrate 模式深入细节）

SKILL.md「执行步骤 → illustrate 模式」已给出 7 步框架。本文件展开 SKILL.md 没有覆盖的执行细节——三层分析的完整字段、Type 分配策略、插图位置规则、prompt YAML 样例。

Step 3（确认 Settings）和 Step 6（插入与报告）见 SKILL.md，本文件不重复。

---

## Step 1: Pre-check

### 1.1 确定 Input 类型

| 输入 | 输出目录 | 下一步 |
|------|---------|--------|
| 文件路径 | `{article-dir}/imgs/` | 继续 |
| 粘贴内容 | `illustrations/{topic-slug}/` | 保存源文件后继续 |

### 1.2 加载偏好（config.json）

读取 skill 目录下 `config.json` 的 `backend` 段（`provider` / `fallback_to_agnes`）。这两个字段控制后端选择与回退行为。`cover` 段和 `preferences` 段对 illustrate 模式不生效（仅 cover 模式用）。

> **注意**：preset / density / palette / output_dir **不在 config 中**——它们是 runtime 决策：preset 和 density 由 Step 2 内容分析后推荐（见 [style-presets.md](style-presets.md) 的 Content Type→Preset 表、[density-guide.md](density-guide.md) 的长度→密度表）；palette 由 preset 带出或用户覆盖；output_dir 固定为 `{article-dir}/imgs/`（见 Step 1.1）。density 默认值 `balanced` 也不在 config 中（runtime 默认）。

| 结果 | 操作 |
|------|------|
| 找到且完整 | 读取、显示摘要 |
| 缺字段 | 用默认值补全（`provider=gaoding`, `fallback_to_agnes=false`）并引导首次配置 |

---

## Step 2: 分析文章（三层：全局 → 切段 → 分段）

分析分三步，目的是让插图决策对齐文章的 `##` 章节结构。每段产出的 type/title_text/labels 会通过 segments.json 传递给下游播客 conductor，让播客要点和图内容对齐（语义对应）。

**关键规则**：不要把隐喻/比喻画成字面图像。例如"思维的弹簧"不画弹簧，而是可视化"弹性思维"的概念。

### 2a. 全局轻量分析（1 次调用，读全文）

| 分析项 | 输出 |
|--------|------|
| 内容类型 | technical / tutorial / methodology / narrative |
| 插图目的 | information / visualization / imagination |
| 推荐预设 | 基于 content type 推荐（查 [style-presets.md](style-presets.md) 的 Content Type→Preset 表） |
| 推荐密度 | 基于 content type 和文章长度推荐（查 [density-guide.md](density-guide.md)） |
| 全文 thesis | 文章主旨/标题的核心主张（给片头图用） |
| 全文 CTA | 文末的号召/总结主题（给片尾图用） |

### 2b. 切段（确定性，无 LLM）

扫描文章的 `##` 标题，按章节切段，得到 M 个 body segment（heading 已知，illustration 待定）。复用 `build_segments.py` 的 heading 扫描逻辑。

- **M ≥ 2** → 走分段驱动（Step 2c 逐段分析）。每张图、每段内容都有明确的归属段。
- **M = 0**（无 `##` 章节）→ **退回全局模式**：跳过 2c，Step 2a 的全局分析直接决定所有插图（与旧逻辑一致）。outline 的 `article_has_sections: false`，Step 5.1b 跳过，Step 7 走扫描模式。

### 2c. 分段分析（1 次批处理调用，喂所有段 + 全局 Style/Palette/预算）

逐段决定该段画什么。**批处理而非逐段独立调用**——保留全局视野，能识别跨段对比（段 A 旧方案 + 段 B 新方案 → 一张 comparison）和相邻段 Type 去重。

每段输入：该段 heading + 该段正文。每段输出：

| 字段 | 说明 |
|------|------|
| `type` | 该段适合的插图类型（infographic/flowchart/comparison/framework/timeline/scene） |
| `visual_content` | 图中的核心视觉元素 |
| `title_text` | 图内主标题（**文章真实中文词**，scene 类型可省）。来自该段真实出现的词，不是占位符 |
| `labels` | 图内标签数组（**文章真实中文词**，scene 类型可省）。来自该段真实出现的术语/数字/关键词 |
| `position_hint` | 插图在该段的位置（段首/段中/段尾，给 Step 6 插入用） |

**Type 分配策略**（基于段落内容特征）：
- 概念解释段 → infographic
- 步骤流程段 → flowchart
- 对比分析段 → comparison
- 框架模型段 → framework
- 历史演进段 → timeline
- 感悟叙事段 → scene

**跨段图**：若检测到跨两段的对比关系（段 A 讲旧方案 + 段 B 讲新方案），产出一个 comparison 候选，归属到靠后的段。标注 `cross_segment: true`。

**预算截断**：所有段候选点按优先级（核心概念 > 过程流程 > 对比 > 框架 > 数据 > 总结）排序，按密度预算 N 截断。被截断的段不配图。

**片头片尾图**：基于 Step 2a 的 thesis/CTA 额外规划两张图（opening/ending），不归属任何 body 段。

### 2d. 确定插图位置（分段驱动模式自动确定）

分段驱动模式下，每段的位置由 `position_hint`（段首/段中/段尾）决定，不需要额外判断「适合/不适合」。全局模式下仍用以下规则：

**适合插图的位置**：
- 核心论点阐述后
- 抽象概念解释处
- 数据/对比展示处
- 过程/流程描述处
- 长段落的自然断点

**不适合插图的位置**：
- 纯情感描写
- 过渡段
- 引用/出处说明
- 文章开头/结尾（太短的段落）

---

## Step 4: 生成大纲

outline.md 格式（YAML frontmatter + 每 illustration 一节）。分段驱动模式下，每个 Illustration 条目含 Segment（归属段）/ Heading / Title Text / Labels 字段。

frontmatter（三维法，文章级统一 style）：

```yaml
---
preset: knowledge
type: infographic
style: sketch-notes
palette: warm              # 全局锁（规则 #14），记录用
density: balanced
image_count: 4
segment_count: 6           # ## 章节数（分段驱动模式）
article_has_sections: true  # 是否走了分段驱动（false = 全局模式）
---
```

**Segment 字段的作用**：它是 Step 5.1b `build_segments --from-outline` 建立 segment→filename 映射的依据。必须在 outline 里正确填写，否则 segments.json 的 illustration 字段会错配。

> **三维法**：frontmatter 含 `style`（文章级单值），不再含 `rendering`（派生自 style）。Palette 字段记录为 `warm`（全局锁）。

---

## Step 5: 生成图片

### 5.1 构建 Prompt 文件

⛔ **阻塞步骤**：必须先为每张插图保存 prompt 文件，再调用生成。

每张插图的 prompt 文件：`{output_dir}/prompts/NN-{type}-{slug}.md`

格式（三维法）：
```yaml
---
illustration_id: 01
type: infographic
style: sketch-notes
palette: warm
aspect: "16:9"
title_text: "三个被低估的副业"
labels: ["写作变现", "视频剪辑", "AI 配音"]
---

[Type-specific prompt content]
```

⛔ **title_text/labels 硬约束**：infographic/comparison/flowchart/framework/timeline 类型**必须**含 title_text 和 labels（值来自该段文章真实中文词，禁占位符/抽象词）。scene 类型可省。这两个字段会被 `build_segments --prompts-dir` 提取到 segments.json 的 illustration_meta，供下游播客 conductor 对齐图内容、供覆盖校验脚本检查播客是否讲全了图上的标签。详见 [prompt-construction.md](prompt-construction.md)。

Prompt 构建规范见 [prompt-construction.md](prompt-construction.md)。

**维度传递规则**：illustrate 模式调用 image-generator 时，dimensions 的各维度来源见 [image-studio.md](../agents/image-studio.md) 的「维度传递规则（illustrate → image-generator）」段——三维（type + style + palette=warm）+ 派生维度（rendering 从 style 查 style-rendering-mapping.md；text/font 从 type 查 visual-preset-mapping.md；mood 默认 balanced）。

> **派生维度不能留空**：rendering/text/font 必须按上述查表派生后传入 image-generator，否则 prompt 模板中的文字描述不会渲染到图片中（text=none 时）或 rendering 缺失导致风格漂移。

> 历史 outline 文件（含 `rendering`+`palette` 字段而无 `style` 的旧版）仍可被兼容读取——agent 遇到旧 outline 时按反向映射（如 hand-drawn + macaron → sketch-notes）还原 style 即可。

### 5.1b 产出 segments.json（分段驱动模式必须）

prompt 文件落盘后、生图前，立即跑 `build_segments` 产出 segments.json。这让下游播客 conductor 在生图完成前就能读到分段定义和 illustration_meta——这是消除 ai-news-digest 隐藏竞态的关键。

- **分段驱动模式**（`article_has_sections: true`）：走路径 A（`--from-outline`），不依赖文章插图引用。完整 bash 命令见 SKILL.md Step 5.1b（权威源）。
- **全局模式**（`article_has_sections: false`）：跳过此步，segments.json 在 Step 7 用扫描模式产出。
- **prompt_only 模式**：此步**也执行**（在返回 prompt_only JSON 之前）。返回的 JSON 含 `segments_file` 字段。

### 5.2 生图（委托 image-generator）

本 skill 不直接操作浏览器或 API。Step 5.2 调用 `image-generator` skill 批量接口（JSON 格式见 [image-studio.md](../agents/image-studio.md) 的 batch delta），传入 prompt_file + target_size + output_path + provider。image-generator 内部完成后端选择、浏览器自动化（Gaoding/Jimeng）、API 调用（Agnes）、PIL 裁剪、>5KB 验证、失败回退（受 `backend.fallback_to_agnes` 控制）。

Gaoding/Jimeng 的浏览器自动化细节（导航/输入/JS dispatch/轮询/导出/取消社区发布）见 [image-generator 的 gaoding-image-generation.md](../../image-generator/references/gaoding-image-generation.md)，本 skill 不展开。

### 5.3 验证

每张图返回后，本 skill 只需确认：文件存在 + 尺寸与 target_size 接近。详细校验规则见 [image-studio.md](../agents/image-studio.md) 的「质量检查」表。
