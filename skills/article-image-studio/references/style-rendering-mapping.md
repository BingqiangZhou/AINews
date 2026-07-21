# Style → Rendering 映射（单一来源）

> **用途**：三维法（Type × Style × Palette）下，**Rendering 不是用户维度**，由 Style 派生。本文件是 **Style → Rendering 的唯一权威映射**，`agents/image-studio.md` 和 `references/workflow.md` 必须读本文件查表，不得内联硬编码映射。
>
> **设计原则**：
> 1. `rendering` 是"渲染技法"粗分（7 值），style 的精细视觉差异（线条质感、版式、装饰元素）由各 style 文件（`styles/<name>.md` 的 Visual Elements / Style Rules，部分另含 Layout Guidelines）承载并写入 prompt 正文。
> 2. **palette-default 列仅为参考**——cover 与 illustrate 模式 palette 全局锁 `warm`（见 SKILL.md「关键规则：Palette 全局锁 warm」），下表的 palette-default 在实际生成时被无条件覆盖为 `warm`，仅当未来解锁 palette 或 custom 模式才生效。
> 3. 命名沿袭合并前 `article-cover-image-generator` 的 26 个 `style_preset`，同名时复用其语义。

---

## 映射主表（23 个 style）

| style | rendering | palette-default（仅参考，被 warm 锁覆盖） | 备注 |
|---|---|---|---|
| `sketch-notes` | `hand-drawn` | `macaron` | **默认主推**；暖色奶油纸+黑线+马卡龙色块 |
| `vector-illustration` | `flat-vector` | `retro` | 干净黑轮廓+复古柔色扁平矢量 |
| `notion` | `digital` | `mono` | 极简手绘线稿，类 Notion 美学 |
| `elegant` | `hand-drawn` | `elegant` | 精致优雅，商务感 |
| `warm` | `hand-drawn` | `warm` | 友好暖色调，金色光线 |
| `minimal` | `flat-vector` | `mono` | 极致干净的禅意极简 |
| `blueprint` | `digital` | `cool` | 蓝色工程图纸，技术精确感 |
| `watercolor` | `painterly` | `earth` | 柔和水彩晕染，可见笔触 |
| `editorial` | `digital` | `cool` | 杂志级编辑信息图 |
| `scientific` | `digital` | `cool` | 学术精确示意图（借用 blueprint 的 digital+cool） |
| `chalkboard` | `chalk` | `dark` | 黑板粉笔手绘，教室板书 |
| `fantasy-animation` | `painterly` | `pastel` | 吉卜力/迪士尼奇幻手绘 |
| `flat` | `flat-vector` | `vivid` | 现代几何扁平矢量 |
| `flat-doodle` | `flat-vector` | `pastel` | 圆润粗轮廓可爱扁平涂鸦 |
| `intuition-machine` | `digital` | `retro` | 仿旧纸张双语技术简报 |
| `nature` | `hand-drawn` | `earth` | 大地色系有机插画 |
| `pixel-art` | `pixel` | `vivid` | 8 位像素游戏美学 |
| `playful` | `hand-drawn` | `pastel` | 奇思妙想粉彩趣味涂鸦 |
| `retro` | `digital` | `retro` | 80/90 年代霓虹几何复古 |
| `sketch` | `hand-drawn` | `mono` | 原始笔记本铅笔素描 |
| `screen-print` | `screen-print` | `retro` | 丝网印刷海报艺术 |
| `ink-notes` | `chalk` | `mono` | 专业黑墨视觉笔记，Mike Rohde 风格（cover 的 `chalk` rendering 最接近"干性笔触"） |
| `vintage` | `hand-drawn` | `retro` | 仿旧羊皮纸历史感 |

---

## 查表规则（agent 执行维度派生时遵循）

1. 从 outline.md（illustrate）或入参（cover）读取 `style` 字段（如 `ink-notes`）。
2. 在本表查到 `rendering`（如 `ink-notes → rendering=chalk`）。
3. **palette 无条件采用 `warm`**（全局锁，见 SKILL.md）——本表的 palette-default 列**不读**，仅留作未来解锁时的参考。
4. 将 `rendering` 传给 `image-generator` 的 dimensions。
5. `text` 和 `font` 维度**不读本表**——查 [visual-preset-mapping.md](visual-preset-mapping.md) 的「Type → Text/Font 默认值」段（按当前 Type 查）。
6. `mood` 维度默认 `balanced`，不暴露给用户。

### 维度传递示例

outline 里某张图：`type: framework, style: ink-notes`

查本表：`ink-notes → rendering=chalk`
查 Type→Text/Font 表：`framework → text=text-rich, font=handwritten`
palette 全局锁：`warm`
mood 默认：`balanced`

最终传给 image-generator 的 dimensions：
```json
{
  "dimensions": {
    "type": "framework",
    "style": "ink-notes",
    "palette": "warm",
    "rendering": "chalk",
    "text": "text-rich",
    "mood": "balanced",
    "font": "handwritten"
  }
}
```

> 注：image-generator 收到 dimensions 时，`style` 是用户维度（信息记录），`rendering` 是派生维度（实际控制渲染技法的字段）。两者都写入 prompt 文件 frontmatter，便于追溯。

---

## 历史色板兼容（仅供解锁时参考）

历史曾用 4 色板（macaron/warm/mono-ink/neon），现已全局锁 warm。若未来解锁 palette，历史 palette 别名的映射关系见 [palette-colors.md](palette-colors.md) 的「色板别名」段（权威源）。

> 特别注意：`neon` 在 palette-colors.md 中**独立保留**（深底霓虹，与 vivid 白底高饱和语义不同），**不映射到 vivid**。

---

## 维护说明

- **新增 style**：在 `styles/<new>.md` 建文件 → 在本表加一行映射 → 在 [styles.md](styles.md) 的 Style Gallery 和兼容矩阵补条目 → 在 [style-presets.md](style-presets.md) 补 preset 别名。
- **改名**：同步改本表 + styles.md 索引 + style-presets.md。
- **本表是 Style → Rendering 的唯一来源**：`agents/image-studio.md`、`workflow.md`、`SKILL.md` 不得内联映射，统一引本文件。
