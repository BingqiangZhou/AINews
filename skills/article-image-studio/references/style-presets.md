# Presets Reference

统一的预设别名系统——每个 preset 都展开到**三维**（Type + Style + Palette），用户只需记一个 `--preset` 命令。`--style` 是独立参数（控制 Style 维度），与 `--preset` 并列。

> **三维法**：所有 preset 展开为 `type + style + palette`。palette 在 cover/illustrate 模式被全局 warm 锁覆盖（见 SKILL.md「关键规则 #14」），本表 palette 列仅对 custom 模式或未来解锁时生效。Rendering 从 style 派生（查 [style-rendering-mapping.md](style-rendering-mapping.md)），Text/Font 从 type 派生（查 [visual-preset-mapping.md](visual-preset-mapping.md)「Type→Text/Font」表）。

---

## 预设速查（按使用频率排序）

### 默认预设

**`hand-drawn-edu`** —— 无强内容信号时的安全选择（illustrate 模式默认）。温暖手绘教育信息图，对多数文章都适用。展开：`infographic + sketch-notes + macaron`（macaron 被 warm 锁覆盖）。

### 中文别名预设（ai-news-digest 集成专用）

> ⚠️ **不可删除/改名**——ai-news-digest 的 `visual_preset` 自动映射依赖它们。

| 别名 | 等价于 | Type | Style | Palette | visual_preset 来源 |
|---|---|---|---|---|---|
| `knowledge` | `hand-drawn-edu` | infographic | sketch-notes | macaron | knowledge-card → knowledge |
| `narrative` | `storytelling` | scene | warm | warm | cozy-story → narrative |
| `analysis` | `ink-notes-framework` | framework | ink-notes | mono-ink | bold-warning → analysis, minimal-opinion → analysis |
| `timeline` | `history` | timeline | elegant | — | 无直接映射 |

> 注：Palette 列全部在实际生成时被 warm 锁覆盖；mono-ink/macaron 等历史命名仅作 custom 模式参考。

---

## 完整预设表（按类别，三维展开）

### Technical & Engineering（技术工程）

| --preset | Type | Style | Palette | 适用 |
|---|---|---|---|---|
| `tech-explainer` | infographic | blueprint | cool | API 文档、系统指标、技术深潜 |
| `system-design` | framework | blueprint | cool | 架构图、系统设计 |
| `architecture` | framework | vector-illustration | mono | 组件关系、模块结构 |
| `science-paper` | infographic | scientific | cool | 研究发现、实验结果、学术 |
| `blueprint` | infographic | blueprint | cool | 蓝图风技术图（原 --style blueprint） |

### Knowledge & Education（知识教育）

| --preset | Type | Style | Palette | 适用 |
|---|---|---|---|---|
| `knowledge-base` | infographic | vector-illustration | retro | 概念解说、教程、how-to |
| `saas-guide` | infographic | notion | mono | 产品指南、SaaS 文档、工具演示 |
| `notion` | infographic | notion | mono | Notion 极简风（原 --style notion） |
| `tutorial` | flowchart | vector-illustration | retro | 分步教程、安装指南 |
| `process-flow` | flowchart | notion | mono | 工作流文档、入门流程 |
| `warm-knowledge` | infographic | vector-illustration | warm | 产品展示、团队介绍、品牌内容 |
| `edu-visual` | infographic | vector-illustration | macaron | 知识总结、概念解说、教育文章 |
| `hand-drawn-edu` | infographic | sketch-notes | macaron | **默认 preset**。手绘教育信息图 |
| `sketch-notes` | infographic | sketch-notes | macaron | 同 hand-drawn-edu（原 --style sketch-notes） |
| `hand-drawn-edu-flow` | flowchart | sketch-notes | macaron | 手绘流程解说 |
| `hand-drawn-edu-compare` | comparison | sketch-notes | macaron | 手绘并排对比 |
| `ink-notes-compare` | comparison | ink-notes | mono-ink | 前后对比、传统 vs 新、思维转变 |
| `ink-notes-flow` | flowchart | ink-notes | mono-ink | 专业流程解说、技术走查 |
| `ink-notes-framework` | framework | ink-notes | mono-ink | 系统类比、架构隐喻、技术宣言 |
| `ink-notes` | framework | ink-notes | mono-ink | 同 ink-notes-framework（原 --style） |
| `chalkboard-class` | infographic | chalkboard | dark | 课堂教学、工作坊、知识传授 |
| `chalkboard` | infographic | chalkboard | dark | 同 chalkboard-class（原 --style） |

### Data & Analysis（数据分析）

| --preset | Type | Style | Palette | 适用 |
|---|---|---|---|---|
| `data-report` | infographic | editorial | cool | 数据新闻、指标报告、仪表盘 |
| `editorial` | infographic | editorial | cool | 杂志级编辑信息图（原 --style） |
| `editorial-infographic` | infographic | editorial | cool | 同 editorial |
| `versus` | comparison | vector-illustration | retro | 技术对比、框架对决 |
| `business-compare` | comparison | elegant | elegant | 产品评测、战略选项 |

### Narrative & Creative（叙事创意）

| --preset | Type | Style | Palette | 适用 |
|---|---|---|---|---|
| `storytelling` | scene | warm | warm | 个人随笔、反思、成长故事 |
| `warm` | scene | warm | warm | 同 storytelling（原 --style warm） |
| `lifestyle` | scene | watercolor | earth | 旅行、健康、生活、创意 |
| `watercolor` | scene | watercolor | earth | 水彩风（原 --style watercolor） |
| `history` | timeline | elegant | elegant | 历史综述、里程碑 |
| `evolution` | timeline | warm | warm | 进步叙事、成长旅程 |
| `fantasy` | scene | fantasy-animation | pastel | 奇幻故事、魔法、家庭友好 |
| `fantasy-animation` | scene | fantasy-animation | pastel | 同 fantasy（原 --style） |
| `heritage` | timeline | vintage | retro | 历史、传承、古典、博物馆风 |
| `vintage` | timeline | vintage | retro | 同 heritage（原 --style vintage） |

### Editorial & Opinion（社论观点）

| --preset | Type | Style | Palette | 适用 |
|---|---|---|---|---|
| `opinion-piece` | scene | screen-print | retro | 评论、社论、批判文章 |
| `editorial-poster` | comparison | screen-print | retro | 辩论、对立观点 |
| `cinematic` | scene | screen-print | duotone | 戏剧叙事、文化随笔（原 --style） |
| `screen-print` | scene | screen-print | retro | 丝网印刷海报风（原 --style） |
| `poster-art` | scene | screen-print | retro | 海报艺术（原 --style） |
| `mondo` | scene | screen-print | mono | Mondo 海报（原 --style） |
| `art-deco` | scene | screen-print | elegant | 装饰艺术（原 --style） |
| `propaganda` | scene | screen-print | vivid | 宣传海报（原 --style） |

### Niche & Visual（小众场景 + 视觉构图类）

| --preset | Type | Style | Palette | 适用 |
|---|---|---|---|---|
| `retro-game` | infographic | pixel-art | vivid | 游戏、8 位、极客 |
| `pixel-art` | infographic | pixel-art | vivid | 同 retro-game（原 --style） |
| `retro-pop` | scene | retro | retro | 80/90 年代、流行文化、赛博 |
| `retro` | scene | retro | retro | 同 retro-pop（原 --style） |
| `brainstorm` | framework | sketch | mono | 头脑风暴、创意探索、草稿 |
| `sketch` | framework | sketch | mono | 同 brainstorm（原 --style） |
| `nature-wellness` | scene | nature | earth | 环保、健康、慢生活 |
| `nature` | scene | nature | earth | 同 nature-wellness（原 --style） |
| `minimal-zen` | infographic | minimal | mono | 哲学、极简、核心概念 |
| `minimal` | infographic | minimal | mono | 同 minimal-zen（原 --style） |
| `intuition-machine` | infographic | intuition-machine | retro | 仿旧纸张双语技术简报（原 --style） |
| `flat-doodle` | infographic | flat-doodle | pastel | 圆润粗轮廓可爱涂鸦（原 --style） |
| `flat` | infographic | flat | vivid | 现代几何扁平矢量（原 --style） |
| `vector-illustration` | infographic | vector-illustration | retro | 干净黑轮廓扁平矢量（原 --style） |
| `warm-flat` | infographic | vector-illustration | warm | 暖色扁平矢量（原 --style） |
| `elegant` | comparison | elegant | elegant | 精致优雅（原 --style） |
| `playful` | scene | playful | pastel | 奇思妙想粉彩趣味（原 --style） |
| `dark-atmospheric` | hero | digital | dark | 深色氛围封面（原 --style） |
| `scientific` | infographic | scientific | cool | 学术精确示意图（原 --style） |

---

## Mood 派生说明

Mood 不作为 preset 的展开维度（默认 balanced，不暴露）。原 Mood 分配逻辑（教程/知识→balanced、评论/对比→bold、反思/叙事→subtle）保留为参考，未来如需细分可作为派生规则实现。

---

## Content Type → Preset 推荐表

illustrate 模式 Step 3 推荐时用此表（基于 Step 2 内容分析）：

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

## Convenience Presets for ai-news-digest

ai-news-digest 的 `visual_preset`（`knowledge-card` / `cozy-story` / `bold-warning` / `minimal-opinion`）到三维的映射分两张表（Cover / Illustrate），详见 [visual-preset-mapping.md](visual-preset-mapping.md)。本文件的 `knowledge`/`narrative`/`analysis`/`timeline` 四个别名是这些 visual_preset 的 illustrate 模式等价物。

---

## Override 示例

### 单维覆盖（Style）

```
--preset tech-explainer --style notion
```
Result: infographic type + notion style（覆盖原 blueprint style），palette 被 warm 锁覆盖。

### Type 覆盖（Text/Font 自动调整）

```
--preset storytelling --type timeline
```
Result: timeline type + warm style，text/font 自动按 timeline 的 title-subtitle/handwritten 调整（查 [visual-preset-mapping.md](visual-preset-mapping.md#三type-textfont-默认值cover-和-illustrate-共用11-值-type)）。

### Style 独立指定

```
--style ink-notes
```
Result: 不依赖 preset，直接指定 ink-notes style。Type 由 auto-selection 按内容推荐，rendering 派生为 chalk，palette=warm。

### Palette 覆盖（无效）

```
--preset hand-drawn-edu --palette warm
```
Result: palette 全局锁 warm，--palette 参数被忽略。

### 完整三维显式（跳过 preset）

```
--type infographic --style sketch-notes
```
Result: 等价于 `--preset hand-drawn-edu`（palette 无条件 warm）。

---

## `--style` 独立参数

`--style` 是独立参数。Style 是三维法的核心维度之一，直接控制渲染技法（派生 Rendering）和视觉语言细节（写 prompt 正文）。

23 个合法 style 名见 [styles.md](styles.md) 索引或 [style-rendering-mapping.md](style-rendering-mapping.md) 主表。

显式 `--type` / `--style` 标志**总是覆盖** preset 的对应维度。`--palette` 被 warm 锁覆盖（无效）。Rendering/Text/Font/Mood 不是用户参数，不接受 `--rendering` 等标志。
