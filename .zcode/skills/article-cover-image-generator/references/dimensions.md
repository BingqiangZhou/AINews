# Cover Image Dimensions Reference

六维方法论的完整定义。每个值附 **Prompt cues**（该值在 prompt 中应激发的视觉词）、**Compatibility hints**（最佳搭配，详见 [compatibility-matrix.md](compatibility-matrix.md)）、**Anti-patterns**（不该出现什么）。

---

## Type（6 值）

定义整体构图方法。

### `hero`
大视觉冲击，标题压图。

- **Best for:** 产品发布、品牌宣传、重大公告
- **Composition:** 大焦点视觉（占 60-70% 面积），标题压在视觉上，戏剧化
- **Prompt cues:** `large focal visual, dramatic centerpiece, title overlay area, bold subject`
- **Compatibility:** ✓✓ painterly / digital / screen-print；搭配 vivid / dark / duotone
- **Anti-patterns:** ❌ 密集小元素堆砌（失去焦点）；❌ 焦点视觉小于画面 40%

### `conceptual`
概念可视化，抽象表达核心。

- **Best for:** 技术文章、方法论、架构设计
- **Composition:** 抽象图形表达核心概念，信息层级，干净分区，留白均衡
- **Prompt cues:** `abstract geometric shapes, information hierarchy, balanced negative space, layered concepts`
- **Compatibility:** ✓✓ flat-vector / digital；搭配 cool / mono / macaron
- **Anti-patterns:** ❌ 具象写实场景（应抽象化）；❌ 单一焦点（应是层级结构）

### `typography`
文字主导，标题为主体。

- **Best for:** 观点、引言、洞见
- **Composition:** 标题为首要元素（占 40%+ 面积），极简辅助视觉，强层级
- **Prompt cues:** `prominent title typography, minimal supporting visuals, strong typographic hierarchy`
- **Compatibility:** ✓✓ flat-vector / digital / screen-print；搭配 mono / dark / elegant。**注意：必须 text ≥ title-only**（见 compatibility Type×Text，typography×none=✗）
- **Anti-patterns:** ❌ text: none（无字则失去意义）；❌ 标题字号过小（应 ≥ 画面高度 1/6）

### `metaphor`
视觉隐喻，具象表达抽象。

- **Best for:** 哲学、成长、个人发展
- **Composition:** 具象物/场景代表抽象概念，象征性元素，情感共鸣
- **Prompt cues:** `symbolic object, metaphorical scene, concrete representing abstract, emotional resonance`
- **Compatibility:** ✓✓ hand-drawn / painterly / screen-print；搭配 warm / earth / elegant
- **Anti-patterns:** ❌ text-rich（隐喻靠图像，文字宜少，见 Type×Text metaphor×text-rich=✗）；❌ 直白图解（应留想象空间）

### `scene`
氛围场景，叙事感。

- **Best for:** 故事、旅行、生活方式
- **Composition:** 氛围环境，叙事元素，定调光照与色彩
- **Prompt cues:** `atmospheric environment, narrative elements, mood-setting lighting, environmental storytelling`
- **Compatibility:** ✓✓ painterly / digital；搭配 warm / earth / pastel。**避免 flat-vector**（见 Type×Rendering scene×flat-vector=✗）
- **Anti-patterns:** ❌ flat-vector 扁平化（破坏氛围）；❌ text-rich（场景靠画面叙事，文字宜少）

### `minimal`
极简构图，大量留白。

- **Best for:** 禅意、聚焦、核心概念
- **Composition:** 单一焦点元素，大量留白（60%+），仅保留本质形状
- **Prompt cues:** `single focal element, generous whitespace, essential shapes only, refined simplicity`
- **Compatibility:** ✓✓ flat-vector / digital / screen-print；搭配 mono / elegant / cool
- **Anti-patterns:** ❌ 密集细节/装饰（违背极简）；❌ bold mood（见 Type×Mood minimal×bold=✗）；❌ text-rich

---

## Palette（11 值）

`warm`, `elegant`, `cool`, `dark`, `earth`, `vivid`, `pastel`, `mono`, `retro`, `duotone`, `macaron`。

完整 hex + decorative_hints + color_ratio 见 [palette-colors.md](palette-colors.md)。

---

## Rendering（7 值）

定义视觉渲染风格 / 插画技法。

### `flat-vector`
干净几何形状，纯色填充，无渐变。

- **Feel:** 现代、干净
- **Details:** 锐利边缘，均匀色块，最小纹理
- **Prompt cues:** `flat vector illustration, clean solid fills, sharp geometric edges, no gradients`
- **Compatibility:** ✓✓ warm / cool / vivid / pastel / mono / retro；✓✓ conceptual / typography / minimal。**避免 scene**（见矩阵 ✗）
- **Anti-patterns:** ❌ 渐变/光晕/阴影；❌ 手绘抖动线条

### `hand-drawn`
素描有机线条，不完美笔触。

- **Feel:** 个人、随性
- **Details:** 变化的线宽，可见笔触纹理，有机不完美
- **Prompt cues:** `hand-drawn sketch, varied line weight, visible stroke texture, organic imperfection`
- **Compatibility:** ✓✓ warm / earth / pastel / retro；✓✓ metaphor。**避免 clean font + painterly/digital**（见 Font×Rendering clean×hand-drawn=✗）
- **Anti-patterns:** ❌ 数学般精确的几何；❌ 纯色无笔触

### `painterly`
笔触可见，水彩效果，柔和边缘。

- **Feel:** 艺术、梦幻
- **Details:** 可见笔触纹理，色彩晕染，柔和过渡
- **Prompt cues:** `loose watercolor washes, visible brush texture, soft color bleeding, painterly edges`
- **Compatibility:** ✓✓ warm / earth / pastel；✓✓ hero / metaphor / scene。**避免 cool / mono / duotone**（见矩阵 ✗）
- **Anti-patterns:** ❌ 锐利矢量边缘；❌ 限制色板（水彩需色彩流动）

### `digital`
精致、精确、渐变友好。

- **Feel:** 企业、精致
- **Details:** 平滑渐变，精确形状，专业收尾
- **Prompt cues:** `polished digital illustration, smooth gradients, precise shapes, professional finish`
- **Compatibility:** ✓✓ elegant / cool / dark / mono / retro；✓✓ hero / conceptual / typography / minimal
- **Anti-patterns:** ❌ 可见的手绘笔触；❌ 像素化锯齿

### `pixel`
像素艺术，8-bit 美学，块状形状。

- **Feel:** 复古、游戏
- **Details:** 网格对齐，每区域限制色数，可见像素
- **Prompt cues:** `pixel art, 8-bit aesthetic, grid-aligned blocks, limited color palette per area`
- **Compatibility:** ✓✓ vivid；搭配 hero / scene。**避免 elegant / earth / pastel / duotone / metaphor / minimal**（见矩阵 ✗）
- **Anti-patterns:** ❌ 平滑抗锯齿；❌ 丰富渐变（像素风需硬边色块）

### `chalk`
黑板纹理，粉笔痕迹。

- **Feel:** 教学、教程
- **Details:** 深色背景，粉笔状笔触，晕染边缘
- **Prompt cues:** `chalkboard texture, dusty chalk strokes, smudged edges, dark matte background`
- **Compatibility:** ✓✓ dark；搭配 hero / conceptual。**避免 elegant / earth / pastel / serif font**（见矩阵 ✗）
- **Anti-patterns:** ❌ 亮色背景（chalk 需深色底）；❌ clean font（见 Font×Rendering clean×chalk=✗）

### `screen-print`
大胆平涂，限制色板，强对比。

- **Feel:** 海报、戏剧化
- **Details:** 硬边，叠色图层，套印标记美学
- **Prompt cues:** `screen-print poster, bold flat color layers, hard edges, registration-mark aesthetic, limited palette`
- **Compatibility:** ✓✓ dark / vivid / mono / retro / duotone；✓✓ hero / typography / minimal。**避免 pastel / duotone×hand-drawn**（见矩阵）
- **Anti-patterns:** ❌ 柔和渐变；❌ 细腻笔触（应是硬边色块叠加）

---

## Text（4 值）

控制封面上的文字量。

### `none`
纯视觉，无文字。**封面默认。**

### `title-only`
文章标题作为压字。标准博客封面。

### `title-subtitle`
标题 + 副标题/标语。系列、教程。

### `text-rich`
多文字元素、标签、说明。公告、信息图。

> **图内文字契约**：后端只消费 prompt 正文。要画的具体文字必须写进正文，不能只放 YAML frontmatter。

---

## Mood（3 值）

控制整体对比度与视觉强度。

### `subtle`
低对比，柔和，克制。

- **Prompt cues:** `muted tones, low contrast, soft diffused light, understated`
- **Use for:** 专业、学术、深度思考

### `balanced`
中等对比，和谐。

- **Prompt cues:** `harmonious contrast, balanced composition, even lighting`
- **Use for:** 通用、教育、标准内容（默认）

### `bold`
高对比，戏剧化，抓眼。

- **Prompt cues:** `high contrast, dramatic lighting, vivid saturation, eye-catching`
- **Use for:** 发布、促销、娱乐。**避免 minimal**（见 Type×Mood minimal×bold=✗）

---

## Font（4 值）

控制字体人格（图内文字若有）。

### `clean`
无衬线，现代，技术。**(默认)**

- **Compatibility:** ✓✓ flat-vector / digital / pixel / screen-print。**避免 hand-drawn / painterly / chalk**（见 Font×Rendering）

### `handwritten`
个人，随性，友好。

- **Compatibility:** ✓✓ hand-drawn / painterly / chalk。**避免 pixel / screen-print**

### `serif`
编辑、学术、经典。

- **Compatibility:** ✓✓ digital / screen-print。**避免 hand-drawn / pixel / chalk**

### `display`
粗装饰，醒目。

- **Compatibility:** ✓✓ flat-vector / digital / pixel / screen-print（最通用）。与所有 rendering 兼容
