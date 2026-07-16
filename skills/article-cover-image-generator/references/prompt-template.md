# Prompt Template（结构化槽位）

Step 4「Prompt 构建」的统一骨架。取代"LLM 自由发挥 20-40 词"的不确定性，用固定槽位保证 prompt 质量、一致性与可复现性。

---

## 槽位结构

完整 visual prompt 由 6 个槽位按顺序拼接（每个槽位 3-8 词，整段 20-40 词）：

```
{target_label}，{target_size_desc}。{Subject} {Setting} {Lighting} {Style words} {Mood} {Composition}
```

| 槽位 | 作用 | 来源维度 | 示例词 |
|------|------|---------|--------|
| **Subject** | 画面的主体/焦点 | type + content | `a single glowing lightbulb` / `layered abstract geometric shapes` |
| **Setting** | 主体所处的环境/背景 | type + palette(background) | `on a soft cream background` / `against deep navy gradient` |
| **Lighting** | 光照氛围 | mood | `soft diffused light` / `dramatic high-contrast lighting` |
| **Style words** | 渲染技法/插画风格 | rendering | `flat vector illustration, clean solid fills` / `loose watercolor washes, visible brush texture` |
| **Mood** | 情绪强度修饰 | mood | `understated and calm` / `bold and energetic` |
| **Composition** | 构图布局指令 | type | `centered focal element, generous negative space` / `dynamic asymmetrical balance, layered depth` |

---

## 颜色规则（硬约束，再强调）

- prompt 正文**只用描述性颜色名**：`warm orange` / `cream background` / `暖米白` / `橄榄绿`
- **禁止 hex 色值**：AI 图像模型会把 `#ED8936` 当成需要渲染进图的文字
- hex 仅写入 prompt 文件的 YAML frontmatter 作为元数据

详见 [palette-colors.md](palette-colors.md) 末尾的语义约束。

---

## 完整示例

### 示例 1：hero + cool + flat-vector（科技产品发布封面）

```
WeChat公众号封面图，尺寸900x383像素，宽幅横版banner比例约2.35:1。
A sleek geometric monolith floating above a layered horizon line, set against a light gray to off-white gradient background, under crisp even lighting, flat vector illustration with clean solid fills and sharp edges, balanced and professional, large focal visual occupying two-thirds of the frame with strong negative space on the right for title overlay.
```

YAML frontmatter：
```yaml
---
type: hero
palette: cool
rendering: flat-vector
text: none
mood: balanced
font: clean
target_size: 900x383
palette_colors:
  primary: "#2563EB"
  background: "#F8F9FA"
  accent: "#F59E0B"
---
```

### 示例 2：scene + warm + painterly（生活故事插图）

```
文章插图，尺寸1920x1080像素，16:9宽幅横版比例。
一个人坐在窗边读书的剪影，窗外是温暖的金色午后光线，背景是柔和的奶油色与桃色渐变水彩晕染，沐浴在柔和漫射的暖光中，松散的水彩笔触带着可见的纹理与色彩晕开，静谧温柔而富有叙事感，氛围式环境构图，主体偏左三分之一处，右侧留白呼应光线。
```

### 示例 3：conceptual + mono + digital（极简概念图）

```
WeChat公众号封面图，尺寸900x383像素，宽幅横版banner比例约2.35:1。
A single abstract network of interconnected nodes rendered as precise geometric forms, on a pure white background, under neutral flat lighting, polished digital illustration with smooth gradients and professional finish, understated and focused, centered focal element with generous whitespace reinforcing essential simplicity.
```

---

## 当 `text != none` 时

若 `text` 维度非 `none`（title-only / title-subtitle / text-rich），在 Composition 槽位后追加文字布局指令：

- **title-only**：`title "{文章标题}" rendered in {font} typography, positioned {position}`
- **title-subtitle**：`title "{标题}" with subtitle "{副标题}" below, in {font} typography`
- **text-rich**：`multiple labels and tags ({具体标签词}) distributed across the composition in {font} typography`

> **图内文字契约**：后端（Gaoding 万相2.7）只消费 prompt 正文。要画的具体中文必须写进正文，不能只放在 YAML frontmatter。详见编排器的插图 prompt 规范的「图内文字契约」一节。

---

## 反模式（禁止）

- ❌ 只写抽象描述不写主体：`a modern cover about technology`（没有 Subject）
- ❌ hex 进正文：`background color #F8F9FA`（会被误渲染为文字）
- ❌ 风格词与 rendering 维度矛盾：rendering=hand-drawn 却写 `smooth gradients, precise shapes`
- ❌ 把维度标签当文字：`palette: cool, mood: balanced`（标签不是视觉描述）
- ❌ 占位符不替换：`title "{标题}"`（提交前必须替换为真实文字）
