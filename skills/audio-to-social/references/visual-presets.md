# Content Styles and Visual Presets

> 本文件是内容风格和视觉预设说明，由 Phase 2/3/5 按需加载。

This reference keeps text style and media style aligned across platforms.

## Content Styles

| Style | Best for | Text behavior |
|-------|----------|---------------|
| `deep_analysis` | 观点输出、行业思考、技术复盘 | 逻辑清楚，概念准确，少情绪，多因果 |
| `casual_chat` | 日常感悟、经验分享、踩坑故事 | 口语自然，保留场景和不确定感 |
| `inspirational` | 成长突破、认知转变、心态变化 | 节奏更强，有画面和共鸣，但不硬凑金句 |

## Visual Presets

| Preset | Best for | Cover |
|--------|----------|-------|
| `knowledge-card` | 方法论、工具、清单、教程 | Minimal diagram, calm contrast |
| `cozy-story` | 个人经历、复盘、日常情绪 | Warm scene, soft light |
| `bold-warning` | 避坑、提醒、冲突、反差 | High contrast symbolic cover |
| `minimal-opinion` | 观点、观察、评论、反思 | Editorial whitespace |

## Baoyu Cover Dimensions

封面生成已委托 `article-cover-image-generator` skill，使用五维方法论（Type x Palette x Rendering x Text x Mood + Font）。

→ 完整维度定义和映射见 `article-cover-image-generator/references/visual-preset-mapping.md`

## Auto Selection

- Facts include tools, steps, metrics, or repeatable methods -> `knowledge-card`
- Storyline centers on personal experience or emotion -> `cozy-story`
- Tensions include risk, mistake, warning, or strong contrast -> `bold-warning`
- Core thesis is reflective or analytical with few concrete scenes -> `minimal-opinion`

When multiple presets fit, choose the one that best serves the gongzhonghao cover image.

## Prompt Record Requirements

Every media prompt file should include:

- selected `content_style`
- selected `visual_preset`
- selected Baoyu cover dimensions
- source transcript path
- target platform and output path
- final prompt or scene/card breakdown
- backend/script parameters
