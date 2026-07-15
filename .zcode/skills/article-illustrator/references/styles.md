# Style 索引

> 本文件是 23 个 style 的**导航中枢**：速查别名、总览、Type × Style 兼容矩阵、自动推荐策略。
> 每个 style 的完整定义在 `styles/<name>.md`，标准结构：Design Aesthetic / Background / Color Palette / Visual Elements / Style Rules / Best For（六段）。其中 `sketch-notes` 和 `ink-notes` 另含 Layout Guidelines 与 Type Compatibility 段（最详尽）；其余 style 的 Type 兼容性数据汇总在本页下文的兼容矩阵。
> style 到 article-cover-image-generator 的 (rendering, palette) 映射在 [style-rendering-mapping.md](style-rendering-mapping.md)（单一来源）。

---

## Core Styles（速查别名）

简化选择层，用 7 个易记别名指向实际 style。**当内容分析无明显信号时，默认用 `hand-drawn`（→ sketch-notes）。**

| Core Style 别名 | 实际指向 | 适用 |
|---|---|---|
| `hand-drawn` | sketch-notes | **默认**。暖奶油纸+黑手绘线+马卡龙色块——教育信息图、概念解说、入门引导、通用知识 |
| `vector` | vector-illustration | 知识文章、教程、科技内容 |
| `minimal-flat` | notion | 通用、知识分享、SaaS |
| `sci-fi` | blueprint | AI、前沿科技、系统设计 |
| `editorial` | editorial | 流程、数据、新闻杂志 |
| `scene` | warm / watercolor | 叙事、情感、生活 |
| `poster` | screen-print | 观点、社论、文化、电影感 |

---

## Style Gallery（23 个）

| Style | 中文一句话 | Best For | 详细定义 |
|---|---|---|---|
| `sketch-notes` | 暖奶油纸+黑手绘线+马卡龙色块教育信息图 | 教育、知识分享、概念解说、教程、入门、产品演示 | [styles/sketch-notes.md](styles/sketch-notes.md) |
| `vector-illustration` | 干净黑轮廓+复古柔色扁平矢量 | 知识文章、教程、科技内容 | [styles/vector-illustration.md](styles/vector-illustration.md) |
| `notion` | 极简手绘线稿，类 Notion 美学 | 知识分享、SaaS、生产力、通用 | [styles/notion.md](styles/notion.md) |
| `elegant` | 精致克制的优雅插画 | 商业、思想领袖、战略、专业内容 | [styles/elegant.md](styles/elegant.md) |
| `warm` | 友好亲和的暖色调插画 | 个人成长、生活、教育、情感 | [styles/warm.md](styles/warm.md) |
| `minimal` | 极致干净的禅意极简 | 哲学、极简主义、核心概念 | [styles/minimal.md](styles/minimal.md) |
| `blueprint` | 蓝色工程图纸，技术精确感 | 架构、系统设计、工程 | [styles/blueprint.md](styles/blueprint.md) |
| `watercolor` | 柔和水彩晕染，可见笔触 | 生活、旅行、创意、情感叙事 | [styles/watercolor.md](styles/watercolor.md) |
| `editorial` | 杂志级编辑信息图（Wired 风格） | 科技解说、数据新闻、调查 | [styles/editorial.md](styles/editorial.md) |
| `scientific` | 学术精确示意图 | 生物、化学、医学、科研论文 | [styles/scientific.md](styles/scientific.md) |
| `chalkboard` | 黑板粉笔手绘，教室板书 | 教育、教学、工作坊讲解 | [styles/chalkboard.md](styles/chalkboard.md) |
| `fantasy-animation` | 吉卜力/迪士尼奇幻手绘 | 故事书、魔法、情感、家庭友好 | [styles/fantasy-animation.md](styles/fantasy-animation.md) |
| `flat` | 现代几何扁平矢量 | 现代数字、当代商业、社交内容 | [styles/flat.md](styles/flat.md) |
| `flat-doodle` | 圆润粗轮廓可爱扁平涂鸦 | 可爱、友好、亲和、初学者引导 | [styles/flat-doodle.md](styles/flat-doodle.md) |
| `intuition-machine` | 仿旧纸张双语技术简报 | 技术深度文章、学术简报、双语受众 | [styles/intuition-machine.md](styles/intuition-machine.md) |
| `nature` | 大地色系有机插画 | 环保、健康、自然、可持续 | [styles/nature.md](styles/nature.md) |
| `pixel-art` | 8 位像素游戏美学 | 游戏、复古科技、极客文化 | [styles/pixel-art.md](styles/pixel-art.md) |
| `playful` | 奇思妙想粉彩趣味涂鸦 | 趣味、休闲、儿童教育 | [styles/playful.md](styles/playful.md) |
| `retro` | 80/90 年代霓虹几何复古 | 怀旧、复古、赛博、流行文化 | [styles/retro.md](styles/retro.md) |
| `sketch` | 原始笔记本铅笔素描 | 头脑风暴、创意探索、草稿感 | [styles/sketch.md](styles/sketch.md) |
| `screen-print` | 丝网印刷海报艺术 | 观点、社论、文化评论、电影感 | [styles/screen-print.md](styles/screen-print.md) |
| `ink-notes` | 纯白黑墨专业视觉笔记（Mike Rohde 风格） | 宣言、前后对比、框架类比、技术评论 | [styles/ink-notes.md](styles/ink-notes.md) |
| `vintage` | 仿旧羊皮纸历史感 | 历史、传统、传承、古典 | [styles/vintage.md](styles/vintage.md) |

---

## Type × Style 兼容矩阵

> **✓✓** = 强烈推荐 ｜ **✓** = 兼容 ｜ **⚠** = 可用但非首选 ｜ **✗** = 不推荐
>
> 数据来源：`sketch-notes`/`ink-notes` 的 Type Compatibility 来自其 style 文件；其余 11 个（sketch-notes/vector-illustration/notion/warm/minimal/blueprint/watercolor/elegant/editorial/scientific/screen-print）来自 baoyu 原始矩阵；最后 10 个（chalkboard/fantasy-animation/flat/flat-doodle/intuition-machine/nature/pixel-art/playful/retro/sketch/vintage）基于各 style 的 Best For 描述与视觉特性合理推断（标注 *）。

| Type ＼ Style | sketch-notes | vector-illustration | notion | warm | minimal | blueprint | watercolor | elegant | editorial | scientific | screen-print | ink-notes | chalkboard | fantasy-animation | flat | flat-doodle | intuition-machine | nature | pixel-art | playful | retro | sketch | vintage |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **infographic** | ✓✓ | ✓✓ | ✓✓ | ✓ | ✓✓ | ✓✓ | ✓ | ✓✓ | ✓✓ | ✓✓ | ✓ | ✓✓ | ✓✓ * | ✓ * | ✓✓ * | ✓✓ * | ✓✓ * | ✓ * | ✓ * | ✓ * | ✓ * | ✓ * | ✓ * |
| **scene** | ✗ | ✓ | ✓ | ✓✓ | ✓ | ✗ | ✓✓ | ✓ | ✓ | ✗ | ✓✓ | ✗ | ⚠ * | ✓✓ * | ✓ * | ✓ * | ✗ * | ✓✓ * | ✗ * | ✓ * | ✓ * | ⚠ * | ✓ * |
| **flowchart** | ✓✓ | ✓✓ | ✓✓ | ✓ | ✓ | ✓✓ | ✗ | ✓ | ✓✓ | ✓ | ✗ | ✓✓ | ✓✓ * | ⚠ * | ✓✓ * | ✓✓ * | ✓✓ * | ⚠ * | ⚠ * | ✓ * | ⚠ * | ✓ * | ⚠ * |
| **comparison** | ✓✓ | ✓✓ | ✓✓ | ✓ | ✓✓ | ✓ | ✓ | ✓✓ | ✓✓ | ✓ | ✓ | ✓✓ | ✓ * | ⚠ * | ✓✓ * | ✓✓ * | ✓ * | ⚠ * | ⚠ * | ✓ * | ⚠ * | ✓ * | ⚠ * |
| **framework** | ✓✓ | ✓✓ | ✓✓ | ✓ | ✓✓ | ✓✓ | ✗ | ✓✓ | ✓ | ✓✓ | ✓ | ✓✓ | ✓ * | ⚠ * | ✓✓ * | ✓✓ * | ✓✓ * | ⚠ * | ⚠ * | ✓ * | ⚠ * | ✓ * | ⚠ * |
| **timeline** | ✓ | ✓ | ✓✓ | ✓ | ✓ | ✓ | ✓✓ | ✓✓ | ✓✓ | ✓ | ✓ | ✓ | ✓ * | ✓ * | ✓✓ * | ✓ * | ✓ * | ✓ * | ✓ * | ✓ * | ✓✓ * | ⚠ * | ✓✓ * |

---

## Auto Selection by Type（无强信号时的默认）

`sketch-notes` 是所有图表类 Type 的默认首选。仅当 Step 2 内容分析有明确信号（技术/数据/叙事/观点）时才覆盖为其他首选。

| Type | 首选 Style | 备选 Styles |
|------|----------|------------|
| infographic | sketch-notes | vector-illustration, notion, blueprint, editorial |
| scene | warm | watercolor, elegant, fantasy-animation |
| flowchart | sketch-notes | vector-illustration, notion, blueprint |
| comparison | sketch-notes | vector-illustration, notion, elegant, ink-notes |
| framework | sketch-notes | blueprint, vector-illustration, notion, ink-notes |
| timeline | elegant | sketch-notes, warm, editorial, vintage |

---

## Auto Selection by Content Signals（内容信号→Type+Style）

Step 2 内容分析后，按下表推荐 Type 和 Style：

| 内容信号 | 推荐 Type | 推荐 Style |
|---|---|---|
| **(无强信号 / 通用文章)** | **infographic** | **sketch-notes** |
| 知识、概念、教程、学习、指南、入门 | infographic | sketch-notes, vector-illustration, notion |
| 生产力、SaaS、工具、App、软件 | infographic | sketch-notes, notion, vector-illustration |
| How-to、步骤、工作流、流程、教程 | flowchart | sketch-notes, vector-illustration, notion |
| API、指标、数据、对比、数字 | infographic | blueprint, vector-illustration |
| 科技、AI、编程、开发、代码 | infographic | vector-illustration, blueprint, sketch-notes |
| 框架、模型、架构、原则 | framework | blueprint, vector-illustration, sketch-notes |
| vs、优劣、前后对比、替代方案 | comparison | vector-illustration, notion, sketch-notes, ink-notes |
| 宣言、思维转变、职场、OS、白板、专业视觉笔记 | comparison / framework | **ink-notes** |
| 故事、情感、旅程、经历、个人 | scene | warm, watercolor, fantasy-animation |
| 历史、时间线、进展、演进 | timeline | elegant, warm, vintage |
| 商业、专业、战略、企业 | framework | elegant |
| 观点、社论、文化、哲学、电影感、戏剧、海报 | scene | **screen-print** |
| 生物、化学、医学、科学 | infographic | **scientific** |
| 解说、新闻、杂志、调查 | infographic | **editorial** |
| 教育、教学、工作坊、课堂讲解 | infographic / flowchart | **chalkboard** |
| 儿童、奇幻、魔法、家庭友好 | scene | **fantasy-animation**, playful |
| 游戏、复古科技、极客、8 位 | infographic | **pixel-art**, retro |
| 怀旧、80/90 年代、流行文化、赛博 | scene / infographic | **retro**, pixel-art |
| 头脑风暴、创意探索、草稿、思考过程 | framework / flowchart | **sketch** |
| 环保、健康、自然、可持续、慢生活 | scene | **nature**, watercolor |
| 历史、传承、古典、博物馆 | timeline | **vintage**, elegant |
| 技术 depth、学术简报、双语 | infographic / framework | **intuition-machine**, blueprint |
| 现代数字产品、当代商业、社交 | infographic | **flat**, vector-illustration |
| 可爱、亲和、初学者、休闲 | infographic / flowchart | **flat-doodle**, playful |

---

## Palette Gallery（色板总览）

色板可覆盖 style 的默认配色。任意 style × 任意 palette 自由组合：`--style vector-illustration --palette macaron`。

| Palette | 描述 | 适用 |
|---|---|---|
| `macaron` | 柔和粉彩色块（蓝/薄荷/薰衣草/蜜桃）+ 暖奶油底 | 教育、知识、教程 |
| `warm` | 暖大地色（橙/赤陶/金）+ 柔桃底，无冷色 | 品牌、产品、生活 |
| `neon` | 高饱和霓虹（粉/青/黄）+ 深紫底 | 游戏、复古、流行文化 |
| `mono-ink` | 纯白底黑墨 + 少量语义点缀（珊瑚红/柔和青/灰紫） | 专业视觉笔记、前后对比、宣言 |

完整色板规格（hex/角色/语义约束）见 [palettes.md](palettes.md)。色板到 article-cover-image-generator 的映射见 [style-rendering-mapping.md](style-rendering-mapping.md#色板兼容article-illustrator--article-cover-image-generator)。

---

## Palette Override 规则

1. 读 style 文件 → 取渲染规则（Visual Elements / Style Rules / 线条质感 / 纹理）
2. 读 palette 文件（`palettes.md` 对应段）→ 取 Colors + Background
3. Palette 的 Colors **替换** style 的默认 Color Palette
4. Palette 的 Background **替换** style 的默认 Background
5. Style 的纹理描述**保留**

未指定 palette 时，用 style 自带的默认配色（见各 style 文件的 Color Palette 段）。
