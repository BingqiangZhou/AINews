---
name: article-illustrator
version: "2.1.0"
description: 分析文章结构，识别插图位置，用 Type × Style × Palette 三维方法生成一致性配图。支持 Gaoding AI 生图 + Agnes 回退，density 参数控制插图数量。**触发场景**：用户提到"为文章配图""生成插图""文章插图""illustrate article""add images to article"，或者想为 Markdown 文章添加配图时使用。
metadata:
  presets: [hand-drawn-edu, knowledge, narrative, analysis, timeline, tech-explainer, storytelling, opinion-piece]  # 代表性子集，完整 ~30 个见 references/style-presets.md
  density_levels: [minimal, balanced, per-section, rich]
---

# Article Illustrator

分析文章结构，识别插图位置，用 Type × Style × Palette 三维方法生成一致性配图。

## 关联 Skills

- **audio-to-social**：Phase 6 调用本 skill 为公众号文章生成插图
- **baoyu-article-illustrator**：本 skill 的方法论来源（Type × Style × Palette）

## 三维方法论

| 维度 | 控制 | 示例 |
|------|------|------|
| **Type** | 信息结构 | infographic, scene, flowchart, comparison, framework, timeline（6 种） |
| **Style** | 渲染方式 | sketch-notes, vector-illustration, ink-notes, notion, elegant, warm, minimal, blueprint, watercolor, editorial, scientific, chalkboard, fantasy-animation, flat, flat-doodle, intuition-machine, nature, pixel-art, playful, retro, sketch, screen-print, vintage（**23 种**，见 [Style 索引](references/styles.md)） |
| **Palette** | 色彩方案 | macaron, warm, neon, mono-ink（4 种，见 [色板定义](references/palettes.md)） |

自由组合：`--type infographic --style blueprint --palette macaron`，或用 `--preset hand-drawn-edu` 一次设定三维。完整 preset 见 [预设参考](references/style-presets.md)。

> Style 到 article-cover-image-generator 的 (rendering, palette) 映射见 [style-rendering-mapping.md](references/style-rendering-mapping.md)（单一来源）。

## 流程概览

```text
输入文章 Markdown → 分析结构与内容类型
→ 确认 settings（preset/density/style/palette）
→ 生成插图大纲（position, type, visual content, filename）
→ 逐张构建 prompt 并落盘到 prompts/
→ Gaoding AI 生图（Agnes 回退）
→ 插入图片引用到文章 Markdown
→ 压缩 → 报告
```

## 关键规则

1. **Prompt 先落盘**：所有插图 prompt 必须先写入 `prompts/NN-{type}-{slug}.md`，再调用生成。
2. **三维一致**：同一篇文章的所有插图保持 type、style、palette 一致。
3. **密度控制**：通过 `density` 参数控制插图数量，不盲目堆砌。
4. **隐喻不直译**：文章中的隐喻/比喻不直接画成字面图像，而是可视化背后的概念。
5. **覆盖前备份**：写入任何输出文件前，已存在的非空文件先备份。
6. **Gaoding 只点一次**：生图按钮只点击一次，通过 `list_pages` 轮询等待结果。
7. **中文 Prompt**：所有 prompt 使用中文编写，图片内的文字（标题、标签、数据）也使用中文。

## Density 策略

| Level | 数量 | 适用场景 |
|-------|------|---------|
| `minimal` | 1-2 张 | 核心观点处，克制使用 |
| `balanced` | 3-5 张 | 每个主要段落配一张 |
| `per-section` | 每个 ## 标题一张 | 图文并茂 |
| `rich` | 6+ 张 | 教程、深度分析 |

详细策略见 [密度指南](references/density-guide.md)。

## 预设

**默认 preset**：`hand-drawn-edu`（infographic + sketch-notes + macaron）——无强内容信号时的安全选择。

**中文别名 preset**（向后兼容 audio-to-social）：`knowledge` / `narrative` / `analysis` / `timeline`。

完整 preset 列表（~30 个，分 6 类）见 [预设参考](references/style-presets.md)。常用：

| 预设 | Type | Style | Palette | 适用场景 |
|------|------|-------|---------|---------|
| `hand-drawn-edu` | infographic | sketch-notes | macaron | **默认**。教育信息图、概念解说、通用知识 |
| `knowledge`（别名） | infographic | sketch-notes | macaron | 知识分享、教程、方法论 |
| `tech-explainer` | infographic | blueprint | — | API 文档、系统指标、技术深潜 |
| `system-design` | framework | blueprint | — | 架构图、系统设计 |
| `storytelling` | scene | warm | — | 个人随笔、反思、成长故事 |
| `narrative`（别名） | scene | warm | warm | 叙事、感悟、个人经历 |
| `analysis`（别名） | framework | ink-notes | mono-ink | 技术分析、对比评测 |
| `ink-notes-framework` | framework | ink-notes | mono-ink | 系统类比、技术宣言 |
| `opinion-piece` | scene | screen-print | — | 评论、社论、批判文章 |
| `history` | timeline | elegant | — | 历史综述、里程碑 |
| `timeline`（别名） | timeline | elegant | — | 演进历程、发展脉络 |

**Content Type → Preset 推荐**见 [style-presets.md](references/style-presets.md#content-type--preset-推荐表)。

## 执行步骤

### 1. Pre-check

读取 `config.json` 的 `illustration` 段获取偏好设置（preset、density、image_backend 等）。缺字段则引导首次配置。

确认输入：
- 文章文件路径（Markdown）
- 可选：`--preset`、`--density`、`--style`、`--palette` 覆盖默认值

### 2. 分析文章（三层：全局 → 切段 → 分段）

分析分三步进行，目的是让「画什么」「画几张」「什么风格」的决策对齐文章的 `##` 章节结构，使每张图、每段内容都有明确的归属段。这一层产出的信息（每段的 type/title_text/labels）会通过 segments.json 传递给下游播客 conductor，让播客要点和图内容对齐。

**关键规则**：隐喻 → 可视化背后概念，不画字面图像。

#### 2a. 全局轻量分析（1 次调用，读全文）

| 分析项 | 输出 |
|--------|------|
| 内容类型 | technical / tutorial / methodology / narrative |
| 推荐预设 | 基于 content type 推荐（查 [Content Type → Preset 推荐](references/style-presets.md#content-type--preset-推荐表)） |
| 全文 thesis | 文章主旨/标题的核心主张（给片头图用） |
| 全文 CTA | 文末的号召/总结主题（给片尾图用） |
| 密度预算 N | 基于 content type + 文章长度（查 [密度指南](references/density-guide.md)） |

#### 2b. 切段（确定性，无 LLM）

扫描文章的 `##` 标题，按章节切段，得到 M 个 body segment（heading 已知，illustration 待定）。

- **M ≥ 2** → 走分段驱动（Step 2c 逐段分析）。
- **M = 0**（无 `##` 章节）→ **退回全局模式**：跳过 2c，Step 2a 的全局分析直接决定所有插图（与旧逻辑一致），Step 7 走扫描模式。

#### 2c. 分段分析（1 次批处理调用，喂所有段 + 全局 Style/Palette/预算）

逐段决定该段画什么。每段输出：

| 字段 | 说明 |
|------|------|
| `type` | 该段适合的插图类型（infographic/flowchart/comparison/framework/timeline/scene） |
| `visual_content` | 图中的核心视觉元素 |
| `title_text` | 图内主标题（**文章真实中文词**，scene 类型可省） |
| `labels` | 图内标签数组（**文章真实中文词**，scene 类型可省） |
| `position_hint` | 插图在该段的位置（段首/段中/段尾，给 Step 6 插入用） |

**跨段图**：若检测到跨两段的对比关系（段 A 讲旧方案 + 段 B 讲新方案），产出一个 comparison 候选，归属到靠后的段。

**一段多图**：信息密度高的段（如一节内有多个并列要点、或先概念后流程）可产出多张候选图。这些图共享同一个 segment index，outline.md 里多个 Illustration 块的 `**Segment**` 字段填同一个值。build_segments 会收集成 `illustrations` 数组，illustration_meta 的 labels 取并集。

**预算截断**：所有段候选点按优先级排序，按密度预算 N 截断（哪些段画、哪些段跳过、哪些段画多张）。一段多图时注意总图数不超过预算——优先保证覆盖面（每段至少一张），再给高密度段加图。

**片头片尾图（opening/ending）**：基于 Step 2a 的 thesis/CTA 额外规划两张图，**不插入文章**：
- **片头图（opening）**：基于 thesis 的品牌视觉总览，用于播客片头（cold open）和视频开场。文件名 `NN-opening-<slug>.png`。
- **片尾图（ending）**：基于 CTA 的收尾图（如"关注/收藏/转发"引导），用于播客片尾（CTA）和视频结尾。文件名 `NN-ending-<slug>.png`。
- 这两张图落 `imgs/` 但 Step 6 不回写文章。Step 5.1b 的 `build_segments --from-outline` 会自动把它们识别为 opening/ending 段写入 segments.json。

→ 详细步骤见 [工作流参考](references/workflow.md#step-2-分析文章三层全局--切段--分段)

### 3. 确认 Settings

一次 `AskUserQuestion`，最多 3 问。用户说"直接生成"/"跳过确认"时跳过。

| Q | 必选 | 说明 |
|---|------|------|
| Q1: 预设或 Type | 是 | 基于 Step 2 推荐 preset（见 [Content Type → Preset 推荐](references/style-presets.md#content-type--preset-推荐表)）；选项含推荐 preset + 备选 preset + 手动选 type（infographic/scene/flowchart/comparison/framework/timeline）。无强信号时推荐 `hand-drawn-edu` |
| Q2: 密度 | 是 | minimal / balanced / per-section / rich |
| Q3: Style | 选 preset 时跳过；手动选 type 时必填 | 推荐兼容 style + 备选 + Other（见 [Style Gallery](references/styles.md#style-gallery23-个)） |
| Q4: 色板 | 否 | 默认用预设色板，可覆盖为 macaron/warm/neon/mono-ink |

### 4. 生成大纲

保存 `{output_dir}/outline.md`：

```yaml
---
preset: knowledge
type: infographic
style: sketch-notes
palette: macaron
density: balanced
image_count: 4
segment_count: 6            # ## 章节数（分段驱动模式）
article_has_sections: true   # 是否走了分段驱动（false = 全局模式）
---

## Illustration 1
**Segment**: 0              # 归属的 segment index（OPENING/ENDING 表示片头片尾）
**Heading**: 一、核心概念     # 段标题（片头片尾无此项）
**Position**: 段尾
**Type**: infographic
**Purpose**: [为什么需要这张图]
**Visual Content**: [图中的核心视觉元素]
**Title Text**: 核心概念      # 图内主标题（文章真实中文词，scene 类型可省）
**Labels**: [要素A, 要素B]    # 图内标签（文章真实中文词数组，scene 类型可省）
**Filename**: 01-infographic-core-concept.png
```

> **Segment 字段**是分段驱动的关键：`build_segments --from-outline`（Step 5.1b）读它来建立 segment→filename 映射，不依赖文章里的 `![]()` 引用（此时图可能还没插入）。

### 5. 生成图片

**⛔ 阻塞步骤：Prompt 文件必须先生成并保存。**

> **跨 skill 依赖**：本 skill 的插图生成依赖 `article-cover-image-generator` skill，确保该 skill 已安装。

**⛔ 读取 image_backend 偏好**：调用 `article-cover-image-generator` 前，必须读取 `config.json` 的 `illustration.image_backend`，将其作为 `cover_provider` 传递。映射：`image_backend: gaoding` → `cover_provider: gaoding`，`image_backend: jimeng` → `cover_provider: jimeng`，`image_backend: agnes` → `cover_provider: agnes`。未设置时默认 `gaoding`。

1. 为每张插图构建 prompt，保存到 `prompts/NN-{type}-{slug}.md`（含 YAML frontmatter）
2. Prompt 结构遵循 [Prompt 构建规范](references/prompt-construction.md)

**⛔ Step 5.1b：产出 segments.json（分段驱动模式必须，prompt_only 模式也执行）**

prompt 文件落盘后、生图前，立即跑 `build_segments` 产出 `imgs/segments.json`（含 illustration_meta）。这让下游播客 conductor 在生图完成前就能拿到分段定义和图信息，消除 audio-to-social 的隐藏竞态。

- **分段驱动模式**（`article_has_sections: true`）：走路径 A（`--from-outline`），不依赖文章插图引用：
  ```bash
  <py> <scripts>/build_segments.py \
    --article "<article>/公众号_文章.md" \
    --output "<article>/imgs/segments.json" \
    --from-outline "<article>/imgs/outline.md" \
    --prompts-dir "<article>/imgs/prompts"
  ```
- **全局模式**（`article_has_sections: false`，无 `##` 章节）：Step 5.1b 跳过，segments.json 在 Step 7（文章插图后）用扫描模式产出。

**⛔ prompt_only 检查**：如果 `prompt_only == true`，在完成 Step 5.1-5.1b（prompt 文件构建 + segments.json 产出）后直接返回：
```json
{
  "success": true,
  "data": {
    "prompt_files": ["imgs/prompts/01-infographic-concept.md", ...],
    "outline_file": "imgs/outline.md",
    "segments_file": "imgs/segments.json",
    "mode": "prompt_only"
  }
}
```
**不进入** Step 5.2-5.3（图片生成）和 Step 6（插入文章）。调用方（如 audio-to-social）稍后会将这些 prompt 文件与其他图片 prompt 一起批量提交给 `article-cover-image-generator`；同时下游播客（conductor）已经可以读 segments.json 开始规划蓝图——这是分段驱动的核心收益。

3. **并行生成所有插图**：委托 `article-cover-image-generator` skill 的批量并行模式（参见 [article-cover-image-generator 批量并行生成](../article-cover-image-generator/SKILL.md#批量并行生成)和 [Gaoding 并行生成模式](../image-generator/references/gaoding-image-generation.md#并行生成模式)）
   - 所有 prompt 先落盘到 `prompts/` 目录
   - Gaoding：在创建页连续提交所有 prompt 并点击生成，然后轮询等待所有编辑器 tab，按完成顺序逐个导出
   - Agnes：所有 `agnes_image.py` 命令后台并行执行
4. Gaoding 失败回退（受 config 控制）：仅当 `illustration.fallback_to_agnes == true`（默认 `false`）时回退 Agnes，否则跳过该图并记录失败 ID。与 `audio-to-social` 的"默认不回退"策略一致。回退命令：
   ```bash
   {config.environment.conda_python} skills/image-generator/scripts/agnes_image.py --prompt "{prompt}" --size 1920x1080 --output "{output_dir}/{filename}" --json
   ```
5. 验证每张图片存在且 > 5KB

> 公众号上传使用 PNG 原图（微信不接受 webp）；图片压缩由调用方（如 audio-to-social Phase 7 `compress_images.py`）统一处理，本 skill 不压缩。

### 6. 插入与报告

1. 在文章 Markdown 中，每个插图位置后插入 `![description](imgs/NN-{type}-{slug}.png)`
2. 输出摘要：
   ```
   Article Illustration Complete!
   Article: [path] | Preset: [preset] | Density: [density]
   Images: X/N generated
   ```

### 7. 产出/校验分段定义（imgs/segments.json）

`imgs/segments.json` 是**按插图分段的唯一权威来源**：下游播客（conductor 按 segment 分组要点、读 illustration_meta 对齐图内容）和视频（plan_scenes 按 segment 配图）都读它，不再各自重新分析文章结构。每个 segment 除 index/role/heading 外，含 `illustration`（图路径）和可选的 `illustration_meta`（type/title_text/labels，从 prompt 文件 frontmatter 提取）。

产出时机按模式分两种：

- **分段驱动模式**：segments.json 已在 Step 5.1b 产出（路径 A，`--from-outline`）。Step 7 退化为**校验**——确认 Step 6 插入文章的 `![]()` 路径与 outline 的 Filename 一致。不一致则修正 segments.json 或重新插入。
- **全局模式**（无 `##` 章节）：segments.json 在此步产出（路径 B，扫描模式）：
  ```bash
  <py> <scripts>/build_segments.py --article "<article>/公众号_文章.md" \
    --output "<article>/imgs/segments.json" --prompts-dir "<article>/imgs/prompts"
  ```
  扫描文章里的 `![]()` 引用，每张图归属它之前最近的 `##` 标题。无 `##` 章节的文章 `segment_count=0`，下游回退原逻辑。

> segments.json 的 schema（build_segments.py 产出）：
> ```json
> {
>   "index": 0, "role": "body", "heading": "一、核心概念",
>   "heading_line": 5, "content_end_line": 12,
>   "illustration": "imgs/01-infographic-concept.png", "illustration_line": 10,
>   "illustrations": ["imgs/01-infographic-concept.png", "imgs/02-flowchart-detail.png"],
>   "illustration_meta": {"type": "infographic", "title_text": "核心概念", "labels": ["要素A", "要素B"]}
> }
> ```
> - `illustration`（单值）= `illustrations[0]`，向后兼容旧下游。
> - `illustrations`（数组）= 该段全部图路径；一段一图时为单元素列表。
> - `illustration_meta` 仅当传了 `--prompts-dir` 且对应 prompt 文件存在时才有；一段多图时 labels 取并集、type 取首张（不一致时为 "mixed"）；否则该键不出现（向下兼容旧下游）。

## 产物结构

（全局总览见 [docs/article-manifest.md](../../../docs/article-manifest.md)）

```
{article-dir}/
├── {article}.md                  # 更新后的文章（含图片引用）
├── imgs/
│   ├── outline.md                # 含 Segment/Title Text/Labels 字段
│   ├── segments.json             # 分段定义（含 illustration_meta），Step 5.1b 产出
│   ├── prompts/
│   │   ├── 01-infographic-concept.md   # frontmatter 含 title_text/labels
│   │   └── 02-scene-scenario.md
│   ├── 01-infographic-concept.png
│   └── 02-scene-scenario.png
```

## 脚本目录

| 脚本 | 用途 |
|------|------|
| `scripts/build_segments.py` | Step 5.1b/7：产出 `imgs/segments.json`（章节→插图分段 + illustration_meta）。两种路径：`--from-outline`（分段驱动，文章未插图时用）/ 扫描模式（默认）。下游播客/视频复用 |

## 按需读取

| 文件 | 用途 | 加载时机 |
|------|------|---------|
| `references/workflow.md` | 详细工作流 | Step 2-6 |
| `references/prompt-construction.md` | Prompt 构建规范和模板 | Step 5 |
| `references/style-presets.md` | 预设定义（~30 个）+ Content Type 推荐 | Step 3 |
| `references/styles.md` | Style 索引 + Type×Style 兼容矩阵 + 自动推荐 | Step 3, 5 |
| `references/styles/<name>.md` | 单个 style 的七段式完整定义 | Step 5（拼 prompt 时按需加载对应 style） |
| `references/style-rendering-mapping.md` | style→cover (rendering,palette) 映射（单一来源） | Step 5（委托 article-cover-image-generator 时） |
| `references/palettes.md` | 色板定义（4 种） | Step 5 |
| `references/density-guide.md` | 密度策略 | Step 2 |

## 确认策略

| 情况 | 行为 |
|------|------|
| 用户说"直接生成" | 跳过 Step 3 确认，使用推荐设置 |
| 用户指定 preset | 跳过 Q1 |
| config.json 有配置 | 作为默认值，确认时预选 |

## 与 audio-to-social 集成

当被 audio-to-social 调用时：
- `visual_preset` 自动映射到预设：knowledge-card→knowledge, cozy-story→narrative, bold-warning→analysis, minimal-opinion→analysis
- 输入为 `公众号_文章.md`
- 输出目录为 `{output_dir}/imgs/`

**两步委派**（消除隐藏竞态）：audio-to-social 把插图委派拆成两步：
1. **Phase 3b-prepare**（prompt_only=true）：illustrator 跑到 Step 5.1b，产出 prompt 文件 + outline + segments.json（含 illustration_meta），返回 prompt_only JSON。此时下游播客 conductor 已可读 segments.json 开始规划蓝图。
2. **Phase 3b-render**：illustrator 继续跑 Step 5.2-5.3（生图）+ Step 6（回写文章）。可与 Phase 4（播客）并行——播客不依赖 PNG，只依赖 segments.json 的 meta 信息。

**prompt_only 返回的 segments_file 字段**：Phase 4 的 conductor 读它来按 segment 分组要点 + 对齐图内容（illustration_meta 的 labels 决定播客要讲哪些词）。

**微信发布说明**：`wechat-mp-draft.js` 创建草稿时自动扫描 HTML 中的 `imgs/` 图片引用，通过微信 `uploadimg` API 上传 PNG 文件并替换为微信 URL。
