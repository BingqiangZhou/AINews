---
name: article-image-studio
version: "3.4.2"
description: >
  文章视觉资产一体化编排器——封面（单图）+ 插图（文章级多图）+ segments.json（下游分段权威）。
  统一三维方法论（Type × Style × Palette）+ 单一 `--preset` 别名系统（每个 preset 展开为完整三维），
  委托 image-generator 出图。三种模式：cover（单图封面）/ illustrate（文章配图）/ batch（批量混合）。
  **触发场景**：用户提到"生成封面""封面图""为文章配图""生成插图""illustrate article"
  "add images to article""cover image""文章插图"，或需要为文章/公众号/小红书/抖音生成
  封面图与配图时使用。
---

# Article Image Studio

文章视觉资产一体化编排器。统一处理封面（单图）与插图（文章级多图），共享**单一三维方法论（Type × Style × Palette）**与 prompt 构建，通过 `mode` 参数分支不同流程。实际生图统一委托 `image-generator` skill（Gaoding/Jimeng/Agnes/Pollinations 多后端）。

> 本文档只描述当前状态。

## 关联 Skills

- **ai-news-digest**：Phase 7a（封面，cover 模式）+ Phase 7b（插图，illustrate 模式，两步委派 prepare/render）委托本 skill
- **article-studio**：产出 `公众号_文章.md` 后，配图与封面留给本 skill
- **article-to-solo-podcast**：读本 skill 产出的 `imgs/segments.json`（含 illustration_meta）按 segment 分组要点 + 对齐图内容
- **article-to-video**：读 `imgs/segments.json` 按 segment 配图
- **image-generator**：实际生图后端（Gaoding/Jimeng/Agnes/Pollinations），本 skill 委派之

---

## 三种模式

| 模式 | 触发场景 | 入参特征 | 产物 |
|---|---|---|---|
| **cover** | 单张封面（900×383 公众号 / 自定义） | `content_context` + `target_size` + `mode=cover`（默认） | `公众号_封面.png` + `prompts/cover.md` |
| **illustrate** | 文章配图（1920×1080，多张） | `article_file` + `mode=illustrate` | `imgs/*.png` + `outline.md` + `segments.json` + 回写文章 |
| **batch** | 批量任意尺寸混合（封面 + 多张插图） | `images[]` 数组 + `mode=batch` | 多张 PNG |

未显式传 `mode` 时按入参特征自动判定：有 `article_file` → illustrate；有 `images` 数组 → batch；否则 → cover。

---

## 三维方法论（唯一权威）

| 维度 | 可选值 | 默认 |
|------|--------|------|
| **Type**（11 值） | hero, conceptual, typography, metaphor, scene, minimal（视觉构图类，cover 场景为主）+ infographic, flowchart, comparison, framework, timeline（信息结构类，illustrate 场景为主） | auto（按 mode 分流推荐） |
| **Style**（23 值） | sketch-notes, vector-illustration, notion, elegant, warm, minimal, blueprint, watercolor, editorial, scientific, chalkboard, fantasy-animation, flat, flat-doodle, intuition-machine, nature, pixel-art, playful, retro, sketch, screen-print, ink-notes, vintage | sketch-notes |
| **Palette** | **锁 warm**（cover/illustrate 模式硬锁，见下方「关键规则：Palette 全局锁 warm」） | warm |

### 派生维度（不暴露给用户）

三维之外的视觉控制全部派生自上述三维，**不是用户参数**：

| 派生维度 | 来源 | 说明 |
|---|---|---|
| **Rendering** | 查 [style-rendering-mapping.md](references/style-rendering-mapping.md) | Style → Rendering（7 值：flat-vector/hand-drawn/painterly/digital/pixel/chalk/screen-print）。如 `ink-notes → chalk`、`sketch-notes → hand-drawn` |
| **Text** | 查 [visual-preset-mapping.md](references/visual-preset-mapping.md) 的「Type → Text/Font」表 | Type → Text（4 值：none/title-only/title-subtitle/text-rich）。如 `hero → none`、`infographic → text-rich` |
| **Font** | 查 [visual-preset-mapping.md](references/visual-preset-mapping.md) 的「Type → Text/Font」表 | Type → Font（4 值：clean/handwritten/serif/display）。如 `hero → clean`、`infographic → handwritten` |
| **Mood** | 默认 `balanced` | 不暴露为维度，不参与 auto-selection |

→ Type 11 值详细定义见 [dimensions.md](references/dimensions.md)
→ Style 23 值详细定义见 [styles.md](references/styles.md) + `styles/<name>.md`
→ Style → Rendering 映射见 [style-rendering-mapping.md](references/style-rendering-mapping.md)
→ Type → Text/Font 映射见 [visual-preset-mapping.md](references/visual-preset-mapping.md)
→ auto-selection 规则（含 Type → Style 推荐）见 [auto-selection-rules.md](references/auto-selection-rules.md)
→ 兼容性矩阵见 [compatibility-matrix.md](references/compatibility-matrix.md)

## 用户友好别名层

为降低三维直接选择的认知成本，提供 `--preset` 别名系统：

1. **`--preset X`**：详见 [style-presets.md](references/style-presets.md)。每个 preset 直接展开为三维（type + style + palette），其中 palette 列在实际生成时被 warm 锁覆盖。
2. **`--style X`**（独立参数，控制 Style 维度）：直接指定 23 个 style 之一（如 `--style ink-notes`）。
3. **`--visual_preset X`**（4 个，ai-news-digest 专用 convenience preset）：自动展开为三维策略，Cover/Illustrate 两张映射表分别处理，详见 [visual-preset-mapping.md](references/visual-preset-mapping.md)。

> **23 个 style（sketch-notes/ink-notes/blueprint...）是运行时维度**。Style 既决定 Rendering（派生），也提供视觉语言细节——`styles/<name>.md` 的 Visual Elements / Style Rules 段在 Step 4 拼 prompt 时按需查阅，把关键视觉描述词写进 prompt 正文（详见 [prompt-construction.md](references/prompt-construction.md) 的「维度加载顺序」、[prompt-template.md](references/prompt-template.md) 的「Style 参考文档触发规则」）。

## 色板

**Palette 全局锁 warm**（见规则 #14）。11 色板 hex 定义保留作参考（custom 模式或未来解锁时可用）。→ 完整定义见 [palette-colors.md](references/palette-colors.md)

---

## 流程概览

### cover 模式
```text
输入（content_context + target_size） → [加载偏好] → [分析内容 + 自动选 Type/Style（Palette 锁 warm）]
→ [派生 Rendering（查 style-rendering-mapping）+ Text/Font（查 Type→Text/Font 表）]
→ [构建 Prompt（用 styles/<style>.md 视觉语言）] → [生成图片] → [后处理] → [报告]
```

### illustrate 模式
```text
输入文章 Markdown → [分析结构与内容类型（三层：全局→切段→分段）]
→ [确认 settings（preset/density/style）]
→ [生成插图大纲（position, type, style, visual content, filename）]
→ [逐张构建 prompt 并落盘到 prompts/（frontmatter 含 type/style/palette=warm）]
→ [产出 segments.json（含 illustration_meta）]  ← Step 5.1b，下游 conductor 前置
→ [image-generator 生图]
→ [插入图片引用到文章 Markdown] → [报告]
```

### batch 模式
```text
输入 images[] 数组（每项含 prompt_file/target_size/output_path）
→ [校验所有 prompt 文件存在] → [按 backend 选择并行/串行策略]
→ [image-generator 批量生成] → [逐张后处理验证] → [汇总报告]
```

---

## 关键规则

> 合并自原 cover（14 条）+ illustrator（7 条），去重对齐为下方 14 条主规则 + 4 条 illustrate 模式额外规则（共 18 条编号）。规则后标注适用 mode。

1. **Prompt 先落盘**（all）：所有 prompt 必须先写入 `prompts/` 目录，再调用生成后端。
2. **Gaoding 只点一次**（all）：生图按钮只点击一次（每次消耗 3 豆），通过 `list_pages` 轮询等待结果。
3. **覆盖前备份**（all）：写入任何输出文件前，已存在的非空文件先备份。
4. **Text 由 Type 派生**（all）：三维法下 text 不是用户参数，由 [visual-preset-mapping.md](references/visual-preset-mapping.md) 的「Type → Text/Font」表派生（如 `hero → none`、`infographic → text-rich`）。
5. **回退受 config 控制**（all）：Gaoding/Jimeng 失败时，仅当 `backend.fallback_to_agnes == true`（默认 `false`）才回退 Agnes；否则报告失败由调用方决定。与 ai-news-digest 的"默认不回退"策略一致。
6. **参数化尺寸**（all）：通过 `target_size` 参数控制输出尺寸（900x383 / 1920x1080 / 自定义）。
7. **自动取消社区发布**（all，Gaoding）：Gaoding 导出时必须取消勾选"自动发布至社区"。
8. **批量并行**（batch/illustrate）：多张图片（封面 + 插图，或多张插图）尽量并行生成，不逐张串行（受 backend 串行约束除外，见 #10）。
9. **Gaoding 互斥**（all）：同一时刻只能有一个 agent/进程操作 Gaoding（共享 Chrome 实例）。被编排调用时，多个图片请求必须在同一个 agent 内用批量模式处理，不能启动多个并行 agent 分别调用 Gaoding。
10. **⛔ Gaoding 多图必须串行（每张新 tab）**（batch/illustrate）：同一创建页 tab 内反复 `innerHTML='' + execCommand('insertText')` **不能可靠触发 React 状态更新**，会导致"每次提交的都是同一个 prompt"、生成出来全是雷同的图。多张图**必须每张开一个全新 tab**（`new_page` → `creation?skill=3`），每张独立选模型→输入→验证→生成→导出。详见 [`../image-generator/references/gaoding-image-generation.md`](../image-generator/references/gaoding-image-generation.md)「串行生成模式」。
11. **⛔ 禁止程序化替代生图**（all）：绝不允许用 SVG/HTML/canvas/Canvas API/PIL/Pillow 绘图等方式替代 AI 图像模型生成位图。封面/插图必须是 `image-generator` 经由 Gaoding（万相2.7）/ Agnes / Jimeng 产出的真实位图。后处理仅允许：crop / resize / 压缩 / 格式转换（且不得改动主构图或文字）。
12. **⛔ 禁止程序化修补已生成图的文字**（all）：若生成图含错误文字/乱码，**禁止**用 PIL/Pillow/ImageMagick 在已生成图上贴字、抹字、改字。正确做法：(a) 修改 prompt 重新生成，或 (b) 改用 `text: none` 变体重生成。
13. **后端失败显式上报，不静默降级**（all）：`image-generator` 返回 `success: false` 时，本 skill 必须把失败结果 + `fallback_reason` 原样上报调用方，不静默重试、不静默换后端（除非 `backend.fallback_to_agnes: true`）。
14. **⛔ Palette 全局锁 warm**（all）：cover 与 illustrate 模式 **palette 全局固定为 `warm`**，由 config.json `preferences.default_palette` + `cover.palette` 共同锁定为单一来源。**不被 visual_preset / preset / `--palette` / auto-selection 覆盖**——所有 preset 和 style 自带的 palette-default 列仅作参考，实际生成时一律 `warm`。保留品牌色一致性策略（用户实测 26 个预设后选定）。仅 cover/illustrate 模式生效；custom 模式不应用此锁。

### illustrate 模式额外规则

15. **同一篇文章风格一致**（illustrate）：同一篇文章的所有插图 type 系列 + style 保持一致（如教程类统一 flowchart + sketch-notes，对比类统一 comparison + ink-notes）。Palette 已全局锁 warm（规则 #14），无需文章内额外约束。Type 按段落内容自由选（教程配 flowchart、对比配 comparison），style 文章级统一。
16. **密度控制**：通过 `density` 参数控制插图数量（minimal 1-2 / balanced 3-5 / per-section 每段一张 / rich 6+），不盲目堆砌。
17. **隐喻不直译**：文章中的隐喻/比喻不直接画成字面图像，而是可视化背后的概念。
18. **中文 Prompt**：所有 prompt 使用中文编写，图片内的文字（标题、标签、数据）也使用中文。

---

## 偏好与优先级

三维值解析遵循单一优先级链（高 → 低），保证"偏好可覆盖、显式参数最高"：

```
[Palette 全局锁 warm] — cover/illustrate 模式最高优先（见「关键规则 #14」）
        │   由 config.json preferences.default_palette + cover.palette 共同锁定
        │   不被任何 preset / --palette / auto-selection 覆盖
        ↓ Type 与 Style 维度（cover/illustrate）+ 全维度（custom）走以下链：
显式传入参数（--type / --style / backend.provider / target_size 等）
        ↓ 若为 auto 或未传
visual_preset / preset 映射（三维展开：type + style + palette）
        ↓ 若仍为 auto 或未覆盖该维度
config.json → preferences 段（用户偏好，见下）
        ↓ 若为 auto
auto-selection-rules（内容信号驱动；含 Type → Style 推荐表）
```

> **派生维度不参与优先级链**：Rendering（从 Style 派生，查 [style-rendering-mapping.md](references/style-rendering-mapping.md)）、Text/Font（从 Type 派生，查 [visual-preset-mapping.md](references/visual-preset-mapping.md)）、Mood（默认 balanced）——这三个维度不是用户参数，不进入优先级链，也不在 config.json 暴露默认值字段。

| preferences 字段 | 取值 | 说明 |
|------|------|------|
| `default_type` | auto / hero / conceptual / infographic / ... | 默认 Type 偏好（11 值之一） |
| `default_style` | auto / sketch-notes / ink-notes / ... | 默认 Style 偏好（23 值之一） |
| `default_palette` | warm（硬锁） | 默认 Palette——锁 warm（规则 #14），改此项无效 |
| `default_aspect` | 2.35:1 / 16:9 / 1:1 | 默认宽高比（未显式传 target_size 时参考） |
| `language` | zh / en / auto | prompt 语言偏好（auto = 按内容检测） |
| `disabled_presets` | string[] | 禁用的 `--preset` 名列表（命中时回退到 auto-selection） |

> **单一来源声明**：遵循 AGENTS.md「config.json 是单一来源」约定。所有偏好集中在 config.json 的 `backend` + `cover` + `preferences` 三段。
>
> **config 字段说明**：`default_rendering` / `default_text` / `default_mood` / `default_font` 字段已废弃（派生维度不读 config，见上）；`default_style` 是有效字段。config.json 仍可保留这些旧字段做向后兼容，但解析时忽略。

---

## 输入（按 mode 分类）

### cover 模式输入

| 参数 | 必选 | 说明 |
|------|------|------|
| `content_context` | 是 | 文章标题 + brief 核心论点 + 话题关键词 |
| `target_size` | 是 | 输出尺寸，如 `900x383`、`1920x1080` |
| `type` | 否 | 11 值 Type 之一，auto 则自动推荐（cover 偏 hero/conceptual） |
| `style` | 否 | 23 值 Style 之一，auto 则按 Type 推荐（默认 sketch-notes） |
| `visual_preset` | 否 | convenience preset 名称，自动映射为三维策略 |
| `preset` | 否 | `--preset` 别名之一（见 [style-presets.md](references/style-presets.md)）。三维展开为 type + style + palette（palette 被 warm 锁覆盖） |
| `backend.provider` | 否 | gaoding（默认）/ jimeng / agnes |
| `output_path` | 是 | 输出文件路径 |
| `output_dir` | 是 | 输出目录（prompts/ 和产物存放） |
| `references` | 否 | 参考图片路径列表 |
| `prompt_only` | 否 | boolean, default false。为 true 时只执行 Steps 1-4，跳过图片生成 |

> Rendering / Text / Font / Mood 不是用户参数（派生维度，见「三维方法论」）。Palette 锁 warm（规则 #14），`--palette` 被忽略。

### illustrate 模式输入

| 参数 | 必选 | 说明 |
|------|------|------|
| `article_file` | 是 | 文章 Markdown 文件路径 |
| `preset` | 否 | `--preset` 三维组合（默认按内容推荐，无信号时 `hand-drawn-edu`） |
| `density` | 否 | minimal / balanced / per-section / rich（默认 balanced） |
| `type` | 否 | 11 值 Type 之一（illustrate 偏 infographic/flowchart/comparison/framework/timeline/scene） |
| `style` | 否 | 23 值 Style 之一（覆盖 preset 的 style；文章级统一） |
| `visual_preset` | 否 | ai-news-digest 专用 convenience preset |
| `backend.provider` | 否 | gaoding（默认）/ jimeng / agnes |
| `output_dir` | 否 | 默认 `{article-dir}/imgs/` |
| `prompt_only` | 否 | boolean, default false。为 true 时只产出 prompt + outline + segments.json，不生图 |

> 同 cover 模式：派生维度非用户参数，Palette 锁 warm。

### batch 模式输入

| 参数 | 必选 | 说明 |
|------|------|------|
| `images` | 是 | 图片列表，每项含 `prompt_file` / `target_size` / `output_path` |
| `backend.provider` | 否 | gaoding（默认）/ jimeng / agnes |

---

## 输出

### cover / batch 模式输出（完整生成）

```json
{
  "success": true,
  "data": {
    "image_path": "生成的图片文件路径",
    "provider": "gaoding | jimeng | agnes",
    "dimensions": { "type": "...", "style": "...", "palette": "warm", "rendering": "...(派生)", "text": "...(派生)", "mood": "balanced", "font": "...(派生)" },
    "fallback_used": false,
    "fallback_reason": null,
    "original_size": "1923x818",
    "final_size": "900x383"
  }
}
```

> `dimensions` 中 `type` / `style` 是用户三维，`palette` 锁 warm；`rendering` / `text` / `font` 是派生值（供追溯），`mood` 默认 balanced。

其余输出场景（仅列 schema 关键字段）：

| 场景 | 返回结构关键差异 |
|------|------|
| **cover/batch prompt_only** | `data.prompt_file` + `data.dimensions` + `data.target_size` + `data.mode: "prompt_only"`（无 image_path） |
| **batch 汇总** | 顶层 `results[]` 数组，每项 `{success, data \| error}` |
| **illustrate 完整** | `data.generated[]` + `data.failed[]` + `data.total` + `data.outline_file` + `data.segments_file` |
| **illustrate prompt_only** | `data.prompt_files[]` + `data.outline_file` + `data.segments_file` + `data.mode: "prompt_only"` |

---

## 执行步骤

### cover 模式步骤

#### 1. Pre-check

1. 读取 `config.json` 的 `cover` 段 + `preferences` 段 + `backend` 段获取偏好设置（provider、gaoding_model、jimeng_model、model(Agnes 回退)、三维默认 type/style、语言偏好等）。按「偏好与优先级」段的优先级链合并（废弃字段见该段说明）。
   > **AINews 单一来源**：跨 skill 共享字段（`backend.{provider,model,gaoding_model,jimeng_model}`、`environment`）优先读 `../ai-news-digest/config.json#cover` + `#environment`，本 skill 的 config.json 仅作 fallback 与本地三维偏好。
2. 确认 `output_dir` 存在，不存在则创建。
3. 确认 `content_context` 和 `target_size` 已提供。

#### 2. 内容分析

1. 分析 content_context：提取主题、基调、关键词、视觉隐喻。
2. 检测内容语言。
3. **参考图深度分析**（当 `references` 非空时）：读取 [reference-images.md](references/reference-images.md)，按 6 维度表（品牌元素/标志性图案/精确 hex/布局比例/字体处理/渲染特征）提取可复现元素，标注 `usage`（direct/style/palette），保存参考图到 `refs/ref-NN-{slug}.{ext}`。这些元素将在 Step 4 按 MUST/REQUIRED 规则注入 prompt 正文。

#### 3. 维度选择（自动，不询问用户）

根据 content 信号自动推荐 Type 和 Style，全自动无交互（Palette 已锁 warm、Rendering/Text/Font/Mood 已派生，见「三维方法论」）：

- 如果传入了 `visual_preset`，使用 [visual-preset-mapping.md](references/visual-preset-mapping.md) Cover 表的映射（取 type + style）
- 如果传入了 `preset`，使用 [style-presets.md](references/style-presets.md) 的三维映射（取 type + style；palette 列被 warm 覆盖）
- 如果传入了显式 `--type` / `--style`，使用显式值
- 剩余 auto 维度（type/style）：根据 content_context 信号和 [auto-selection-rules.md](references/auto-selection-rules.md) 自动推荐（cover 偏 hero/conceptual/typography/metaphor/minimal + sketch-notes/warm/elegant 等）
- **派生 Rendering**：查 [style-rendering-mapping.md](references/style-rendering-mapping.md) 按 style 得 rendering
- **派生 Text/Font**：查 [visual-preset-mapping.md](references/visual-preset-mapping.md)「Type→Text/Font」表按 type 得 text/font
- 检查兼容性矩阵（Type × Rendering 派生组合若冲突，调整 style）
- 直接进入 Step 4，不暂停等待用户确认

#### 4. Prompt 构建

1. 根据 target_size 确定 target profile：

| Profile | target_label | target_size_desc | prompt_language |
|---------|-------------|-----------------|----------------|
| wechat-cover | WeChat公众号封面图 | 尺寸900x383像素，宽幅横版banner比例约2.35:1 | English |
| illustration | 文章插图 | 尺寸1920x1080像素，16:9宽幅横版比例 | 中文 |
| custom | 自定义 | 尺寸{W}x{H}像素 | 视场景 |

2. 构建 visual prompt（20-40 词描述），**使用 [prompt-template.md](references/prompt-template.md) 的 6 槽位结构**（Subject + Setting + Lighting + Style words + Mood + Composition）。**Style words 槽位的视觉描述词从 `styles/<style>.md` 加载**（三维法的 Style 维度）。
3. **颜色规则**：视觉 prompt 中**只用描述性颜色名称**，**禁止包含任何 hex 色值**。hex 仅写入 prompt 文件的 YAML frontmatter。
4. 写入 `prompts/cover.md`（或 `prompts/NN-{type}-{slug}.md`），记录：最终 prompt（含尺寸前缀）、三维策略（type + style + palette=warm）+ 派生维度（rendering/text/font/mood）、backend.provider、target_size、references（如有）。
5. **参考元素注入**（当 Step 2 分析了参考图时）：按 [reference-images.md](references/reference-images.md) §4 的转译规则，在 prompt 正文末尾追加 `# 参考元素 — 必须复现` 段落，每个元素用 MUST 前缀逐条描述。

#### 4.5 Prompt-Only 检查

如果 `prompt_only == true`：返回成功，`data.prompt_file` 设为 prompt 文件路径，`data.mode` 设为 `"prompt_only"`。**不进入** Step 5-7。

#### 5. 图片生成（委托 image-generator）

调用 `image-generator`，传入：`prompt_file` / `output_path` / `target_size` / `provider`。`image-generator` 内部处理后端选择、浏览器自动化、API 调用、回退（受 `backend.fallback_to_agnes` 控制）、后处理（>5KB 验证 + PIL 裁剪 + _raw 删除）。返回 `{ success, data: { image_path, provider, fallback_used, ... } }`。

> 含中文文字的封面必须用 Gaoding + 万相2.7，或 Jimeng + 图片 4.7（Agnes 中文渲染不稳定）。`backend.provider` 默认 `gaoding`。

#### 6-7. 后处理与报告

后处理已由 `image-generator` 完成。本 skill 只需读取返回的 `image_path` 确认存在，输出报告（Provider / Type / Palette / Rendering / Text / Mood / Font / Size / Location）。

---

### illustrate 模式步骤

#### 1. Pre-check

读取 `config.json` 的 `backend` 段（`provider` / `fallback_to_agnes`）+ `preferences` 段（三维默认偏好：default_type / default_style）。`cover` 段对 illustrate 模式不生效（仅 cover 模式用）。确认输入：文章文件路径（Markdown），可选 `--preset`/`--density`/`--style`/`--type` 覆盖默认值（`--palette` 被 warm 锁忽略）。`density` 默认值不在 config 中（runtime 决策，默认 `balanced`，见 [density-guide.md](references/density-guide.md)）。

#### 2. 分析文章（三层：全局 → 切段 → 分段）

目的是让「画什么」「画几张」「什么风格」的决策对齐文章的 `##` 章节结构，使每张图、每段内容都有明确的归属段。这一层产出的信息（每段的 type/title_text/labels）会通过 segments.json 传递给下游播客 conductor。

**关键规则**：隐喻 → 可视化背后概念，不画字面图像。

详见 [workflow.md](references/workflow.md#step-2-分析文章-三层-全局-切段-分段)。三层流程：

- **2a. 全局轻量分析**（1 次调用，读全文）：内容类型 / 推荐预设 / 全文 thesis / 全文 CTA / 密度预算 N。
- **2b. 切段**（确定性，无 LLM）：扫描 `##` 标题切段，得到 M 个 body segment。M ≥ 2 走分段驱动（Step 2c）；M = 0 退回全局模式。
- **2c. 分段分析**（1 次批处理调用）：逐段决定 type/visual_content/title_text/labels/position_hint。支持跨段图、一段多图、预算截断、片头片尾图（opening/ending）。

#### 3. 确认 Settings

一次 `AskUserQuestion`，最多 3 问。用户说"直接生成"/"跳过确认"时跳过。被编排调用时零交互。

| Q | 必选 | 说明 |
|---|------|------|
| Q1: 预设或 Type | 是 | 基于 Step 2 推荐 preset；无强信号时 `hand-drawn-edu`（=infographic + sketch-notes + warm） |
| Q2: 密度 | 是 | minimal / balanced / per-section / rich |
| Q3: Style | 选 preset 时跳过；手动选 type 时必填 | 推荐兼容 style + 备选（见 [auto-selection-rules.md](references/auto-selection-rules.md) 的 Type → Style 推荐表） |

> Palette 已全局锁 warm（规则 #14），不再询问色板。

#### 4. 生成大纲

保存 `{output_dir}/outline.md`（含 Segment / Heading / Position / Type / Purpose / Visual Content / Title Text / Labels / Filename 字段）。详见 [workflow.md](references/workflow.md)。

#### 5. 生成图片

**⛔ 阻塞步骤：Prompt 文件必须先生成并保存。**

1. 为每张插图构建 prompt，保存到 `prompts/NN-{type}-{slug}.md`（含 YAML frontmatter）。Prompt 结构遵循 [prompt-construction.md](references/prompt-construction.md)。
2. **⛔ Step 5.1b：产出 segments.json**（分段驱动模式必须，prompt_only 模式也执行）：
   - **分段驱动模式**（`article_has_sections: true`）：走路径 A（`--from-outline`）：
     ```bash
     <py> <scripts>/build_segments.py \
       --article "<article>/公众号_文章.md" \
       --output "<article>/imgs/segments.json" \
       --from-outline "<article>/imgs/outline.md" \
       --prompts-dir "<article>/imgs/prompts"
     ```
   - **全局模式**（`article_has_sections: false`）：Step 5.1b 跳过，segments.json 在 Step 7（文章插图后）用扫描模式产出。
3. **⛔ prompt_only 检查**：如果 `prompt_only == true`，在完成 Step 5.1-5.1b 后直接返回 prompt_only JSON，**不进入** Step 5.2-5.3 和 Step 6。下游 conductor 已可读 segments.json 开始规划蓝图。
4. **并行/串行生成所有插图**：调用 `image-generator` 的批量接口（Gaoding 多图串行每张新 tab；Agnes 多图并行；Jimeng 多图串行每张新对话）。并发上限 5 张。
5. Gaoding/Jimeng 失败回退（受 `backend.fallback_to_agnes` 控制，默认 false）。
6. 验证每张图片存在且 > 5KB。

> 公众号上传使用 PNG 原图（微信不接受 webp）；图片压缩由调用方（如 ai-news-digest Phase 8 archive 的 `compress_images.py`）统一处理，本 skill 不压缩。

#### 6. 插入与报告

1. 在文章 Markdown 中，每个插图位置后插入 `![description](imgs/NN-{type}-{slug}.png)`。
2. 输出摘要（Article / Preset / Density / Images X/N generated）。

#### 7. 产出/校验分段定义（imgs/segments.json）

`imgs/segments.json` 是**按插图分段的唯一权威来源**：下游播客 conductor 和视频 plan_scenes 都读它。产出时机按模式分两种（详见 [workflow.md](references/workflow.md)）：
- **分段驱动模式**：segments.json 已在 Step 5.1b 产出。Step 7 退化为校验。
- **全局模式**：segments.json 在此步用扫描模式产出。

---

## 被编排调用协议（ai-news-digest）

ai-news-digest 按以下三步委派本 skill，全程零交互：

1. **Phase 7a 封面**（cover 模式）：传 `content_context` + `target_size=900x383` + `output_path=<article_dir>/公众号_封面.png` + `visual_preset` + `backend.provider`。
2. **Phase 7b-prepare 插图**（illustrate 模式，`prompt_only=true`）：传 `article_file` + `visual_preset` + `density`。产出 prompt + outline + segments.json（含 illustration_meta）。下游播客 conductor 已可读 segments.json 开始规划蓝图。
3. **Phase 7b-render 插图**：续跑从 prompt_only 断点继续 Step 5.2-6，或批量委派 batch 模式生成所有 PNG 再回写。可与 Phase 7c（播客）并行——播客不依赖 PNG，只依赖 segments.json 的 meta 信息。

> `visual_preset` 自动映射：knowledge-card→knowledge, cozy-story→narrative, bold-warning→analysis, minimal-opinion→analysis（详见 [visual-preset-mapping.md](references/visual-preset-mapping.md)）。
> **微信发布说明**：`skills/browser-publisher/scripts/wechat-mp-draft.py` 创建草稿时自动扫描 HTML 中的 `imgs/` 图片引用，通过微信 `uploadimg` API 上传 PNG 文件并替换为微信 URL。

---

## 按需读取

| 文件 | 用途 | 加载时机 |
|------|------|---------|
| `references/dimensions.md` | 三维定义（Type 11 值 + Style 23 值 + Palette）+ 派生维度说明 | Step 3 |
| `references/style-presets.md` | `--preset` 统一别名系统（三维展开：type + style + palette） | Step 3 |
| `references/styles.md` | 23 style **运行时维度**索引 + Type×Style 兼容矩阵 + Auto Selection by Type | Step 3-4 |
| `references/styles/<name>.md` | 单个 style 的设计参考（Visual Elements / Style Rules，写 prompt 正文用） | Step 4（按 style 查阅） |
| `references/style-rendering-mapping.md` | **Style → Rendering 派生映射**（23 行，单一来源） | Step 3（派生 rendering 时） |
| `references/compatibility-matrix.md` | 兼容性矩阵（Type×Rendering 派生检查参考） | Step 3 |
| `references/auto-selection-rules.md` | 自动推荐规则（11 Type 信号 + Type → Style 推荐表） | Step 3 |
| `references/palette-colors.md` | 色板 hex 定义（11 + neon + mono-ink 别名；全局只用 warm） | Step 4 |
| `references/prompt-template.md` | prompt 6 槽位结构模板（cover/custom） | Step 4（cover/custom） |
| `references/prompt-construction.md` | 插图 prompt 构建规范（title_text/labels 硬约束，Type-Specific 模板） | Step 5（illustrate） |
| `references/reference-images.md` | 参考图深度处理框架 | Step 2（当 references 非空时） |
| `references/visual-preset-mapping.md` | visual_preset 映射（Cover/Illustrate 两表，三维展开）+ Type → Text/Font 默认值（11 行） | Step 3 |
| `references/density-guide.md` | 密度策略（illustrate） | Step 2（illustrate） |
| `references/workflow.md` | illustrate 模式详细工作流 | Step 2-6（illustrate） |
| `references/environment.md` | 运行依赖与换机器迁移清单 | 首次配置/换机器时 |

## 脚本目录

| 脚本 | 用途 |
|------|------|
| `scripts/build_segments.py` | illustrate Step 5.1b/7：产出 `imgs/segments.json`（章节→插图分段 + illustration_meta）。两种路径：`--from-outline`（分段驱动）/ 扫描模式（默认）。下游播客/视频复用 |

## 确认策略

**cover / batch 模式由 agent 自动完成，不询问用户、不需要用户选择。** Agent 根据 config.json 默认值、content 信号、auto-selection-rules、偏好链自动确定 Type 和 Style（Palette 锁 warm，Rendering/Text/Font/Mood 派生），直接进入生成步骤。

**illustrate 模式**：用户直接调用时有 Step 3 一次确认（最多 3 问，用户说"直接生成"跳过）；被编排调用时零交互。

- Type 与 Style 由 agent 按内容信号自动裁决（或用户显式指定）。
- 用户如需调整风格，可在生成后要求重新生成并显式指定 `--style` / `--type` / preset。

---

## 产物结构

### cover 模式
```
{output_dir}/
├── prompts/
│   └── cover.md              # 生成 prompt（含 YAML frontmatter）
└── {output_filename}.png      # 最终输出图片
```

### illustrate 模式
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
