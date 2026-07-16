# 发布记录 publish.json（权威）

> 本文件定义 `publish.json` 的 schema 与写入约定。browser-publisher 每次发布后（无论成功/失败、无论直接调用还是编排器调用）都写它。这是「某篇文章发到哪些平台、各是什么状态」的**唯一权威记录**，`articles/README.md` 的发布状态列对齐它。

## 定位

- **路径**：`<article_dir>/publish.json`（与 `state.json` 同级，文章目录根）。
- **生命周期**：运行态，**不进 git**（`articles/` 整个被 `.gitignore` 忽略）。
- **一份文章一份**：只记这一篇文章在各平台的发布状态，不是全局日志。

## Schema（`publish-record-v1`）

```json
{
  "schema_version": "publish-record-v1",
  "article_dir": "articles/YYYY-MM-DD_<slug>",
  "tracks": {
    "wechat_mp": {
      "status": "published",
      "url": "https://mp.weixin.qq.com/s/...",
      "media_id": "MEDIA_ID",
      "published_at": "YYYY-MM-DDTHH:MM:SS+08:00"
    },
    "ximalaya": {
      "status": "published",
      "url": "https://www.ximalaya.com/sound/<sound_id>",
      "episode": <N>,
      "published_at": "YYYY-MM-DDTHH:MM:SS+08:00"
    },
    "douyin": {
      "status": "scheduled",
      "url": "https://creator.douyin.com/creator-micro/content/manage",
      "published_at": "YYYY-MM-DDTHH:MM:SS+08:00"
    }
  },
  "updated_at": "YYYY-MM-DDTHH:MM:SS+08:00"
}
```

### 字段

| 字段 | 说明 |
|------|------|
| `schema_version` | 固定 `"publish-record-v1"` |
| `article_dir` | 文章目录相对仓库根的路径（如 `articles/2026-07-12_...`） |
| `tracks` | 各平台发布状态，key 为平台内部名 |
| `tracks.{platform}.status` | 见下表枚举 |
| `tracks.{platform}.url` | 发布结果页 URL（草稿阶段可填草稿箱/管理页 URL） |
| `tracks.{platform}.published_at` | ISO 8601 带时区；定时发布为 `scheduled_at` |
| `tracks.{platform}.media_id` | 公众号专用：草稿 media_id |
| `tracks.{platform}.episode` | 喜马拉雅专用：集号 |
| `tracks.{platform}.error` | `status:"failed"` 时必填，失败原因 |
| `updated_at` | 本次写入时间，ISO 8601 带时区 |

### 平台标识

复用 browser-publisher 内部名（见 SKILL.md「支持平台」表），**不用**编排器别名（`gongzhonghao`/`boker`）：

| 内部名 | 平台 |
|--------|------|
| `wechat_mp` | 微信公众号 |
| `ximalaya` | 喜马拉雅 |
| `douyin` | 抖音 |
| `xiaohongshu` | 小红书 |
| `wechat_channels` | 微信视频号 |

### status 枚举

| status | 含义 | 典型场景 |
|--------|------|---------|
| `draft` | 草稿已建未发表 | 公众号 `wechat-mp-draft.py` 成功，尚未扫码发表 |
| `published` | 已正式发布 | 平台发布/提交成功 |
| `scheduled` | 定时发布中 | 抖音定时，`published_at` = `scheduled_at` |
| `failed` | 发布失败 | 上传超时/登录失效等，必填 `error` |
| `skipped` | 跳过 | config 关闭该平台或频率超限 |

## 写入约定

- **合并写，不全量重写**：每次只更新一个平台的 track，保留其它平台 track 不动（幂等）。
- **失败也写**：`status:"failed"` + `error`，方便后续重试和 README 反映真实状态。
- **公众号两阶段**：`wechat-mp-draft.py` 成功 → `status:"draft"`；用户后续扫码真正发表 → 更新为 `status:"published"`（发表动作在扫码环节，自动化不到，由用户或编排器后续调用脚本更新）。
- **写入工具**：用 `scripts/update_publish_record.py`（原子写 + 输入校验 + 合并），不要手写 JSON。

## 与现有 state 的关系

- **不替代** `ai-news-digest` 的 `state.json.publish.tracks`——那是编排器自己的总账，schema 不同（用 `gongzhonghao`/`boker` 别名）。
- **不污染** `article-studio` 的 `state.json`（写作器状态，无发布概念）。
- publish.json 是 browser-publisher 层的统一记录，编排器未来可读它回填自己的 state（本次不实现）。
