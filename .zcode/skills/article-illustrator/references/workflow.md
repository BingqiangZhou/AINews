# Workflow

## Step 1: Pre-check

### 1.1 确定 Input 类型

| 输入 | 输出目录 | 下一步 |
|------|---------|--------|
| 文件路径 | `{article-dir}/imgs/` | 继续 |
| 粘贴内容 | `illustrations/{topic-slug}/` | 保存源文件后继续 |

### 1.2 加载偏好（config.json）

读取 skill 目录下 `config.json` 的 `illustration` 段（`image_backend`、`fallback_to_agnes`）。这两个字段控制后端选择与回退行为。

> **注意**：preset / density / palette / output_dir **不在 config 中**——它们是 runtime 决策：preset 和 density 由 Step 2 内容分析后推荐（见 [style-presets.md](style-presets.md) 的 Content Type→Preset 表、[density-guide.md](density-guide.md) 的长度→密度表）；palette 由 preset 带出或用户覆盖；output_dir 固定为 `{article-dir}/imgs/`（见 Step 1.1）。

| 结果 | 操作 |
|------|------|
| 找到且完整 | 读取、显示摘要 |
| 缺字段 | 用默认值补全（`image_backend=gaoding`, `fallback_to_agnes=false`）并引导首次配置 |

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

## Step 3: 确认 Settings

设置确认表（预设/密度/色板）见 SKILL.md「执行步骤 → 3. 确认 Settings」。一次 `AskUserQuestion` 最多 3 问，用户说“直接生成”时跳过。

---

## Step 4: 生成大纲

outline.md 格式（YAML frontmatter + 每 illustration 一节）。分段驱动模式下，每个 Illustration 条目含 Segment（归属段）/ Heading / Title Text / Labels 字段。完整格式见 SKILL.md「执行步骤 → 4. 生成大纲」。

**Segment 字段的作用**：它是 Step 5.1b `build_segments --from-outline` 建立 segment→filename 映射的依据。必须在 outline 里正确填写，否则 segments.json 的 illustration 字段会错配。

---

## Step 5: 生成图片

### 5.1 构建 Prompt 文件

⛔ **阻塞步骤**：必须先为每张插图保存 prompt 文件，再调用生成。

每张插图的 prompt 文件：`{output_dir}/prompts/NN-{type}-{slug}.md`

格式：
```yaml
---
illustration_id: 01
type: infographic
style: sketch-notes
palette: macaron
aspect: "16:9"
title_text: "三个被低估的副业"
labels: ["写作变现", "视频剪辑", "AI 配音"]
---

[Type-specific prompt content]
```

⛔ **title_text/labels 硬约束**：infographic/comparison/flowchart/framework/timeline 类型**必须**含 title_text 和 labels（值来自该段文章真实中文词，禁占位符/抽象词）。scene 类型可省。这两个字段会被 `build_segments --prompts-dir` 提取到 segments.json 的 illustration_meta，供下游播客 conductor 对齐图内容、供覆盖校验脚本检查播客是否讲全了图上的标签。详见 [prompt-construction.md](prompt-construction.md)。

Prompt 构建规范见 [prompt-construction.md](prompt-construction.md)。

**维度传递规则**：调用 article-cover-image-generator 时，dimensions 的各维度按以下来源解析：

| 维度 | 来源 | 说明 |
|---|---|---|
| `rendering` + 默认 `palette` | [style-rendering-mapping.md](style-rendering-mapping.md) 主表 | 按当前插图 `style` 查（如 `ink-notes → rendering=chalk, palette=mono`） |
| `palette`（最终） | outline 指定优先，否则用上表的默认值 | 若 outline 指定 article palette（macaron/warm/mono-ink/neon），按 [style-rendering-mapping.md](style-rendering-mapping.md#色板兼容article-illustrator--article-cover-image-generator) 转成 cover palette |
| `text` + `font` | `../../article-cover-image-generator/references/visual-preset-mapping.md` 的「Illustration Profile Text/Font Override」 | 按当前 illustration_type 查（如 `framework → text=text-rich, font=handwritten`） |
| `type` | 手动设 `conceptual`（信息图类）或 `scene`（场景类） | 其余交由 cover auto-selection |
| `mood` | 默认 `balanced` 或交由 cover auto-selection | — |

例如 outline 里某张图 `type: framework, style: ink-notes, palette: mono-ink`：

```json
{
  "dimensions": {
    "type": "conceptual",
    "palette": "mono",
    "rendering": "chalk",
    "text": "text-rich",
    "mood": "balanced",
    "font": "handwritten"
  }
}
```

**text 和 font 不能留空或使用默认值（none / clean）**，否则 prompt 模板中的文字描述不会渲染到图片中。

### 5.1b 产出 segments.json（分段驱动模式必须）

prompt 文件落盘后、生图前，立即跑 `build_segments` 产出 segments.json。这让下游播客 conductor 在生图完成前就能读到分段定义和 illustration_meta——这是消除 audio-to-social 隐藏竞态的关键。

**分段驱动模式**（`article_has_sections: true`）：走路径 A（`--from-outline`），不依赖文章插图引用：
```bash
<py> <scripts>/build_segments.py \
  --article "{output_dir}/../公众号_文章.md" \
  --output "{output_dir}/segments.json" \
  --from-outline "{output_dir}/outline.md" \
  --prompts-dir "{output_dir}/prompts"
```

**全局模式**（`article_has_sections: false`）：跳过此步，segments.json 在 Step 7 用扫描模式产出。

**prompt_only 模式**：此步**也执行**（在返回 prompt_only JSON 之前）。返回的 JSON 含 `segments_file` 字段。

### 5.2 选择生成路径

- **Gaoding AI**（默认）：委托 `article-cover-image-generator` skill，读取 [gaoding-image-generation.md](../../image-generator/references/gaoding-image-generation.md)，通过 Chrome DevTools MCP 自动化生图
- **Agnes 回退**：Gaoding 任何步骤失败时自动回退

### 5.3 生成流程（每张图）

1. 导航到 Gaoding AI 生图页面
2. 输入中文 prompt（开头含尺寸描述"文章插图，尺寸1920x1080像素，16:9宽幅横版比例"，后续全中文描述视觉内容）
3. JS dispatchEvent 点击生成（只点一次）
4. `list_pages` 轮询等待编辑器 tab 自动打开
5. `wait_for` "已成功生成"
6. 导出 → 确认 PNG → 取消社区发布 → 下载
7. 如需要，PIL 裁剪到目标尺寸
8. 验证文件 > 5KB

---

## Step 6: 插入与报告

在文章 Markdown 中，每个插图位置后插入 `![description](imgs/NN-{type}-{slug}.png)`。

**一段多图**：若某段配了多张图，按该段 Step 2c 的 position_hint 顺序在对应位置插入多个 `![]()` 引用。build_segments 的路径 B 扫描时会按行号顺序收集该段范围内的所有引用到 `illustrations` 数组。

图片引用插入与输出摘要见 SKILL.md「执行步骤 → 6. 插入与报告」。
