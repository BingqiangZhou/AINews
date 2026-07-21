# Visual Preset Mapping

ai-news-digest 的 `visual_preset`（`knowledge-card` / `cozy-story` / `bold-warning` / `minimal-opinion`）到三维（Type × Style × Palette）的映射。Cover 模式与 Illustrate 模式分别映射——两者的 type 语义不同（cover 偏抽象概念图，illustrate 偏具体信息图），分开定义避免语义分歧。

> **三维法**：每个 visual_preset 展开为 `type + style + palette`（palette 全局锁 warm）。Rendering 从 style 派生（查 [style-rendering-mapping.md](style-rendering-mapping.md)），Text/Font 从 type 派生（查本文件第三节）。

---

## 一、Cover Visual Preset Mapping（mode=cover，900x383）

> **Palette 全局锁 warm**（见 SKILL.md「关键规则 #14」）：cover 模式 palette 无条件 `warm`，本表 palette 列全部为 `warm`，不再因 visual_preset 变化。type/style 仍按 visual_preset 映射。

| visual_preset | type | style | palette | 说明 |
|---------------|------|-------|---------|------|
| `knowledge-card` | conceptual | sketch-notes | warm | 封面抽象概念图（cover 专用 Type） |
| `cozy-story` | scene | warm | warm | 氛围场景封面 |
| `bold-warning` | metaphor | screen-print | warm | 视觉隐喻封面（高对比） |
| `minimal-opinion` | minimal | minimal | warm | 极简封面 |

### 派生维度（Cover 表）

派生维度由 type/style 自动派生，不暴露给用户：

| visual_preset | rendering（派生） | text（派生） | font（派生） | mood |
|---------------|------------------|--------------|--------------|------|
| `knowledge-card` | hand-drawn | none | clean | balanced |
| `cozy-story` | hand-drawn | title-only | handwritten | subtle |
| `bold-warning` | screen-print | none | handwritten | bold |
| `minimal-opinion` | flat-vector | none | clean | subtle |

> Cover Alternative Palette：全局锁 warm，无 alternative。

---

## 二、Illustrate Visual Preset Mapping（mode=illustrate，1920x1080）

> **illustrate 模式 type 映射**：illustrate 模式禁用 cover 专用的 `conceptual` Type，需要具体信息结构类 Type（infographic/flowchart/comparison/framework/timeline/scene），因此本表为 illustrate 单独定义 type 映射，**与 cover 表解耦**。
>
> **Palette 全局锁 warm**：illustrate 模式 palette 无条件 `warm`（见 SKILL.md 规则 #14），本表 palette 列全部为 `warm`。type/style 仍按 visual_preset 映射。

| visual_preset | type | style | palette | 说明 |
|---------------|------|-------|---------|------|
| `knowledge-card` | infographic | sketch-notes | warm | 知识/数据/清单的标签密集信息图 |
| `cozy-story` | scene | warm | warm | 叙事场景（个人经历/复盘） |
| `bold-warning` | comparison | ink-notes | warm | 对比/避坑（前后/优劣，强对比） |
| `minimal-opinion` | infographic | minimal | warm | 观点/反思的极简信息图 |

> **设计逻辑**：
> - `knowledge-card`（事实/工具/步骤/指标）→ `infographic`（最通用的信息图，涵盖知识总结）
> - `cozy-story`（个人经历/情感）→ `scene`（氛围场景，与 cover 一致）
> - `bold-warning`（避坑/冲突/反差）→ `comparison`（对比图最能体现"前后/优劣"的张力）
> - `minimal-opinion`（观点/反思）→ `infographic`（观点也需要信息结构化表达，而非纯抽象）

### 派生维度（Illustrate 表）

派生维度由 type/style 自动派生：

| visual_preset | rendering（派生） | text（派生） | font（派生） | mood |
|---------------|------------------|--------------|--------------|------|
| `knowledge-card` | hand-drawn | text-rich | handwritten | balanced |
| `cozy-story` | hand-drawn | title-only | handwritten | subtle |
| `bold-warning` | chalk | title-subtitle | handwritten | bold |
| `minimal-opinion` | flat-vector | text-rich | handwritten | subtle |

> palette 已固定 `warm`，无 alternative。

---

## 三、Type → Text/Font 默认值（cover 和 illustrate 共用，11 值 Type）

> **本表是 Type → Text/Font 映射的唯一事实源**。三维法下 Text 和 Font 都从 Type 派生（不是用户维度），cover 和 illustrate 模式共用此表。无论 visual_preset 是什么，按当前 Type（11 值）查此表得 text/font。

| Type | text | font | 理由 |
|------|------|------|------|
| infographic | `text-rich` | `handwritten` | 标签 + 数据点 + 标题，文字密集 |
| flowchart | `text-rich` | `handwritten` | 步骤名 + 箭头标签 + 判断节点 |
| comparison | `title-subtitle` | `handwritten` | 左右标题 + 要点说明 |
| framework | `text-rich` | `handwritten` | 概念节点 + 关系标签 |
| timeline | `title-subtitle` | `handwritten` | 时间标签 + 事件描述 |
| scene | `title-only` | `handwritten` | 场景标题，无额外标签（也可 none） |
| hero | `none` | `clean` | 封面为主，文字交给排版系统 |
| conceptual | `none` | `clean` | **cover 专用**，illustrate 禁用 |
| typography | `title-only` | `display` | 文字主导 |
| metaphor | `none` | `handwritten` | 隐喻靠图像，文字宜少 |
| minimal | `none` | `clean` | 极简，无文字 |

**单一信息源声明**：本节是 Type → Text/Font 映射的唯一事实源。[dimensions.md](dimensions.md) 的 Type 详解段保留一行「派生 Text/Font」速查列、[prompt-construction.md](prompt-construction.md) 均与本表保持一致；如出现冲突以本表为准。
