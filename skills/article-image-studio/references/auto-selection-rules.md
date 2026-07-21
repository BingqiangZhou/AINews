# Auto-Selection Rules

三维法（Type × Style × Palette）下，当 Type 或 Style 为 auto 时，按内容信号自动推荐。

> **Palette 全局锁 warm**（见 SKILL.md 规则 #14）：cover 和 illustrate 模式 palette 无条件 warm，**不查本文件的 Auto Palette 表**。本文件的 Palette 表仅对 custom 模式或未来解锁时生效。
>
> **派生维度不参与 auto-selection**：Rendering（从 Style 派生）、Text/Font（从 Type 派生）、Mood（默认 balanced）——这些不是用户维度，由 [style-rendering-mapping.md](style-rendering-mapping.md) 和 [visual-preset-mapping.md](visual-preset-mapping.md) 自动派生。

## Auto Type Selection

> Type 枚举 11 值，分三类。视觉构图类（cover 场景为主）：hero/conceptual/typography/metaphor/minimal；信息结构类（illustrate 场景为主）：infographic/flowchart/comparison/framework/timeline；场景类：scene。**cover 和 illustrate 共用 11 值**，auto-selection 按 mode 分流推荐。
>
> **模式偏好**：
> - **cover 模式**：无强信号时选 `conceptual`（封面抽象概念图最通用）。偏 hero/conceptual/typography/metaphor/minimal/scene。
> - **illustrate 模式**：无强信号时选 `infographic`（最通用的信息图）。偏 infographic/flowchart/comparison/framework/timeline/scene。
>
> **模式限制**：
> - `conceptual` 是 **cover 专用** Type——illustrate 模式禁用（auto-selection 在 illustrate 模式遇到"架构/系统/API/技术"等 conceptual 信号时，改选 `infographic` 或 `framework`）。理由：conceptual 与 infographic 边界模糊，illustrate 需要具体信息结构。
> - `hero` / `typography` 主要用于 cover 封面，illustrate 模式极少触发。

| Signals | Type | 模式偏好 |
|---------|------|---------|
| Product, launch, announcement, release, reveal | `hero` | cover 为主 |
| Architecture, framework, system, API, technical, model（纯概念，无具体节点） | `conceptual` | **cover 专用**；illustrate 改用 `infographic` 或 `framework` |
| Quote, opinion, insight, thought, headline, statement | `typography` | cover 为主 |
| Philosophy, growth, abstract, meaning, reflection | `metaphor` | 通用 |
| Story, journey, travel, lifestyle, experience, narrative | `scene` | 通用 |
| Zen, focus, essential, core, simple, pure | `minimal` | 通用 |
| Knowledge, data, metrics, summary, concept explainer, list, onboarding | `infographic` | **illustrate 默认** |
| Steps, workflow, process, decision tree, installation, tutorial flow | `flowchart` | illustrate |
| Versus, before/after, pros/cons, evaluation, comparison, alternative | `comparison` | illustrate |
| System design, architecture nodes, concept model, mapping, hub-spoke | `framework` | illustrate |
| History, evolution, milestone, timeline, chronology, journey over time | `timeline` | illustrate |

## Auto Style Selection

> Style 是三维法的核心维度，当未显式指定 `--style` 且 preset 未覆盖时，按 Type 推荐 Style。

| Type | 首选 Style | 备选 Styles |
|------|------------|-------------|
| `hero` | screen-print | watercolor, fantasy-animation |
| `conceptual` | sketch-notes | vector-illustration, minimal, blueprint |
| `typography` | editorial | screen-print, elegant |
| `metaphor` | warm | watercolor, fantasy-animation, screen-print |
| `scene` | warm | watercolor, elegant, fantasy-animation, playful |
| `minimal` | minimal | vector-illustration, flat, notion |
| `infographic` | sketch-notes | vector-illustration, notion, blueprint, editorial |
| `flowchart` | sketch-notes | ink-notes, vector-illustration, notion |
| `comparison` | ink-notes | vector-illustration, elegant, sketch-notes |
| `framework` | ink-notes | blueprint, vector-illustration, sketch |
| `timeline` | elegant | sketch-notes, warm, vintage |

**选 Style 的辅助信号**（与 Type 推荐叠加）：

| 内容信号 | 偏好的 Style |
|---------|--------------|
| 教育、知识、儿童 | sketch-notes / flat-doodle / playful |
| 技术、API、工程 | blueprint / notion / scientific |
| 数据、报告、仪表盘 | editorial / scientific |
| 黑墨视觉笔记、技术宣言、思维转变 | ink-notes |
| 叙事、个人、情感 | warm / watercolor |
| 历史、怀旧、复古 | vintage / retro |
| 奇幻、童话 | fantasy-animation |
| 环保、健康、慢生活 | nature |
| 游戏、极客 | pixel-art |
| 海报、社论、戏剧 | screen-print |

## Auto Palette Selection（仅 custom 模式参考）

> **固定约束**：cover 和 illustrate 模式 palette 全局锁 `warm`（见 SKILL.md 规则 #14）——**不查此表**。本表仅对 custom 模式或其他未固定 palette 的场景生效。

| Signals | Palette |
|---------|---------|
| Personal story, emotion, lifestyle, human | `warm` |
| Business, professional, thought leadership, luxury | `elegant` |
| Architecture, system, API, technical, code | `cool` |
| Entertainment, premium, cinematic, dark mode | `dark` |
| Nature, wellness, eco, organic, travel | `earth` |
| Product launch, gaming, promotion, event | `vivid` |
| Fantasy, children, gentle, creative, whimsical | `pastel` |
| Zen, focus, essential, pure, simple | `mono` |
| History, vintage, retro, classic, exploration | `retro` |
| Movie poster, album cover, concert, cinematic, dramatic, two-color | `duotone` |
| Education, tutorial, knowledge, onboarding, concept explainer | `macaron` |
