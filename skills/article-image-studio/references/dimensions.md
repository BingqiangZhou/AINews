# Image Studio Dimensions Reference

三维方法论的完整定义：**Type × Style × Palette**（用户维度）+ 派生维度（Rendering/Text/Font/Mood，由 Type/Style 派生，不暴露给用户）。cover 与 illustrate 模式统一用三维法，Palette 全局锁 warm。

---

## Type（11 值）

定义整体构图方法。**唯一 Type 枚举**——视觉构图类（cover 场景为主）+ 信息结构类（illustrate 场景为主）+ 场景类，合并自原 cover 的 6 值与原 illustrator 的 illustration_type 5 值。cover 与 illustrate 共用此 11 值，auto-selection 按 mode 分流推荐。

### 视觉构图类（cover 场景为主）

> 这 5 个 Type 主要用于 cover 模式的封面（单图、氛围/概念导向）。illustrate 模式极少触发，但允许使用（如文章需要一张氛围开场图可选 hero/scene）。**illustrate 模式禁用 `conceptual`**（见该 Type 说明）——插图需要具体信息结构，应走信息结构类（infographic/framework 等）。


#### `hero`
大视觉冲击，标题压图。

- **Best for:** 产品发布、品牌宣传、重大公告
- **Composition:** 大焦点视觉（占 60-70% 面积），标题压在视觉上，戏剧化
- **Prompt cues:** `large focal visual, dramatic centerpiece, title overlay area, bold subject`
- **派生 Text/Font:** `none` / `clean`（见 [visual-preset-mapping.md](visual-preset-mapping.md)）
- **推荐 Style:** screen-print / watercolor / fantasy-animation（戏剧化渲染）
- **Anti-patterns:** ❌ 密集小元素堆砌（失去焦点）；❌ 焦点视觉小于画面 40%

#### `conceptual`
概念可视化，抽象表达核心（**cover 专用**）。

- **Best for:** 封面的抽象概念图——标题压图但有概念层级，比 hero 安静，比 typography 视觉化
- **Composition:** 抽象图形表达核心概念，信息层级，干净分区，留白均衡
- **Prompt cues:** `abstract geometric shapes, information hierarchy, balanced negative space, layered concepts`
- **派生 Text/Font:** `none` / `clean`
- **推荐 Style:** sketch-notes / vector-illustration / minimal / blueprint
- **Anti-patterns:** ❌ 具象写实场景（应抽象化）；❌ 单一焦点（应是层级结构）
- **⚠ illustrate 模式禁用**：插图需要具体信息结构（数据/步骤/节点/事件），不应使用 conceptual。若内容是"纯概念、无具体数据"的插图，改用 `infographic`（它涵盖概念解说 + 知识总结）。conceptual 仅在 cover 模式作为"封面抽象概念图"使用，避免与 infographic 边界模糊。

#### `typography`
文字主导，标题为主体。

- **Best for:** 观点、引言、洞见
- **Composition:** 标题为首要元素（占 40%+ 面积），极简辅助视觉，强层级
- **Prompt cues:** `prominent title typography, minimal supporting visuals, strong typographic hierarchy`
- **派生 Text/Font:** `title-only` / `display`
- **推荐 Style:** editorial / screen-print / elegant
- **Anti-patterns:** ❌ text: none（无字则失去意义）；❌ 标题字号过小（应 ≥ 画面高度 1/6）

#### `metaphor`
视觉隐喻，具象表达抽象。

- **Best for:** 哲学、成长、个人发展
- **Composition:** 具象物/场景代表抽象概念，象征性元素，情感共鸣
- **Prompt cues:** `symbolic object, metaphorical scene, concrete representing abstract, emotional resonance`
- **派生 Text/Font:** `none` / `handwritten`
- **推荐 Style:** warm / watercolor / fantasy-animation / screen-print
- **Anti-patterns:** ❌ text-rich（隐喻靠图像，文字宜少）；❌ 直白图解（应留想象空间）

#### `minimal`
极简构图，大量留白。

- **Best for:** 禅意、聚焦、核心概念
- **Composition:** 单一焦点元素，大量留白（60%+），仅保留本质形状
- **Prompt cues:** `single focal element, generous whitespace, essential shapes only, refined simplicity`
- **派生 Text/Font:** `none` / `clean`
- **推荐 Style:** minimal / vector-illustration / flat / notion
- **Anti-patterns:** ❌ 密集细节/装饰（违背极简）；❌ text-rich

### 信息结构类（illustrate 场景为主）

> 这 5 个 Type 源自原 illustrator 的 illustration_type，现已纳入权威 Type 枚举。它们都**需要图内中文文字**（标签/步骤名/数据/节点名），Text/Font 按 [visual-preset-mapping.md](visual-preset-mapping.md) 的「Type → Text/Font 默认值」表派生。
>
> **图内文字语言由 prompt 正文决定**（prompt-construction.md 要求 labels/title_text 写文章真实中文词）。Prompt cues 只描述视觉结构，不重复语言提示——避免中英混合 prompt 降低模型响应稳定性。

#### `infographic`
信息图——数据/知识/指标的可视化。

- **Best for:** 知识总结、概念解说、数据展示、教程要点、清单
- **Composition:** 标题 + 多个分区/卡片/图标 + 标签说明，信息层级清晰，留白充足
- **Prompt cues:** `infographic layout, labeled icon cards, clear information hierarchy, data visualization, generous whitespace`
- **派生 Text/Font:** `text-rich` / `handwritten`
- **推荐 Style:** sketch-notes / vector-illustration / notion / blueprint / editorial
- **Anti-patterns:** ❌ 无中文标签（infographic 必须有具体词作标签）；❌ 密集堆砌无留白；❌ 占位符（labels 必须是文章真实词）

#### `flowchart`
流程图——步骤/工作流/决策树。

- **Best for:** 教程步骤、工作流文档、决策流程、安装指南
- **Composition:** 节点（步骤框）+ 箭头（流向）+ 判断分支，从上到下或从左到右线性排布
- **Prompt cues:** `flowchart with connected nodes, arrows showing flow direction, decision branches, step labels, top-down or left-right layout`
- **派生 Text/Font:** `text-rich` / `handwritten`
- **推荐 Style:** sketch-notes / ink-notes / vector-illustration / notion
- **Anti-patterns:** ❌ 无箭头（流程图必须有方向指示）；❌ 步骤名用占位符；❌ 循环混乱（应有清晰起点终点）

#### `comparison`
对比图——左右/前后/优劣对比。

- **Best for:** 产品评测、方案对比、前后转变、优劣分析
- **Composition:** 左右（或上下）对称两栏，各有标题 + 要点列表，中间分隔线/对比符号
- **Prompt cues:** `side-by-side comparison layout, two columns with contrasting items, versus composition, labeled pros and cons`
- **派生 Text/Font:** `title-subtitle` / `handwritten`
- **推荐 Style:** ink-notes / vector-illustration / elegant
- **Anti-patterns:** ❌ 两栏不对称失衡；❌ 只有一方无对比；❌ 标题用占位符

#### `framework`
框架图——系统/架构/概念节点关系。

- **Best for:** 系统设计、架构图、概念模型、思维框架、类比映射
- **Composition:** 多个节点（概念框）+ 连接线（关系），中心-辐射或网状结构，节点带标签
- **Prompt cues:** `framework diagram with connected concept nodes, relational structure, hub-spoke or network layout, labeled nodes`
- **派生 Text/Font:** `text-rich` / `handwritten`
- **推荐 Style:** ink-notes / blueprint / vector-illustration
- **Anti-patterns:** ❌ 节点无连接（framework 必须有关系线）；❌ 节点名占位符；❌ 与 flowchart 混淆（framework 是关系，flowchart 是顺序）

#### `timeline`
时间线——演进/里程碑/事件序列。

- **Best for:** 历史综述、发展脉络、成长旅程、项目里程碑、演进历程
- **Composition:** 线性时间轴（水平或垂直）+ 事件节点 + 时间标签 + 事件描述，按时间顺序排布
- **Prompt cues:** `timeline with sequential event nodes, chronological axis, time labels and event descriptions, milestone markers`
- **派生 Text/Font:** `title-subtitle` / `handwritten`
- **推荐 Style:** elegant / sketch-notes / warm / vintage
- **Anti-patterns:** ❌ 无时间标签（timeline 必须有时间维度）；❌ 事件无序；❌ 事件名占位符

### 场景类

#### `scene`
氛围场景，叙事感。

- **Best for:** 故事、旅行、生活方式、个人随笔、反思
- **Composition:** 氛围环境，叙事元素，定调光照与色彩
- **Prompt cues:** `atmospheric environment, narrative elements, mood-setting lighting, environmental storytelling`
- **派生 Text/Font:** `title-only` / `handwritten`
- **推荐 Style:** warm / watercolor / elegant / fantasy-animation（避免 flat-vector 类）
- **Anti-patterns:** ❌ flat-vector 扁平化（破坏氛围）；❌ text-rich（场景靠画面叙事，文字宜少，默认 title-only 或 none）
- **特殊:** scene 是唯一不需要图内标签的 Type（以氛围为主），labels/title_text 可省

---

## Style（23 值）

定义渲染方式 / 插画风格。Style 是运行时维度。

**核心作用**：
1. **派生 Rendering**：查 [style-rendering-mapping.md](style-rendering-mapping.md) 得到 rendering（7 值渲染技法粗分）
2. **提供视觉语言细节**：`styles/<name>.md` 的 Visual Elements / Style Rules / 部分含 Layout Guidelines 段——这些细节在 Step 4 拼 prompt 时写入正文（线条质感、版式、装饰元素）

23 个 Style：`sketch-notes, vector-illustration, notion, elegant, warm, minimal, blueprint, watercolor, editorial, scientific, chalkboard, fantasy-animation, flat, flat-doodle, intuition-machine, nature, pixel-art, playful, retro, sketch, screen-print, ink-notes, vintage`

**默认 Style**：`sketch-notes`（派生 hand-drawn rendering，暖奶油纸 + 黑手绘线视觉语言）。

→ 每个 style 的完整定义见 [styles.md](styles.md) 索引 + `styles/<name>.md` 单文件
→ Style → Rendering 映射见 [style-rendering-mapping.md](style-rendering-mapping.md)
→ Type → Style 推荐见 [auto-selection-rules.md](auto-selection-rules.md)

---

## Palette（锁 warm）

cover 与 illustrate 模式 **palette 全局锁 `warm`**（见 SKILL.md「关键规则：Palette 全局锁 warm」）。所有 preset 和 style 自带的 palette-default 在实际生成时被无条件覆盖为 warm。

11 色板定义保留作参考（custom 模式或未来解锁时可用），完整 hex 见 [palette-colors.md](palette-colors.md)。

---

## 派生维度（不暴露给用户）

以下维度由 Type 或 Style 派生，**不是用户参数**，不进入优先级链，也不在 config.json 暴露默认值字段。

### Rendering（从 Style 派生）

7 值渲染技法粗分：`flat-vector / hand-drawn / painterly / digital / pixel / chalk / screen-print`。

派生规则：查 [style-rendering-mapping.md](style-rendering-mapping.md)（23 行映射，单一来源）。例：
- `sketch-notes → hand-drawn`
- `ink-notes → chalk`
- `blueprint → digital`
- `watercolor → painterly`
- `pixel-art → pixel`
- `screen-print → screen-print`

Rendering 派生后传给 image-generator 的 dimensions，控制实际渲染技法。详细的 Rendering prompt cues（如 hand-drawn → "varied line weight, visible stroke texture"）由 image-generator 内部使用，本文件不再展开。

### Text（从 Type 派生）

4 值图内文字量：`none / title-only / title-subtitle / text-rich`。

派生规则：查 [visual-preset-mapping.md](visual-preset-mapping.md) 的「Type → Text/Font 默认值」表（11 行权威源）。例：`hero → none`、`infographic → text-rich`、`scene → title-only`。

### Font（从 Type 派生）

4 值字体人格：`clean / handwritten / serif / display`。

派生规则：同 Text，查同一张表。例：`hero → clean`、`typography → display`、其余 9 个 Type → `handwritten`。

### Mood（默认 balanced，不暴露）

3 值情绪强度：`subtle / balanced / bold`。

不暴露为维度，默认 `balanced`。若未来需要按内容基调细分，可从 preset 或 auto-selection 派生（当前未实现）。
