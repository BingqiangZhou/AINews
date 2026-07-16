# State Schema（ai-news-digest-v1）

> 本文件是 `state.json` 的权威 schema。编排器启动前必读，每阶段完成后立即回写。

## 设计原则

1. **粗粒度 stage + 关键产物路径**：编排器只追踪 stage 级状态 + 产物路径，下游 skill 的内部细节（如 article-studio 的审查轮次、podcast 的 10 维 rubric）由各下游 skill 自己的 state 记。
2. **即时持久化**：每 stage 完成立即回写整个 state.json（先读完整 → 改目标字段 → 写回），崩溃不丢进度。
3. **下游 state 交叉检查**：重入某 stage 时，若下游 skill 自己的 state（`_podcast/state.json`、`_video/state.json`）显示其内部已完成，也视为本 stage 完成。
4. **status 枚举**：`pending` / `running` / `completed` / `failed` / `skipped`（该产物被 config 开关关闭时）。

## 完整 schema

```json
{
  "schema_version": "ai-news-digest-v1",
  "output_dir": "articles/{YYYY-MM-DD}_AI日报/",
  "date": "YYYY-MM-DD",
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime",
  "last_failed_step": null,
  "error_message": null,

  "stages": {
    "normalize": {
      "status": "completed",
      "project_dir": "articles/{YYYY-MM-DD}_AI日报/"
    },
    "fetch": {
      "status": "completed",
      "candidates_raw": "temp/candidates_raw.json",
      "source_count": 0,
      "candidate_count": 0,
      "stats": {}
    },
    "prefilter": {
      "status": "completed",
      "candidates_file": "temp/candidates_prefiltered.json",
      "count": 0
    },
    "score": {
      "status": "completed",
      "prompt_file": "prompts/scoring_prompt.md",
      "result_file": "prompts/scoring_result.json",
      "ranked_file": "temp/digest_ranked.json",
      "final_top": 0
    },
    "digest": {
      "status": "completed",
      "digest_file": "temp/digest.md"
    },
    "review": {
      "status": "completed",
      "report_file": "temp/review-report-1.json",
      "actions_file": "temp/review_actions.json",
      "verdict": "pass_with_fixes"
    },
    "research": {
      "status": "completed",
      "research_file": "_research/事实素材与来源.md"
    },
    "article": {
      "status": "completed",
      "article_file": "公众号_文章.md",
      "summary_file": "公众号_摘要.txt",
      "article_state_file": "state.json"
    },
    "media": {
      "status": "completed",
      "cover": {"status": "completed", "file": "公众号_封面.png"},
      "illustrations": {
        "status": "completed",
        "prepare_done": true,
        "render_done": true,
        "segments_file": "imgs/segments.json",
        "count": 0,
        "items": []
      }
    },
    "podcast": {
      "status": "completed",
      "script_file": "_podcast/播客_脚本.txt",
      "audio_file": "_podcast/播客_TTS.mp3",
      "episode_number": null
    },
    "video": {
      "status": "completed",
      "video_file": "_video/公众号_视频.mp4"
    },
    "archive": {
      "status": "completed",
      "reconciliation": {},
      "compression": ""
    }
  },

  "episode_number_claimed": null,

  "publish": {
    "tracks": {
      "gongzhonghao": {"status": "pending", "media_id": null, "draft_url": null, "published_at": null},
      "boker": {"status": "pending", "episode_url": null, "published_at": null},
      "douyin": {"status": "pending", "video_url": null, "published_at": null}
    }
  },

  "publish_verification": {
    "tracks": {}
  }
}
```

## 字段说明

### 顶层
- `schema_version`：固定 `ai-news-digest-v1`，用于将来 schema 迁移。
- `output_dir`：项目根（相对 storage_root 或仓库根，取决于 config 约定）。
- `date`：日报日期（YYYY-MM-DD），默认今天，可被用户覆盖。
- `created_at` / `updated_at`：ISO 时间戳，每次回写更新 `updated_at`。
- `last_failed_step`：失败时记 stage 名（如 `"score"`），便于恢复路由。
- `error_message`：失败时的错误描述。

### stages.{stage}.status 枚举
- `pending`：未开始
- `running`：进行中（崩溃恢复时若见 running，重跑该 stage）
- `completed`：完成（重入跳过）
- `failed`：失败（记 `last_failed_step`，不自动重试）
- `skipped`：该产物被 config 开关关闭（如 `config.media.video_enabled: false` 时 `stages.video.status: "skipped"`）

### stages 各 stage 关键字段
- **fetch**：`candidates_raw`（候选列表路径）、`stats`（源抓取统计 ok/empty/not_a_feed 等）。
- **prefilter**：`candidates_file`、`count`（预筛后条数）。
- **score**：`prompt_file`（打分 prompt）、`result_file`（AI 打分结果 JSON）、`ranked_file`（合并排序后）、`final_top`。
- **digest**：`digest_file`（Markdown 榜单，给人看）。
- **review**：`report_file`（审核报告 JSON）、`actions_file`（修正指令 JSON，供 `apply_review.py` 消费；无修正时该文件可不存在）、`verdict`（`pass` / `pass_with_fixes`）。`config.scoring.review_enabled: false` 时 `status: "skipped"` 直接进 research。
- **research**：`research_file`（事实素材文件，article-studio 的权威源）。
- **article**：`article_file`、`summary_file`、`article_state_file`（article-studio 自己的 state，用于交叉检查）。
- **media**：`cover`（封面）+ `illustrations`（插图，两步：prepare_done / render_done）。`illustrations.segments_file` 是 Phase 7c 播客的前置。
- **podcast**：`audio_file`、`episode_number`（本次占用的集号）。
- **video**：`video_file`。
- **archive**：`reconciliation`（一致性检查报告）、`compression`（压缩摘要）。

### episode_number_claimed
- 本次运行占用的喜马拉雅集号（从 ai-news-digest config 的 `boker_next_episode` 读）。
- Phase 7c 播客开始前 claim，Phase 9b 发布成功后由 `bump_episode.py` 递增并清空。
- 崩溃恢复时：若 claimed 非空且对应集号未发布，复用同集号；避免集号空洞。

### publish.tracks
- 三平台发布状态：`pending` / `running` / `published` / `failed` / `skipped`。
- 每平台记 `media_id`/`url`（发布后的平台标识）+ `published_at`。

## 恢复路由

读 `state.json`，按各 stage 的 `status` 路由：

| 情况 | 恢复动作 |
|------|---------|
| 某 stage `completed` | 跳过，进下一 stage |
| 某 stage `running`（崩溃残留） | 重跑该 stage（采集/预筛/合并脚本幂等） |
| 某 stage `failed` | 按 `last_failed_step` 路由到对应阶段重试，清 `error_message` |
| 下游 skill 自己的 state 显示完成 | 视为本 stage 完成（交叉检查） |

## 断点续跑不变量

1. **集号单一来源**：`ai-news-digest/config.json` 的 `platforms.boker_next_episode`。本 skill 只读不写（写由 `bump_episode.py` 在 Phase 9b 发布成功后做）。
2. **项目目录由 Phase 0 建**：采集阶段需先落 `temp/candidates_raw.json` 等中间产物，故 Phase 0 必须先建目录。
3. **事实素材是文章的唯一权威源**：Phase 5 产出的 `_research/事实素材与来源.md` 是 Phase 6 article-studio transcript 模式的 source_file，不可被其它阶段覆盖。
