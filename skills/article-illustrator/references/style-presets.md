# Style Presets

`--preset X` 展开为 type + style + 可选 palette 的组合。用户可用 `--type`/`--style`/`--palette` 覆盖任意维度。

---

## 默认 Preset

当 Step 2 内容分析无明显信号（通用知识文章、混合主题、无明确数据/对比/叙事线索）时，推荐 **`hand-drawn-edu`** 作为 Step 3 Q1 的首选。它是温暖友好的教育信息图默认值，对多数文章都安全可读。

---

## 中文别名 Preset（向后兼容）

> ⚠️ **重要**：这 4 个是编排器集成的兼容别名，**不可删除/改名**。编排器的 `visual_preset` 自动映射依赖它们。

| 别名 Preset | 等价于 | Type | Style | Palette | visual_preset 映射来源 |
|---|---|---|---|---|---|
| `knowledge` | `hand-drawn-edu` | infographic | sketch-notes | macaron | knowledge-card → knowledge |
| `narrative` | `storytelling` | scene | warm | warm | cozy-story → narrative |
| `analysis` | `ink-notes-framework` | framework | ink-notes | mono-ink | bold-warning → analysis, minimal-opinion → analysis |
| `timeline` | `history` | timeline | elegant | — | 无直接映射，需用户指定或从内容推断 |

> 注：原 `narrative` 用 watercolor+warm，现统一为 `warm` style（与 baoyu `storytelling` 对齐，warm 也是水彩质感的友好暖色风格，且与 cover 的 `warm` style_preset 命名一致）。若需严格水彩，用 `--preset storytelling`。

---

## 全部 Preset（按类别）

### Technical & Engineering（技术工程）

| --preset | Type | Style | Palette | 适用 |
|---|---|---|---|---|
| `tech-explainer` | infographic | blueprint | — | API 文档、系统指标、技术深潜 |
| `system-design` | framework | blueprint | — | 架构图、系统设计 |
| `architecture` | framework | vector-illustration | — | 组件关系、模块结构 |
| `science-paper` | infographic | scientific | — | 研究发现、实验结果、学术 |

### Knowledge & Education（知识教育）

| --preset | Type | Style | Palette | 适用 |
|---|---|---|---|---|
| `knowledge-base` | infographic | vector-illustration | — | 概念解说、教程、how-to |
| `saas-guide` | infographic | notion | — | 产品指南、SaaS 文档、工具演示 |
| `tutorial` | flowchart | vector-illustration | — | 分步教程、安装指南 |
| `process-flow` | flowchart | notion | — | 工作流文档、入门流程 |
| `warm-knowledge` | infographic | vector-illustration | warm | 产品展示、团队介绍、品牌内容 |
| `edu-visual` | infographic | vector-illustration | macaron | 知识总结、概念解说、教育文章 |
| `hand-drawn-edu` | infographic | sketch-notes | macaron | **默认 preset**。手绘教育信息图——暖奶油纸+黑线+马卡龙色块。单页解说、概念总结、入门、通用知识 |
| `hand-drawn-edu-flow` | flowchart | sketch-notes | macaron | 手绘流程解说——同温暖教育风格的分步工作流 |
| `hand-drawn-edu-compare` | comparison | sketch-notes | macaron | 手绘并排对比——温暖教育风格 |
| `ink-notes-compare` | comparison | ink-notes | mono-ink | 前后对比、传统 vs 新、思维转变叙事 |
| `ink-notes-flow` | flowchart | ink-notes | mono-ink | 专业流程解说、职场流水线、手绘技术走查 |
| `ink-notes-framework` | framework | ink-notes | mono-ink | 系统类比、指挥中心图、架构隐喻、技术宣言 |
| `chalkboard-class` | infographic | chalkboard | — | 课堂教学、工作坊、知识传授 |

### Data & Analysis（数据分析）

| --preset | Type | Style | Palette | 适用 |
|---|---|---|---|---|
| `data-report` | infographic | editorial | — | 数据新闻、指标报告、仪表盘 |
| `versus` | comparison | vector-illustration | — | 技术对比、框架对决 |
| `business-compare` | comparison | elegant | — | 产品评测、战略选项 |

### Narrative & Creative（叙事创意）

| --preset | Type | Style | Palette | 适用 |
|---|---|---|---|---|
| `storytelling` | scene | warm | — | 个人随笔、反思、成长故事 |
| `lifestyle` | scene | watercolor | — | 旅行、健康、生活、创意 |
| `history` | timeline | elegant | — | 历史综述、里程碑 |
| `evolution` | timeline | warm | — | 进步叙事、成长旅程 |
| `fantasy` | scene | fantasy-animation | — | 奇幻故事、魔法、家庭友好叙事 |
| `heritage` | timeline | vintage | — | 历史、传承、古典、博物馆风 |

### Editorial & Opinion（社论观点）

| --preset | Type | Style | Palette | 适用 |
|---|---|---|---|---|
| `opinion-piece` | scene | screen-print | — | 评论、社论、批判文章 |
| `editorial-poster` | comparison | screen-print | — | 辩论、对立观点 |
| `cinematic` | scene | screen-print | — | 戏剧叙事、文化随笔 |

### Niche（小众场景）

| --preset | Type | Style | Palette | 适用 |
|---|---|---|---|---|
| `retro-game` | infographic | pixel-art | — | 游戏、8 位、极客 |
| `retro-pop` | scene | retro | — | 80/90 年代、流行文化、赛博 |
| `brainstorm` | framework | sketch | — | 头脑风暴、创意探索、草稿 |
| `nature-wellness` | scene | nature | — | 环保、健康、慢生活 |
| `minimal-zen` | infographic | minimal | — | 哲学、极简、核心概念 |

---

## Content Type → Preset 推荐表

Step 3 推荐时用此表（基于 Step 2 内容分析）：

| 内容类型（Step 2） | 主推 Preset | 备选 |
|---|---|---|
| **通用 / 无强信号** | `hand-drawn-edu` | `edu-visual`, `knowledge-base` |
| 教育 / 知识 | `hand-drawn-edu` | `edu-visual`, `knowledge-base`, `tutorial` |
| 教程 | `hand-drawn-edu-flow` | `tutorial`, `process-flow`, `hand-drawn-edu` |
| SaaS / 产品 | `hand-drawn-edu` | `saas-guide`, `knowledge-base`, `process-flow`, `warm-knowledge` |
| 技术 | `tech-explainer` | `system-design`, `architecture`, `hand-drawn-edu` |
| 方法论 / 框架 | `system-design` | `architecture`, `process-flow`, `ink-notes-framework` |
| 数据 / 指标 | `data-report` | `versus`, `tech-explainer` |
| 对比 / 评测 | `versus` | `business-compare`, `hand-drawn-edu-compare`, `editorial-poster`, `ink-notes-compare` |
| 宣言 / 思维转变 / 专业视觉笔记 | `ink-notes-compare` | `ink-notes-framework`, `ink-notes-flow` |
| 叙事 / 个人 | `storytelling` | `lifestyle`, `evolution`, `fantasy` |
| 观点 / 社论 | `opinion-piece` | `cinematic`, `editorial-poster` |
| 历史 / 时间线 | `history` | `evolution`, `heritage` |
| 学术 / 研究 | `science-paper` | `tech-explainer`, `data-report` |
| 教学 / 课堂 | `chalkboard-class` | `hand-drawn-edu`, `tutorial` |
| 儿童 / 奇幻 | `fantasy` | `lifestyle` |
| 游戏 / 极客 | `retro-game` | `retro-pop` |
| 怀旧 / 复古 | `retro-pop` | `retro-game`, `heritage` |
| 头脑风暴 / 创意 | `brainstorm` | `minimal-zen` |
| 环保 / 健康 | `nature-wellness` | `lifestyle` |
| 哲学 / 极简 | `minimal-zen` | `knowledge-base` |

混合内容类型时，以文章主旨对应的 preset 为准。

---

## Override 示例

- `--preset tech-explainer --style notion` = infographic type + notion style（palette 用 notion 默认）
- `--preset storytelling --type timeline` = timeline type + warm style
- `--preset hand-drawn-edu --palette warm` = 手绘教育风但换暖色调
- `--preset ink-notes-compare --palette macaron` = 墨线对比风但换马卡龙色（不常用，但允许）

显式 `--type`/`--style`/`--palette` 标志**总是覆盖** preset 值。
