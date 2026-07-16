# state.json 完整结构（v4）

> 本文件是 `state.json` 的权威 schema 定义。SKILL.md 中只保留要点概述。

> **v4 变更说明**：本 skill 重构为**纯编排器**后，state 从「9 phase 细粒度追踪」瘦身为「编排视角的粗粒度 stage 追踪」。内容生产的内部状态（主编评分、播客 10 维 rubric、视频 5 阶段）由各下游 skill 自己的 state 记录（`_podcast/state.json`、`_video/state.json`、article-studio `state.json`），本编排器只在 `stages.*.status` 上追踪委派是否成功。`schema_version` 从 `audio-to-social-v3` bump 到 `audio-to-social-v4`。
>
> **注意**：`config.json` 的 `schema_version` 与本 state 的 `schema_version` 解耦——`validate_content_quality.py` 仍 pin 在 `audio-to-social-v3`（它现在只被 article-studio 复用，后者已文档化忽略其 `STATE_SCHEMA` 误报）。本编排器自身不再调用该脚本做质量校验。

```json
{
  "schema_version": "audio-to-social-v4",
  "output_dir": "articles/{YYYY-MM-DD}_{标题}",
  "source_type": "audio | url | youtube | wechat_article | markdown",
  "source_assets": [],
  "cache_key": "",
  "stages": {
    "normalize": {
      "status": "completed"
    },
    "transcribe": {
      "status": "pending",
      "transcript_file": "temp/转录文本.txt",
      "reuse_cache": false,
      "source_transcript": "whisper | youtube | source_assets"
    },
    "article": {
      "status": "pending",
      "article_dir": "",
      "article_file": "",
      "digest_file": "",
      "source_mode": "transcript",
      "article_type": "opinion"
    },
    "media": {
      "status": "pending",
      "cover": {
        "status": "pending",
        "output_path": ""
      },
      "illustrations": {
        "status": "pending",
        "prepare_done": false,
        "render_done": false,
        "segments_file": "",
        "count": 0,
        "items": []
      }
    },
    "podcast": {
      "status": "pending",
      "script_file": "",
      "meta_file": "",
      "audio_file": "",
      "episode_number": null
    },
    "video": {
      "status": "pending",
      "video_file": ""
    },
    "archive": {
      "status": "pending",
      "reconciliation": { "status": "pending", "failures": [] },
      "compression": "pending"
    }
  },
  "episode_number_claimed": null,
  "publish": { "tracks": {} },
  "publish_verification": { "tracks": {} }
}
```

## 字段说明

| 字段 | 说明 |
|------|------|
| `schema_version` | 固定 `"audio-to-social-v4"`。本编排器 state。 |
| `output_dir` | 项目根 `articles/{YYYY-MM-DD}_{标题}/`。Phase 2 由 article-studio 建目录后回填。 |
| `source_type` | 输入类型（audio/url/youtube/wechat_article/markdown）。 |
| `source_assets` | 归一化后的素材清单（URL/YT/MD 输入）。 |
| `cache_key` | Whisper 转录缓存键（`scripts/cache_key.py` 算出）。 |
| `stages.normalize.status` | Phase 0 归一化（内联）。 |
| `stages.transcribe.status` | Phase 1 转录（内联，委托 whisper-transcribe）。`transcript_file` 指向转录文本；`reuse_cache` 标记是否复用缓存。 |
| `stages.article.status` | Phase 2 文章（委派 article-studio transcript 模式）。`article_dir` 由 article-studio 建目录后回填——后续所有阶段在此目录下操作。 |
| `stages.media.status` | Phase 3 媒体。`cover.output_path` 记封面。`illustrations` 两步：`prepare_done`（3b-prepare 完成，segments.json 就绪，Phase 4 的前置）、`render_done`（3b-render 完成，PNG 生成+文章回写）、`segments_file` 指向 segments.json。 |
| `stages.podcast.status` | Phase 4 播客（委派 article-to-solo-podcast）。**前置：`illustrations.prepare_done == true`**（conductor 读 segments.json）。`episode_number` 记录所用集号。 |
| `stages.video.status` | Phase 5 视频（委派 article-to-video 5 CLI）。`video_file` 指向最终 mp4。 |
| `stages.archive.status` | Phase 6 归档（内联 reconcile ‖ compress）。 |
| `episode_number_claimed` | Phase 4 播客写入当前集号；Phase 7 发布成功后由 `bump_episode.py` 递增 `config.platforms.boker_next_episode` 并清空。中途崩溃时下次初始化复用该集号，避免集号空洞/复用。 |
| `publish.tracks` / `publish_verification.tracks` | Phase 7 发布（委派 browser-publisher，用户显式触发）。 |

## 断点续跑语义

- **启动前必读 state**：每个 stage 若 `status == "completed"` 直接跳过。
- **下游 state 交叉检查**：重入某 stage 时，若其下游 skill 自己的 state（`_podcast/state.json` 的 phase、`_video/state.json` 的 phase、article-studio `state.json` 的 phase）显示已完成，视为本 stage 完成，无需重跑。
- **即时持久化**：每 stage 完成立即回写整个 state.json（先读完整 → 改目标字段 → 写回），崩溃不丢进度。

## 与旧版（v3）的差异

- 移除 `topic_name`/`topic_pending`/`requested_platforms`/`content_style`/`visual_preset`/`publish_preflight` 顶层字段（编排器不再需要细粒度平台追踪；visual_preset 仍从 config 读传给下游）。
- 移除 `phase1`-`phase7` 细粒度结构（含 `phase4.tracks.{platform}.quality`、`phase6.prompt/article/generate/parallel`）——这些内部状态由下游 skill 各自的 state 记录。
- 新增扁平 `stages.{stage}` 结构，每 stage 只记 `status` + 关键产物路径。
- `output_dir` 从 `{storage_root}/YYYY-MM/YYYY-MM-DD_随笔_主题名` 改为 `articles/{YYYY-MM-DD}_{标题}`（article-studio 原生布局）。
