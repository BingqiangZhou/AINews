# Baoyu Skills Integration Reference

> 本文件定义 audio-to-social 如何复用 Baoyu 系列技能的模式，由主 agent 在 Phase 0/5 按需加载。

This document defines how audio-to-social uses patterns from `JimLiu/baoyu-skills` without expanding the default platform scope.

## Directly Embedded

| Baoyu skill | audio-to-social phase | Contract |
|-------------|-----------------------|----------|
| `baoyu-url-to-markdown` | Phase 0 input normalization | Convert URL, WeChat article, and generic web pages into Markdown under `temp/source_assets/`; record source URL, title, media policy, and fetch time in `index.json`. |
| `baoyu-youtube-transcript` | Phase 0/1 input normalization | Prefer YouTube captions, chapters, cover image, and metadata; write `youtube-transcript.md`, `youtube-meta.json`, and `youtube-cover.*`; fall back to Whisper only when captions are unavailable. |
| `baoyu-cover-image` | Phase 6 cover prompt + generation | Use six dimensions: `type`, `palette`, `rendering`, `text`, `mood`, `font`. Default `text` is `none`, `font` is `clean`. |
| `baoyu-format-markdown` | Phase 5 formatting | Clean Markdown/text structure after quality-gate without adding facts. |
| `baoyu-markdown-to-html` | Phase 6a-article / Phase 8 pre-flight | 现已由 xiaohu 实现（通过 `markdown_to_wechat_html.py` 包装），支持完整 markdown 语法包括图片。 |
| `baoyu-compress-image` | Phase 7 conditional compression | Compress generated images, keep originals. |

## Reference Only

| Baoyu skill | How to use the pattern |
|-------------|------------------------|
| `baoyu-article-illustrator` | Optional article illustration suggestions: analyze article structure, choose insertion points, then generate raster images with type/style/palette consistency. Do not run by default. |
| `baoyu-infographic` | Optional summary graphic for dense analytical episodes. Do not make this a default deliverable. |
| `baoyu-slide-deck` | Optional course/lecture expansion: outline first, then page-level prompts, then image generation. |
| `baoyu-translate` | Reuse quick/normal/refined thinking and glossary consistency patterns for terminology alignment across platform content. |
| `baoyu-post-to-wechat` | Reuse multi-account, pre-flight, HTML/Markdown posting, and post-publish verification ideas in Phase 8. |
| `baoyu-post-to-weibo` / `baoyu-post-to-x` | Reuse publish-type selection and browser-mode selection only; do not add Weibo/X as default targets. |
| `baoyu-wechat-summary` | Future memory layer: brand voice history, de-duplication, privacy guardrails. |
| `baoyu-diagram` / `baoyu-comic` | Optional creative media for explanatory content only when the user asks. |

## Not Default

- `baoyu-image-gen`: deprecated; prefer current runtime image generation or `baoyu-imagine` pattern.
- `baoyu-danger-gemini-web` and `baoyu-danger-x-to-markdown`: reverse-engineered API workflows; require explicit opt-in and consent, never default.

## Invariants

- Two default platforms remain `gongzhonghao` and `boker`（本文件核心边界，不因复用 Baoyu 模式而扩大默认平台范围）。
- 反虚构：所有事实必须来自转录或 `source_assets`，不得编造（见 `references/platform-prompts.md` 反虚构硬约束）。
- Prompt 先落盘：所有 prompt 先写入 `prompts/` 再生成，事后不重建（见 `SKILL.md` 关键规则「Prompt 先落盘」）。
