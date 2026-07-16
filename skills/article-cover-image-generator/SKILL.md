---
name: article-cover-image-generator
version: "2.3.0"
description: >
  文章封面图专用编排器——用六维方法论（Type × Palette × Rendering × Text × Mood × Font）
  + 26 个风格预设构建封面 prompt，委托 image-generator 出图。支持 900x383 公众号封面、
  1920x1080 文章插图、自定义尺寸。**触发场景**：用户提到"生成封面""封面图""cover image""封面设计"，
  或需要为文章/公众号/小红书/抖音生成封面图时使用。注意：本 skill 只负责封面设计（维度+preset+prompt），
  实际图像生成由 image-generator skill 执行。
metadata:
  dimensions: [type, palette, rendering, text, mood, font]
  presets: 26
  backend: image-generator  # 实际生图委托 image-generator skill
---

# Cover Image Generator

使用六维方法论生成封面和插图，支持 Gaoding/Jimeng（浏览器自动化）和 Agnes（API）多后端。

## 关联 Skills

- **编排器（如 ai-news-digest）**：封面生成阶段委托本 skill
- **article-illustrator**：插图生成委托本 skill
- **baoyu-cover-image**：本 skill 的方法论来源

## 六维方法论

| 维度 | 可选值 | 默认 |
|------|--------|------|
| **Type** | hero, conceptual, typography, metaphor, scene, minimal | auto |
| **Palette** | warm, elegant, cool, dark, earth, vivid, pastel, mono, retro, duotone, macaron | macaron |
| **Rendering** | flat-vector, hand-drawn, painterly, digital, pixel, chalk, screen-print | hand-drawn |
| **Text** | none, title-only, title-subtitle, text-rich | none |
| **Mood** | subtle, balanced, bold | balanced |
| **Font** | clean, handwritten, serif, display | handwritten |

> 封面样式由 config.json `cover` 段锁定（取自 `hand-drawn-edu` 预设 + 手写字体），见下方「关键规则 #14」。

→ 详细定义见 [dimensions.md](references/dimensions.md)
→ 兼容性矩阵见 [compatibility-matrix.md](references/compatibility-matrix.md)
→ 自动推荐规则见 [auto-selection-rules.md](references/auto-selection-rules.md)

## 风格预设

`--style X` 展开为 Palette + Rendering 组合，可被显式 `--palette`/`--rendering` 覆盖。

共 26 个预设，如 `blueprint`(cool+digital)、`sketch-notes`(warm+hand-drawn)、`cinematic`(duotone+screen-print) 等。

→ 完整列表见 [style-presets.md](references/style-presets.md)

### Convenience Presets（映射编排器 visual_preset）

支持编排器的 4 个 `visual_preset`（`knowledge-card` / `cozy-story` / `bold-warning` / `minimal-opinion`），自动展开为六维策略（含插图 profile 的 Text/Font 覆盖、备选色板、内容信号判定）。→ 完整映射见 [visual-preset-mapping.md](references/visual-preset-mapping.md)。

## 色板

11 个色板，每个有具体 hex 定义。如 warm(#ED8936)、cool(#2563EB)、macaron(#A8D8EA) 等。

→ 完整定义见 [palette-colors.md](references/palette-colors.md)

## 环境依赖与迁移

本 skill 是纯 Markdown 编排器，实际生图委托 `image-generator` skill。运行前需满足：

| 依赖 | 用途 | 说明 |
|------|------|------|
| **image-generator skill** | 实际生图（Gaoding/Jimeng/Agnes）| 同插件内 `skills/image-generator/`（同仓自带） |
| **Python 3.10+** | image-generator 的 agnes_image.py | 路径见 config.json `environment.conda_python` |
| **Pillow (PIL)** | 后处理裁剪/resize | image-generator 内使用 |
| **Chrome** | Gaoding/Jimeng 浏览器自动化 | 由 chrome-devtools MCP 自动启动；需已登录稿定/即梦 session |
| **AGNES_API_KEY** | Agnes 后端（仅 `cover_provider: agnes` 或回退时）| 见 AGENTS.md 环境变量表 |

### 迁移清单（换机器时必改）

config.json 的 `environment` 段为**本机环境配置**，迁移到新机器时需修改：

- `conda_python`：本机 miniconda3 python 绝对路径（**绝不要假设 PATH 上的 python 是对的**，见 AGENTS.md）
- `chrome_download_dir`：本机 Chrome 下载目录（Gaoding 导出文件落地点）

> 这些硬编码是**有意的**（遵循 AGENTS.md「config.json 显式声明」约定），不是 bug。修改后即可在新机器运行。

## 流程概览

```text
输入 → [加载偏好] → [分析内容 + 自动选维度]
→ [构建 Prompt] → [生成图片] → [后处理] → [报告]
```

## 关键规则

1. **Prompt 先落盘**：所有 prompt 必须先写入 `prompts/` 目录，再调用生成后端
2. **Gaoding 只点一次**：生图按钮只点击一次（每次消耗 3 豆），通过 `list_pages` 轮询等待结果
3. **覆盖前备份**：写入任何输出文件前，已存在的非空文件先备份
4. **默认 text: none**：封面/插图默认不含图内文字，除非用户明确要求
5. **回退受 config 控制**：Gaoding 失败时，仅当 `cover.fallback_to_agnes == true`（默认 `false`）才回退 Agnes；否则报告失败由调用方决定。与编排器的"默认不回退"策略一致
6. **参数化尺寸**：通过 `target_size` 参数控制输出尺寸（900x383 / 1920x1080 / 自定义）
7. **自动取消社区发布**：Gaoding 导出时必须取消勾选"自动发布至社区"
8. **批量并行**：多张图片（封面 + 插图，或多张插图）必须并行生成，不逐张串行
9. **Gaoding 互斥**：同一时刻只能有一个 agent/进程操作 Gaoding（共享 Chrome 实例）。被编排调用时，多个图片请求必须在同一个 agent 内用批量并行模式处理，不能启动多个并行 agent 分别调用 Gaoding
10. **⛔ Gaoding 多图必须串行（每张新 tab）**：同一创建页 tab 内反复 `innerHTML='' + execCommand('insertText')` **不能可靠触发 React 状态更新**，会导致"每次提交的都是同一个 prompt"、生成出来全是雷同的图。多张图**必须每张开一个全新 tab**（`new_page` → `creation?skill=3`），每张独立选模型→输入→验证→生成→导出。详见 [`../image-generator/references/gaoding-image-generation.md`](../image-generator/references/gaoding-image-generation.md)「串行生成模式」。
11. **⛔ 禁止程序化替代生图**：绝不允许用 SVG/HTML/canvas/Canvas API/PIL/Pillow 绘图等方式替代 AI 图像模型生成位图。封面/插图必须是 `image-generator` 经由 Gaoding（万相2.7）/ Agnes 产出的真实位图。理由：程序化出图无美学一致性、无插画质感，会摧毁六维方法论的意义。后处理仅允许：crop / resize / 压缩 / 格式转换（且不得改动主构图或文字）。
12. **⛔ 禁止程序化修补已生成图的文字**：若生成图含错误文字/乱码，**禁止**用 PIL/Pillow/ImageMagick 在已生成图上贴字、抹字、改字。正确做法：(a) 修改 prompt 重新生成，或 (b) 改用 `text: none` 变体重生成。理由：程序化贴字与图像美学风格脱节，字体/排版与 AI 渲染不一致，会被读者一眼识破。
13. **后端失败显式上报，不静默降级**：`image-generator` 返回 `success: false` 时，本 skill 必须把失败结果 + `fallback_reason` 原样上报调用方，不静默重试、不静默换后端（除非 `cover.fallback_to_agnes: true`）。与编排器的"默认不回退，风格一致优先"策略一致。
14. **⛔ 封面固定样式（不再由 agent 选择）**：封面 palette / rendering / font 三个维度**固定**为 `macaron` / `hand-drawn` / `handwritten`（取自 `hand-drawn-edu` 预设 + 手写字体），由 config.json `cover` 段锁定为单一来源。**不被 visual_preset / style_preset 覆盖，不走 auto-selection-rules**——这两类 preset 此后只用于解析剩余的 `type` / `mood`。`text` 默认 `none`（文字交给公众号排版系统），`type` / `mood` 仍按内容信号自动选择。理由：用户要求封面统一为手写体教育插画风格，避免 agent 按内容信号在 11 色板 / 7 渲染 / 4 字体间反复漂移。兼容性已核对（macaron × hand-drawn = ✓✓，handwritten × hand-drawn = ✓✓，见 compatibility-matrix.md），无需调整。

## 偏好与优先级

维度值解析遵循单一优先级链（高 → 低），保证"偏好可覆盖、显式参数最高"：

```
[封面固定维度] palette / rendering / font — 无条件最高优先
        │   由 config.json cover + preferences 两段同时锁定为
        │   macaron / hand-drawn / handwritten（见「关键规则 #14」）
        │   不被任何 preset 或显式参数覆盖（插图 profile 除外，见下）
        ↓ 其余维度（type / text / mood）走以下链：
显式传入参数（dimensions/cover_provider 等）
        ↓ 若为 auto 或未传
visual_preset / style_preset 映射（仅解析 type / mood）
        ↓ 若仍为 auto 或未覆盖该维度
config.json → preferences 段（用户偏好，见下）
        ↓ 若为 auto
config.json → cover 段（机器默认）
        ↓ 若为 auto
auto-selection-rules（内容信号驱动）
```

> **封面固定样式的例外边界**：上述"palette/rendering/font 无条件最高优先"**仅对封面（target_profile == wechat-cover / custom）生效**。当 `target_profile == illustration` 时，回退到原优先级链（visual_preset 映射 + 插图 Text/Font Override 表，见 `visual-preset-mapping.md`），封面固定值不污染插图流程。

| 字段 | 取值 | 说明 |
|------|------|------|
| `default_type` | auto / hero / conceptual / ... | 默认 Type 偏好 |
| `default_palette` | auto / warm / cool / ... | 默认 Palette 偏好 |
| `default_rendering` | auto / flat-vector / ... | 默认 Rendering 偏好 |
| `default_text` | none / title-only / ... | 默认 Text 偏好（默认 none） |
| `default_mood` | subtle / balanced / bold | 默认 Mood 偏好（默认 balanced） |
| `default_font` | clean / handwritten / serif / display | 默认 Font 偏好（默认 clean） |
| `default_aspect` | 2.35:1 / 16:9 / 1:1 | 默认宽高比（未显式传 target_size 时参考） |
| `language` | zh / en / auto | prompt 语言偏好（auto = 按内容检测） |
| `disabled_presets` | string[] | 禁用的 `--style` 预设名列表（命中时回退到 auto-selection） |
| `preferred_palettes` | string[] | 优先推荐的色板（影响 auto-selection 排序，命中内容信号时优先选这些） |

> **单一来源声明**：遵循 AGENTS.md「config.json 是单一来源」约定。本 skill 不引入额外的 EXTEND.md / 用户级偏好文件；所有偏好集中在 config.json 的 `cover` + `preferences` 两段。`cover` 段为机器/流水线默认，`preferences` 段为个人风格偏好，二者由优先级链合并。

## 输入

| 参数 | 必选 | 说明 |
|------|------|------|
| `content_context` | 是 | 文章标题 + brief 核心论点 + 话题关键词 |
| `target_size` | 是 | 输出尺寸，如 `900x383`、`1920x1080` |
| `dimensions` | 否 | 六维策略（type/palette/rendering/text/mood/font），auto 则自动推荐 |
| `visual_preset` | 否 | convenience preset 名称，自动映射为六维策略 |
| `style_preset` | 否 | 26 风格预设之一，映射为 palette+rendering |
| `cover_provider` | 否 | gaoding（默认）/ jimeng / agnes |
| `output_path` | 是 | 输出文件路径 |
| `output_dir` | 是 | 输出目录（prompts/ 和产物存放） |
| `references` | 否 | 参考图片路径列表 |
| `prompt_only` | 否 | boolean, default false。为 true 时只执行 Steps 1-4（到 prompt 构建为止），跳过 Steps 5-7（图片生成、后处理、报告） |

## 输出

**完整生成模式**（`prompt_only == false`）：

```json
{
  "success": true,
  "data": {
    "image_path": "生成的图片文件路径",
    "provider": "gaoding | jimeng | agnes",
    "dimensions": { "type": "...", "palette": "...", "rendering": "...", "text": "...", "mood": "...", "font": "..." },
    "fallback_used": false,
    "fallback_reason": null,
    "original_size": "1923x818",
    "final_size": "900x383"
  }
}
```

**prompt_only 模式**（`prompt_only == true`）：

```json
{
  "success": true,
  "data": {
    "prompt_file": "prompts/cover.md",
    "dimensions": { "type": "...", "palette": "...", "rendering": "...", "text": "...", "mood": "...", "font": "..." },
    "target_size": "900x383",
    "mode": "prompt_only"
  }
}
```

## 执行步骤

### 1. Pre-check

1. 读取 `config.json` 的 `cover` 段 + `preferences` 段获取偏好设置（provider、model(Agnes 回退)、gaoding_model(稿定模型，默认万相2.7)、jimeng_model(即梦模型，默认图片 4.7)、六维默认、语言偏好等）。按「偏好与优先级」段的优先级链合并两段。
2. 确认 `output_dir` 存在，不存在则创建
3. 确认 `content_context` 和 `target_size` 已提供

### 2. 内容分析

1. 分析 content_context：提取主题、基调、关键词、视觉隐喻
2. 检测内容语言
3. **参考图深度分析**（当 `references` 非空时）：读取 [reference-images.md](references/reference-images.md)，按 6 维度表（品牌元素/标志性图案/精确 hex/布局比例/字体处理/渲染特征）提取可复现元素，标注 `usage`（direct/style/palette），保存参考图到 `refs/ref-NN-{slug}.{ext}`。这些元素将在 Step 4 按 MUST/REQUIRED 规则注入 prompt 正文。

### 3. 维度选择（自动，不询问用户）

根据 content 信号自动推荐维度，全自动无交互：

> **封面固定样式**（见「关键规则 #14」）：封面 `palette` / `rendering` / `font` 已由 config.json `cover` 段锁定为 `macaron` / `hand-drawn` / `handwritten`，**直接采用，跳过下面的 preset 映射与 auto-selection**。`visual_preset` / `style_preset` 只用于解析剩余的 `type` / `mood`；`text` 默认 `none`。

- 如果传入了 `visual_preset`，使用 visual-preset-mapping 的映射（**仅取 type/mood**，palette/rendering/font 被规则 #14 覆盖）
- 如果传入了 `style_preset`，使用 style-presets 的映射（**仅取 type/mood**，palette/rendering 被规则 #14 覆盖；style_preset 不影响 font/text）
- 剩余 auto 维度（type/mood）：根据 content_context 信号和 auto-selection-rules 自动推荐
- 检查兼容性矩阵，自动调整 ✗ 组合
- 直接进入 Step 4，不暂停等待用户确认

### 4. Prompt 构建

1. 根据 target_size 确定 target profile：

| Profile | target_label | target_size_desc | prompt_language |
|---------|-------------|-----------------|----------------|
| wechat-cover | WeChat公众号封面图 | 尺寸900x383像素，宽幅横版banner比例约2.35:1 | English |
| illustration | 文章插图 | 尺寸1920x1080像素，16:9宽幅横版比例 | 中文 |
| custom | 自定义 | 尺寸{W}x{H}像素 | 视场景 |

2. 构建 visual prompt（20-40 词描述），**使用 [prompt-template.md](references/prompt-template.md) 的 6 槽位结构**（Subject + Setting + Lighting + Style words + Mood + Composition），替代自由发挥
3. **颜色规则**：视觉 prompt 中**只用描述性颜色名称**（如 warm orange、cream background、"暖米白"、"橄榄绿"），**禁止包含任何 hex 色值**。AI 图像模型无法区分颜色指令和需要显示的文字，hex 值会被误渲染为图内文字。hex 色值仅写入 prompt 文件的 YAML frontmatter 作为元数据记录。
4. 写入 `prompts/cover.md`（或 `prompts/NN-{type}-{slug}.md`），记录：
   - 最终 prompt（含尺寸前缀）
   - 六维策略
   - cover_provider
   - target_size
   - references（如有，含 `references` frontmatter 列表 + MUST/REQUIRED 参考元素段落）
5. **参考元素注入**（当 Step 2 分析了参考图时）：按 [reference-images.md](references/reference-images.md) §4 的转译规则，在 prompt 正文末尾追加 `# 参考元素 — 必须复现` 段落，每个元素用 MUST 前缀逐条描述，并给出整合方案（确切空间排布）。参考元素**不能只放 frontmatter**，必须写入正文才能被后端可靠复现。

### 4.5 Prompt-Only 检查

如果 `prompt_only == true`：
- 返回成功，`data.prompt_file` 设为 prompt 文件路径，`data.mode` 设为 `"prompt_only"`
- **不进入** Step 5-7（图片生成、后处理、报告）
- 报告：`Prompt constructed (prompt-only mode). Location: {prompt_file}`

### 5. 图片生成（委托 image-generator）

本 skill **不直接执行** Gaoding/Jimeng/Agnes 生图，而是委托 `image-generator` skill：

调用 `image-generator`，传入：
- `prompt_file`：Step 4 构建的 `prompts/cover.md`
- `output_path`：目标输出路径
- `target_size`：`{target_width}x{target_height}`
- `provider`：当前 `cover_provider` 值（gaoding / jimeng / agnes）

`image-generator` 内部处理：
- 后端选择（provider 参数 > config）
- Gaoding 浏览器自动化（读 `image-generator/references/gaoding-image-generation.md`）
- Jimeng 浏览器自动化（读 `image-generator/references/jimeng-image-generation.md`）
- Agnes API 调用（`image-generator/scripts/agnes_image.py`）
- Gaoding/Jimeng 失败回退（受 `image-generator` 的 `config.backend.fallback_to_agnes` 控制，默认 false）
- 后处理：>5KB 验证 + PIL 裁剪到 target_size + 删除 _raw

返回 `{ success, data: { image_path, provider, fallback_used, ... } }`。

> **注意**：含中文文字的封面必须用 Gaoding + 万相2.7，或 Jimeng + 图片 4.7（Agnes 中文渲染不稳定）。`cover_provider` 默认 `gaoding`。
> **Jimeng 特殊约束**：即梦 prompt 不含精确像素尺寸（只用用途+比例描述），但本 skill 构建的 prompt 文件含尺寸前缀——当 `cover_provider == jimeng` 时，`image-generator` 的 Jimeng 路径会按 `references/jimeng-image-generation.md` 的 profile 格式重写 prompt（去掉精确像素，改为用途+比例描述），无需调用方特殊处理。

### 6. 后处理

后处理（>5KB 验证、PIL 裁剪、_raw 删除）已由 `image-generator` 在生成时完成。本 skill 只需读取返回的 `image_path` 确认存在。

### 7. 报告

```
Image Generated!
Provider: {provider} | Fallback: {yes/no}
Type: {type} | Palette: {palette} | Rendering: {rendering}
Text: {text} | Mood: {mood} | Font: {font}
Size: {original} → {final}
Location: {output_path}
```

## 批量并行生成

当需要同时生成多张图片（如封面 + 多张插图）时，**必须并行执行**以节省总耗时。批量生成本身由 `image-generator` skill 执行——本 skill 构建 prompt 文件 + 目标尺寸 + dimensions 列表，调用 `image-generator` 的批量接口。

- **并发上限 5 张**（image-generator 控制，避免稿定积分消耗过大和 tab 过多）。
- **所有 prompt 先落盘**：调用批量接口前完成所有图片的 Step 1-4，prompt 文件全部写入 `prompts/`。
- **Gaoding/Jimeng 串行 / Agnes 并行**：image-generator 内部根据后端决定执行策略（Gaoding 多图串行每张新 tab，~70s/张；Jimeng 多图串行每张新对话，~40-70s/张；Agnes 多图并行后台进程）。
- **混合后端 / 混合尺寸**：批次可混合 Gaoding/Jimeng/Agnes 与不同 `target_size`。

### 接口

调用方传入图片列表（非单张参数），由 `image-generator` 执行：

```json
{
  "images": [
    {
      "prompt_file": "prompts/cover.md",
      "target_size": "900x383",
      "output_path": "...",
    },
    {
      "prompt_file": "imgs/prompts/01-infographic-concept.md",
      "target_size": "1920x1080",
      "output_path": "...",
    }
  ],
  "provider": "gaoding"
}
```

`image-generator` 返回：

```json
{
  "results": [
    { "success": true, "data": { "image_path": "...", "provider": "gaoding", ... } },
    { "success": false, "error": "...", "image_id": "..." }
  ]
}
```

## 被编排调用协议

当被编排器（如 ai-news-digest）或 article-illustrator 调用时：
- 接收结构化输入（content_context, dimensions/visual_preset, target_size, cover_provider）
- 全程零交互（本 skill 始终自动完成，不存在询问环节；调用方可选传 `skip_confirmation`，但本 skill 一律忽略它）
- **单张图片**：直接执行 Step 4-7，返回结构化输出（image_path + metadata）
- **多张图片**（封面 + 插图，或多张插图）：使用"批量并行生成"流程，先完成所有 prompt 落盘，再并行提交生成
- **prompt_only 模式**：当 `prompt_only == true` 时，只执行 Steps 1-4，返回 prompt 文件路径。调用方可稍后用预构建的 prompt 调用批量生成。
- **插图 text 覆盖**：当 `target_profile == illustration` 时，`text` 和 `font` 必须按 `visual-preset-mapping.md` 的 Illustration Profile Text/Font Override 表覆盖，不能沿用封面映射的 `text: none`。调用方必须在 dimensions 中显式传入 `text` 和 `font`，或在 prompt 中包含插图类型的文字标签指令。

## 按需读取

| 文件 | 用途 | 加载时机 |
|------|------|---------|
| `references/dimensions.md` | 六维定义 | Step 3 |
| `references/style-presets.md` | 26 风格预设 | Step 3 |
| `references/compatibility-matrix.md` | 兼容性矩阵 | Step 3 |
| `references/auto-selection-rules.md` | 自动推荐规则 | Step 3 |
| `references/palette-colors.md` | 色板 hex 定义 | Step 4 |
| `references/prompt-template.md` | prompt 6 槽位结构模板 | Step 4 |
| `references/reference-images.md` | 参考图深度处理框架 | Step 2（当 references 非空时） |
| `references/visual-preset-mapping.md` | visual_preset 映射 | Step 3 |

## 确认策略

**整个流程由 agent 自动完成，不询问用户、不需要用户选择。** Agent 根据 config.json 固定值、content 信号、auto-selection-rules、偏好链自动确定维度值，直接进入生成步骤。

- **封面 palette / rendering / font 由 config.json `cover` 段固定**（`macaron` / `hand-drawn` / `handwritten`，见「关键规则 #14」），不随内容漂移、不被 preset 覆盖。仅 `type` / `mood` 由 agent 按内容信号自动裁决，`text` 默认 `none`。
- 被编排调用（ai-news-digest 等上层 skill）：零交互，结构化输入 → 结构化输出
- 直接 `/article-cover-image-generator` 调用：同样自动完成，用户如需调整风格，可在生成后要求重新生成并显式指定维度/preset

本 skill 不存在"等待用户确认"环节——`type` / `mood` 由 agent 按优先级链自动裁决，`palette` / `rendering` / `font` 由 config 固定。

## 产物结构

```
{output_dir}/
├── prompts/
│   └── cover.md              # 生成 prompt（含 YAML frontmatter）
├── {output_filename}.png      # 最终输出图片
└── (如果 Gaoding) {output_filename}_raw.png  # 中间文件（生成后删除）
```
