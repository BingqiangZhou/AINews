# Style → Cover 维度映射（单一来源）

> **用途**：article-illustrator 的 `style` 是用户友好别名，最终生成时要委托给 `article-cover-image-generator`（6 维模型）。本文件是 **style → (rendering, palette) 的唯一权威映射**，`agents/illustrator.md` 和 `references/workflow.md` 必须读本文件查表，不得内联硬编码映射。
>
> **设计原则**：
> 1. 命名尽量与 `article-cover-image-generator/references/style-presets.md` 的 26 个 `style_preset` 对齐（同名时直接复用其 palette+rendering）。
> 2. `rendering` 是"渲染技法"粗分（cover 仅 7 值），style 的精细视觉差异由各 style 文件（`styles/<name>.md` 的 Visual Elements / Style Rules，部分另含 Layout Guidelines）承载并写入 prompt 正文。
> 3. `palette` 列是 **默认色板**，可被用户 `--palette` 或 preset 显式覆盖。cover 的 `--palette` 优先级 > 本表默认值。
> 4. article-illustrator 自有的 4 个色板（macaron/warm/mono-ink/neon）与 cover 的 11 个色板对应关系见文末「色板兼容」段。

---

## 映射主表（23 个 style）

| article_style | cover rendering | cover palette（默认） | 对齐的 cover style_preset | 备注 |
|---|---|---|---|---|
| `sketch-notes` | `hand-drawn` | `macaron` | `sketch-notes` / `hand-drawn-edu` | **默认主推**；暖色奶油纸+黑线+马卡龙色块 |
| `vector-illustration` | `flat-vector` | `retro` | `vector-illustration` | 干净黑轮廓+复古柔色扁平矢量 |
| `notion` | `digital` | `mono` | `notion` | 极简手绘线稿，类 Notion 美学 |
| `elegant` | `hand-drawn` | `elegant` | `elegant` | 精致优雅，商务感 |
| `warm` | `hand-drawn` | `warm` | `warm` | 友好暖色调，金色光线 |
| `minimal` | `flat-vector` | `mono` | `minimal` | 极致干净的禅意极简 |
| `blueprint` | `digital` | `cool` | `blueprint` | 蓝色工程图纸，技术精确感 |
| `watercolor` | `painterly` | `earth` | `watercolor` | 柔和水彩晕染，可见笔触 |
| `editorial` | `digital` | `cool` | `editorial-infographic` | 杂志级编辑信息图 |
| `scientific` | `digital` | `cool` | —（无完全对应，借用 blueprint 的 digital+cool） | 学术精确示意图 |
| `chalkboard` | `chalk` | `dark` | `chalkboard` | 黑板粉笔手绘，教室板书 |
| `fantasy-animation` | `painterly` | `pastel` | `fantasy-animation` | 吉卜力/迪士尼奇幻手绘 |
| `flat` | `flat-vector` | `vivid` | —（无对应，用 flat-vector 渲染+vivid 色板） | 现代几何扁平矢量 |
| `flat-doodle` | `flat-vector` | `pastel` | `flat-doodle` | 圆润粗轮廓可爱扁平涂鸦 |
| `intuition-machine` | `digital` | `retro` | `intuition-machine` | 仿旧纸张双语技术简报 |
| `nature` | `hand-drawn` | `earth` | `nature` | 大地色系有机插画 |
| `pixel-art` | `pixel` | `vivid` | `pixel-art` | 8 位像素游戏美学 |
| `playful` | `hand-drawn` | `pastel` | `playful` | 奇思妙想粉彩趣味涂鸦 |
| `retro` | `digital` | `retro` | `retro` | 80/90 年代霓虹几何复古 |
| `sketch` | `hand-drawn` | `mono` | —（无对应，借用 sketch-notes 的 hand-drawn，色板用 mono 更素净） | 原始笔记本铅笔素描 |
| `screen-print` | `screen-print` | `retro` | `poster-art` / `mondo` | 丝网印刷海报艺术（cover 有多个变体，默认用 poster-art 的 retro 配色） |
| `ink-notes` | `chalk` | `mono` | —（无对应；ink-notes 是黑墨白底，cover 的 `chalk` rendering 最接近"干性笔触"，色板用 mono 表达黑白主调） | 专业黑墨视觉笔记，Mike Rohde 风格 |
| `vintage` | `hand-drawn` | `retro` | `vintage` | 仿旧羊皮纸历史感 |

---

## 查表规则（agent 执行 Step 5 时遵循）

1. 从 outline.md 的某张图读取 `style` 字段（如 `ink-notes`）。
2. 在本表查到 `(rendering=chalk, palette=mono)`。
3. 若该图 outline 指定了 `palette`（用户覆盖或 preset 指定），**以 outline 的 palette 为准**，忽略本表的默认 palette。
4. 将 `rendering` 和最终 `palette` 传入 `article-cover-image-generator` 的 `dimensions`。
5. `text` 和 `font` 维度**不读本表**——查 `../../article-cover-image-generator/references/visual-preset-mapping.md` 的「Illustration Profile Text/Font Override」段（按 illustration_type 查）。
6. `type` 和 `mood` 维度由 cover 的 auto-selection 规则解析，或由 preset/visual_preset 指定。

### 维度传递示例

outline 里某张图：`type: framework, style: ink-notes, palette: mono-ink`

查本表：`ink-notes → rendering=chalk, palette(default)=mono`
查 Text/Font 表（cover）：`framework → text=text-rich, font=handwritten`

最终传给 cover 的 dimensions：
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

> 注：illustration_type（infographic/scene/flowchart/comparison/framework/timeline）与 cover 的 type（hero/conceptual/typography/metaphor/scene/minimal）是两套枚举。illustration_type 主要用于查 Text/Font 表；cover 的 `type` 维度建议设为 `conceptual`（信息图类）或 `scene`（场景类），其余由 auto 解析。

---

## 色板兼容（article-illustrator ↔ article-cover-image-generator）

article-illustrator 用户面对的是 **4 个色板**（macaron/warm/mono-ink/neon，定义在 `palettes.md`），cover 支持更细的 **11 个色板**。映射关系：

| article palette | cover palette | 说明 |
|---|---|---|
| `macaron` | `macaron` | 直接对应（cover 也有 macaron） |
| `warm` | `warm` | 直接对应 |
| `mono-ink` | `mono` | article 的 mono-ink（黑墨+语义点缀）→ cover 的 mono（单色） |
| `neon` | `vivid` | article 的 neon（霓虹高饱和）→ cover 的 vivid（鲜艳）最接近 |

当 style 的默认 palette（本表第二列）与用户指定的 article palette 冲突时，**用户 palette 优先**，并按上表转成 cover palette 传入。

---

## 维护说明

- **新增 style**：在 `styles/<new>.md` 建文件 → 在本表加一行映射 → 在 `styles.md` 的 Style Gallery 和兼容矩阵补条目。
- **改名**：先确认 article-cover-image-generator 是否有同名 style_preset，尽量对齐避免分叉。
- **本表是唯一来源**：`agents/illustrator.md`、`workflow.md`、`SKILL.md` 不得内联 style→rendering 映射，统一引本文件。
