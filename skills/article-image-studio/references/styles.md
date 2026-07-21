# Style 索引（三维法的 Style 维度）

> ✅ **运行时维度**：`style`（23 个）是三维法（Type × Style × Palette）的**核心维度之一**。Style 既**派生 Rendering**（查 [style-rendering-mapping.md](style-rendering-mapping.md)），又**提供视觉语言细节**（从 `styles/<name>.md` 的 Visual Elements / Style Rules 段加载到 prompt 正文）。
>
> **使用方式**：
> - 用户通过 `--style sketch-notes` 直接指定（23 值之一）
> - 或通过 `--preset` 间接指定（preset 展开含 style 列）
> - 或 auto-selection 按 Type 推荐合适 style（见 [auto-selection-rules.md](auto-selection-rules.md) 的 Type→Style 推荐表）
>
> Style 写入 outline.md 和 prompt 文件的 frontmatter（记录用户三维选择）。Palette 全局锁 warm，style 自带的 palette-default 在实际生成时被覆盖。

---

## 23 个 Style（按字母序）

每个 style 的完整定义在 `styles/<name>.md`，标准六段：Design Aesthetic / Background / Color Palette / Visual Elements / Style Rules / Best For。

| Style | 中文一句话 | Best For | 详细定义 | 派生 Rendering | palette-default（被 warm 锁覆盖） |
|---|---|---|---|---|---|
| `sketch-notes` | 暖奶油纸+黑手绘线+马卡龙色块教育信息图 | 教育、知识分享、概念解说 | [styles/sketch-notes.md](styles/sketch-notes.md) | hand-drawn | macaron |
| `vector-illustration` | 干净黑轮廓+复古柔色扁平矢量 | 知识文章、教程、科技 | [styles/vector-illustration.md](styles/vector-illustration.md) | flat-vector | retro |
| `notion` | 极简手绘线稿，类 Notion 美学 | 知识分享、SaaS、生产力 | [styles/notion.md](styles/notion.md) | digital | mono |
| `elegant` | 精致克制的优雅插画 | 商业、思想领袖、战略 | [styles/elegant.md](styles/elegant.md) | hand-drawn | elegant |
| `warm` | 友好亲和的暖色调插画 | 个人成长、生活、教育 | [styles/warm.md](styles/warm.md) | hand-drawn | warm |
| `minimal` | 极致干净的禅意极简 | 哲学、极简主义、核心概念 | [styles/minimal.md](styles/minimal.md) | flat-vector | mono |
| `blueprint` | 蓝色工程图纸，技术精确感 | 架构、系统设计、工程 | [styles/blueprint.md](styles/blueprint.md) | digital | cool |
| `watercolor` | 柔和水彩晕染，可见笔触 | 生活、旅行、创意、情感叙事 | [styles/watercolor.md](styles/watercolor.md) | painterly | earth |
| `editorial` | 杂志级编辑信息图（Wired 风格） | 科技解说、数据新闻 | [styles/editorial.md](styles/editorial.md) | digital | cool |
| `scientific` | 学术精确示意图 | 生物、化学、医学、科研 | [styles/scientific.md](styles/scientific.md) | digital | cool |
| `chalkboard` | 黑板粉笔手绘，教室板书 | 教育、教学、工作坊 | [styles/chalkboard.md](styles/chalkboard.md) | chalk | dark |
| `fantasy-animation` | 吉卜力/迪士尼奇幻手绘 | 故事书、魔法、家庭友好 | [styles/fantasy-animation.md](styles/fantasy-animation.md) | painterly | pastel |
| `flat` | 现代几何扁平矢量 | 现代数字、当代商业 | [styles/flat.md](styles/flat.md) | flat-vector | vivid |
| `flat-doodle` | 圆润粗轮廓可爱扁平涂鸦 | 可爱、友好、亲和 | [styles/flat-doodle.md](styles/flat-doodle.md) | flat-vector | pastel |
| `intuition-machine` | 仿旧纸张双语技术简报 | 技术深度、学术简报 | [styles/intuition-machine.md](styles/intuition-machine.md) | digital | retro |
| `nature` | 大地色系有机插画 | 环保、健康、自然 | [styles/nature.md](styles/nature.md) | hand-drawn | earth |
| `pixel-art` | 8 位像素游戏美学 | 游戏、复古科技、极客 | [styles/pixel-art.md](styles/pixel-art.md) | pixel | vivid |
| `playful` | 奇思妙想粉彩趣味涂鸦 | 趣味、休闲、儿童教育 | [styles/playful.md](styles/playful.md) | hand-drawn | pastel |
| `retro` | 80/90 年代霓虹几何复古 | 怀旧、复古、赛博 | [styles/retro.md](styles/retro.md) | digital | retro |
| `sketch` | 原始笔记本铅笔素描 | 头脑风暴、创意探索 | [styles/sketch.md](styles/sketch.md) | hand-drawn | mono |
| `screen-print` | 丝网印刷海报艺术 | 观点、社论、文化 | [styles/screen-print.md](styles/screen-print.md) | screen-print | retro |
| `ink-notes` | 纯白黑墨专业视觉笔记（Mike Rohde 风格） | 宣言、对比、框架类比 | [styles/ink-notes.md](styles/ink-notes.md) | chalk | mono |
| `vintage` | 仿旧羊皮纸历史感 | 历史、传统、传承 | [styles/vintage.md](styles/vintage.md) | hand-drawn | retro |

> **派生 Rendering 列**是硬映射（单一来源 [style-rendering-mapping.md](style-rendering-mapping.md)）。**palette-default 列**仅为参考——全局锁 warm，此列在实际生成时被覆盖。

---

## 如何使用 style 维度（agent 构建prompt 时）

1. **Step 3 选 Type + Style**（三维法的两个用户维度；Type 11 值见 [dimensions.md](dimensions.md#type11-值)，Style 23 值见本文件）——按显式参数 / preset / auto-selection 得出
2. **派生 Rendering**：查 [style-rendering-mapping.md](style-rendering-mapping.md) 按 style 得 rendering（7 值之一）
3. **派生 Text/Font**：查 [visual-preset-mapping.md](visual-preset-mapping.md)「Type→Text/Font」表按 type 得 text/font
4. **Palette**：无条件 warm（规则 #14）
5. **Step 4 写 prompt 正文**：**必读** `styles/<style>.md` 的 Visual Elements / Style Rules 段（部分含 Layout Guidelines），把视觉描述词写进 prompt 正文（Subject/Setting/Style words 槽位）
6. style 作为 frontmatter 字段记录（三维法的 Style 维度），便于追溯

---

## Type × Style 设计亲和性

Type → Style 推荐表（11 行，首选 + 备选）见 [auto-selection-rules.md](auto-selection-rules.md#auto-style-selection) 的「Auto Style Selection」段——那是权威源。本文件不重复。

不是硬约束——用户可自由组合 Type × Style，推荐表只给出"最不会出错"的选择。

---

## 历史色板别名

历史 4 色板别名（macaron/warm/mono-ink/neon）的映射见 [palette-colors.md](palette-colors.md) 的「色板别名」段（权威源）。全局锁 warm，历史命名仅作 custom 模式或未来解锁时参考。

---

## 维护说明

- **新增 style**：在 `styles/<new>.md` 建文件 → 在 [style-rendering-mapping.md](style-rendering-mapping.md) 主表加一行映射 → 在本表加一行（含派生 rendering + palette-default）→ 在 [style-presets.md](style-presets.md) 补 preset 别名。
- **style 是运行时维度**：新增/改名 style 必须同步更新 style-rendering-mapping.md（单一来源）。
- **style 文件归档**：若某个 style 长期不用，可归档到 `_backup/`；但需同步移除本表 + style-rendering-mapping.md + style-presets.md 中的相关条目，保持三者一致。
