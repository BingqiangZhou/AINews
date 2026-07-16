# audio-to-social — 跨 skill 共享资产枢纽（**非 skill**）

> ⚠️ **本目录已不再是 skill / 编排器。** 它没有 `SKILL.md`，没有触发词，不会被
> `/audio-to-social` 命令调用。原来的"录音/URL/YouTube → 文章+播客+视频"编排器
> 已移除。本目录现在只承载**被多个其它 skill 只读复用的共享资产**。

## 为什么还保留这个目录？

历史上有两个编排器：`ai-news-digest`（RSS 资讯线）和 `audio-to-social`（录音转内容线）。
它们共享一批底层资产（Python 工具库、品牌配置、集号计数、TTS 参考音频等），这些资产
最初落在 `audio-to-social/` 下，被 4–9 个 skill 通过 `../audio-to-social/...` 相对路径引用。

录音转内容线停用后，编排器逻辑（SKILL.md / agents / phase references / 转录脚本）被删，
但**共享资产原地保留**——迁移它们会触发 ~70 处跨 skill 路径修改，风险远高于收益。
因此本目录以"共享枢纽"身份继续存在。

## 这里有什么（共享资产清单）

| 资产 | 路径 | 消费者 |
|------|------|--------|
| Python 工具库 | `scripts/lib/utils.py` (+ `lib/__init__.py`) | whisper-transcribe、article-to-video（经 re-export shim） |
| TTS 克隆参考音频 | `scripts/voice_ref.wav` | tts-generation、article-to-solo-podcast、ai-news-digest |
| 覆盖前备份工具 | `scripts/backup_file.py` | ai-news-digest、article-studio、article-to-solo-podcast |
| 集号递增脚本 | `scripts/bump_episode.py` | ai-news-digest、article-to-solo-podcast、browser-publisher |
| 内容质检脚本 | `scripts/validate_content_quality.py` | ai-news-digest、article-studio（+ article-to-solo-podcast 同源解析 brand-config） |
| 图片压缩 | `scripts/compress_images.py` | ai-news-digest |
| 归档一致性检查 | `scripts/reconcile_media.py` | ai-news-digest |
| 品牌/禁用词单一源 | `references/brand-config.md` | ai-news-digest、article-studio、article-to-solo-podcast |
| 跨 skill agent 底座契约 | `agents/_shared_base.md` | ai-news-digest、article-studio、article-to-solo-podcast |
| 共享配置 | `config.json`（brand / cover / image / tts / `platforms.boker_next_episode` 集号单一源 / environment） | 9 个 skill + AGENTS.md + README.md |

## 修改这里的资产时

- 这些资产被多个 skill 依赖，修改前先看根 `AGENTS.md` 的 "Shared code & docs
  single-sourcing" 段，理解单一源契约。
- **不要在本目录新增编排器逻辑**。任何内容生产编排走 `skills/ai-news-digest/`。
- `config.json` 的字段保留自原编排器，标注了哪些是"hub 共享"、哪些是"已废弃编排器
  遗留"——后者无消费者，但保留以免误伤历史引用。
