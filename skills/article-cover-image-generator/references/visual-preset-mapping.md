# Visual Preset Mapping

Maps audio-to-social `visual_preset` values to article-cover-image-generator five-dimensional defaults.

## Cover Profile Mapping (900x383)

封面默认 `text: none`，文字由平台排版系统处理。

> **⚠ 封面样式已固定**（见 SKILL.md「关键规则 #14」）：封面 `palette` / `rendering` / `font` 由 config.json `cover` 段锁定为 `macaron` / `hand-drawn` / `handwritten`（hand-drawn-edu 预设 + 手写字体）。下表的 `palette` / `rendering` / `font` 三列**对封面不再生效**——`visual_preset` 此后只用于解析 `type` / `mood`。本表保留供插图流程及历史参考。

| visual_preset | type | palette | rendering | text | mood | font |
|---------------|------|---------|-----------|------|------|------|
| `knowledge-card` | conceptual | cool | flat-vector | none | balanced | clean |
| `cozy-story` | scene | warm | painterly | none | subtle | handwritten |
| `bold-warning` | metaphor | vivid | digital | none | bold | display |
| `minimal-opinion` | minimal | mono | flat-vector | none | subtle | clean |

## Alternative Palette (secondary choice)

| visual_preset | primary palette | alternative palette |
|---------------|----------------|-------------------|
| `knowledge-card` | cool | mono |
| `cozy-story` | warm | pastel |
| `bold-warning` | vivid | duotone |
| `minimal-opinion` | mono | elegant |

## Illustration Profile Text/Font Override (1920x1080)

插图 **必须** 根据类型覆盖 `text` 和 `font` 维度。visual_preset 映射的 `text: none` 仅适用于封面；插图需要文字标签来传达信息。

| illustration_type | text | font | 理由 |
|-------------------|------|------|------|
| infographic | `text-rich` | `handwritten` | 标签 + 数据点 + 标题，文字密集 |
| flowchart | `text-rich` | `handwritten` | 步骤名 + 箭头标签 + 判断节点 |
| comparison | `title-subtitle` | `handwritten` | 左右标题 + 要点说明 |
| framework | `text-rich` | `handwritten` | 概念节点 + 关系标签 |
| timeline | `title-subtitle` | `handwritten` | 时间标签 + 事件描述 |
| scene | `title-only` | `handwritten` | 场景标题，无额外标签 |
| 其他类型 | `none` | `clean` | scene 之外的无文字类型，无需图内文字 |

**规则**：当 `target_profile == illustration` 时，无论 visual_preset 是什么，`text` 和 `font` 必须按此表覆盖。其余维度（type、palette、rendering、mood）仍使用 visual_preset 映射值。

**单一信息源**：本节是 illustration type → Text/Font 映射的唯一事实源。`article-illustrator/references/prompt-construction.md` 与 `audio-to-social/agents/illustration-prompt-agent.md` 均引用此处，不再内联该表。
