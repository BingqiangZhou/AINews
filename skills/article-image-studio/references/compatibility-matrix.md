# Compatibility Matrices

✓✓ = highly recommended | ✓ = compatible | ✗ = not recommended

> **三维法下的角色**：三维法（Type × Style × Palette）下，Palette 全局锁 warm、Rendering 从 Style 派生、Font 从 Type 派生——本文件的 3 张矩阵不再是用户选维度的查询表，而是**派生维度的兼容性检查参考**：
> - **Palette × Rendering**：用于评估"warm（锁）× 派生 rendering"组合是否自洽；不自洽时（如 warm × chalk）调整 style 或加视觉补偿词。
> - **Type × Rendering**：用于评估"Type × 派生 rendering"组合；冲突时（如 scene × flat-vector）调整 style。
> - **Font × Rendering**：用于评估"派生 font × 派生 rendering"组合；冲突时（如 clean × hand-drawn）说明 Type/Style 选得不自洽，回退重选。
>
> 3 张矩阵：Palette×Rendering / Type×Rendering / Font×Rendering。Type→Text 和 Type→Font 的派生映射见 [visual-preset-mapping.md](visual-preset-mapping.md) 的 Type→Text/Font 表（11 值 Type 权威源）。

---

## Palette × Rendering（配色 × 渲染技法）

控制"色板和画风搭不搭"。这是 prompt 工程最常用的兼容性查询。

| | flat-vector | hand-drawn | painterly | digital | pixel | chalk | screen-print |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| warm | ✓✓ | ✓✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| elegant | ✓ | ✓✓ | ✓ | ✓✓ | ✗ | ✗ | ✓ |
| cool | ✓✓ | ✓ | ✗ | ✓✓ | ✓ | ✓ | ✓ |
| dark | ✓ | ✓ | ✓ | ✓✓ | ✓ | ✓✓ | ✓✓ |
| earth | ✓ | ✓✓ | ✓✓ | ✓ | ✗ | ✗ | ✓ |
| vivid | ✓✓ | ✓ | ✓ | ✓ | ✓✓ | ✓ | ✓✓ |
| pastel | ✓✓ | ✓✓ | ✓✓ | ✓ | ✗ | ✗ | ✗ |
| mono | ✓✓ | ✓ | ✗ | ✓✓ | ✓ | ✓ | ✓✓ |
| retro | ✓✓ | ✓✓ | ✓ | ✓✓ | ✓ | ✗ | ✓✓ |
| duotone | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓✓ |
| macaron | ✓✓ | ✓✓ | ✓ | ✓ | ✗ | ✗ | ✗ |

> neon 独立保留（深底霓虹），与上述白底/亮底色板不直接对比，按需搭配 painterly/digital/screen-print。

---

## Type × Rendering（信息结构 × 渲染技法）

控制"画的内容类型和画风搭不搭"。这是第二常用的查询——决定了一张 infographic 该用 hand-drawn 还是 digital。

| | flat-vector | hand-drawn | painterly | digital | pixel | chalk | screen-print |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| hero | ✓ | ✓✓ | ✓✓ | ✓✓ | ✓ | ✓ | ✓✓ |
| conceptual | ✓✓ | ✓ | ✗ | ✓✓ | ✓ | ✓ | ✓ |
| typography | ✓✓ | ✓ | ✓ | ✓✓ | ✓ | ✓ | ✓✓ |
| metaphor | ✓ | ✓✓ | ✓✓ | ✓ | ✗ | ✓ | ✓✓ |
| scene | ✗ | ✓ | ✓✓ | ✓ | ✓ | ✗ | ✓ |
| minimal | ✓✓ | ✓ | ✓ | ✓✓ | ✗ | ✗ | ✓✓ |
| infographic | ✓✓ | ✓✓ | ✗ | ✓✓ | ✓ | ✓ | ✓ |
| flowchart | ✓✓ | ✓✓ | ✗ | ✓✓ | ✓ | ✓ | ✗ |
| comparison | ✓✓ | ✓✓ | ✗ | ✓ | ✓ | ✓ | ✓✓ |
| framework | ✓✓ | ✓✓ | ✗ | ✓✓ | ✓ | ✓ | ✓ |
| timeline | ✓✓ | ✓✓ | ✓ | ✓✓ | ✓ | ✓ | ✓ |

---

## Font × Rendering（字体 × 渲染技法）

控制"图内字体和画风搭不搭"。hand-drawn 渲染配 clean 字体会脱节，chalk 渲染配 serif 字体会冲突。

| | flat-vector | hand-drawn | painterly | digital | pixel | chalk | screen-print |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| clean | ✓✓ | ✗ | ✗ | ✓✓ | ✓ | ✗ | ✓ |
| handwritten | ✓ | ✓✓ | ✓✓ | ✓ | ✗ | ✓✓ | ✗ |
| serif | ✓ | ✗ | ✓ | ✓✓ | ✗ | ✗ | ✓ |
| display | ✓✓ | ✓ | ✓ | ✓✓ | ✓✓ | ✓ | ✓✓ |

---

## 未列出的 Type 相关映射

Type → Text/Font 和 Type → Mood 不在本文件维护，已分散到更合适的位置：

- **Type × Text** → [visual-preset-mapping.md](visual-preset-mapping.md#三type-textfont-默认值cover-和-illustrate-共用11-值-type) 的「Type → Text/Font 默认值」表（cover 和 illustrate 共用权威源）。
- **Type × Mood** → [dimensions.md](dimensions.md#type11-值) 各 Type 的 Compatibility 行（如 hero 推荐 bold/balanced、minimal 推荐 subtle/balanced）。
