# 发布（三平台草稿模式）

> 本文件详述 Phase 9 三平台草稿发布。本 skill 不实现任何发布代码——全部委派 `browser-publisher` skill。本文件只定义"调哪个脚本/参考哪个 references + 传什么参数 + 产物文件名如何适配"。

## 通用约定

- **发布前必须截图确认**（每平台都要截图给用户看）。
- 公众号发表（非草稿）需用户明确同意并扫码。
- 失败不自动重试，报告 `last_failed_step` + `error_message` 让用户决定。
- 每平台发布后更新 `state.json.publish.tracks.{platform}`。

## 产物文件名适配

本 skill 的产物文件名遵循 articles 约定（公众号_* / _podcast/* / _video/*），但部分发布脚本期望特定文件名：

| 本 skill 产物 | 发布脚本期望 | 适配方式 |
|--------------|-------------|---------|
| `公众号_文章.md` | `公众号_文章.md` | 一致，无需适配（wechat-mp-draft.py 直接读） |
| `公众号_封面.png` | `公众号_封面.png` | 一致 |
| `公众号_摘要.txt` | `公众号_摘要.txt` | 一致 |
| `_podcast/播客_TTS.mp3` | `播客_TTS.mp3` | ximalaya 上传时直接传 `_podcast/播客_TTS.mp3` 绝对路径 |
| `_podcast/播客_标题与描述.txt` | `播客_标题与描述.txt` | ximalaya 读标题时直接传 `_podcast/` 下路径 |
| `_video/公众号_视频.mp4` | 抖音：`抖音_短视频.mp4` | 发布前复制/重命名：`cp _video/公众号_视频.mp4 抖音_短视频.mp4`（项目根） |
| （无） | 抖音：`抖音_文案.txt` | 需生成（见下文"抖音文案生成"） |

---

## 9a 公众号草稿（API，不需浏览器）

**委派目标**：`browser-publisher` skill，调 `scripts/wechat-mp-draft.py`。

### 前置
- 环境变量 `WECHAT_MP_APPID` / `WECHAT_MP_APPSECRET`（config `environment.wechat_mp_appid_env` / `wechat_mp_appsecret_env` 引用）。
- **IP 白名单**：当前机器公网 IP 需加入公众号后台白名单（路径：公众号后台 → 设置与开发 → 基本配置 → IP 白名单）。脚本报错 `40164` 即未加白名单。

### 命令
```bash
<py> skills/browser-publisher/scripts/wechat-mp-draft.py --project-dir "<article_dir>"
```
- 脚本自动：xiaohu 解析 Markdown → 获取 token → 上传内嵌图片 → 上传封面 → 创建草稿。
- 读取 `<article_dir>/公众号_文章.md`（H1 标题）+ `公众号_摘要.txt` + `公众号_封面.png` + `imgs/*.png`（内嵌插图）。
- 默认草稿模式（`config.platforms.gongzhonghao.mode = "draft_only"`），不自动发表。

### 验证
- 草稿创建后**必须**用 `draft/get` 回读验证（标题正确、图片无转义、内嵌图显示正常）。
- 详见 `browser-publisher/references/wechat-mp.md`。

### 完成后
- `state.json.publish.tracks.gongzhonghao.status = "published"`，记 `media_id`。
- 截图草稿箱给用户确认。发表需用户扫码（不在本 skill 自动化范围内）。

---

## 9b 喜马拉雅（浏览器）

**委派目标**：`browser-publisher` skill，按 `references/ximalaya.md` 步骤操作。

### 前置
- Chrome 已登录喜马拉雅 session（Chrome 由 chrome-devtools MCP 自动启动并管理）。
- 集号：从 `ai-news-digest/config.json` 的 `platforms.boker_next_episode` 读（Phase 7c 播客已 claim 到 `state.json.episode_number_claimed`）。

### 步骤（委派 browser-publisher 执行）
1. 导航 `https://studio.ximalaya.com/upload`
2. 检测登录（页面标题"创作中心-喜马拉雅"）
3. 上传 `<article_dir>/_podcast/播客_TTS.mp3`（专辑自动选中，无需手动选）
4. 等待上传成功
5. 填标题：读 `<article_dir>/_podcast/播客_标题与描述.txt`（标题已含集号前缀 `0NNN：`）
6. 标记"是否AI合成"=是
7. 填简介（跨域 iframe，用 type_text）
8. 添加标签
9. 确认发布
10. 详见 `browser-publisher/references/ximalaya.md`

### 集号递增（发布成功后）
```bash
<py> <scripts>/bump_episode.py \
  --config skills/ai-news-digest/config.json \
  --state "<article_dir>/state.json" \
  --bump
```
- 递增 `ai-news-digest/config.json` 的 `boker_next_episode`。
- 清空 `state.json.episode_number_claimed`。
- 集号单一来源是本 skill 的 `config.json` 的 `platforms.boker_next_episode`。

### 完成后
- `state.json.publish.tracks.boker.status = "published"`，记 `episode_url`。

---

## 9c 抖音（浏览器，可定时）

**委派目标**：`browser-publisher` skill，按 `references/douyin.md` 步骤操作。

### 前置
- Chrome 已登录抖音创作者 session。
- 视频文件：`<article_dir>/_video/公众号_视频.mp4`（发布前复制为 `<article_dir>/抖音_短视频.mp4`）。
- 文案文件：需生成 `<article_dir>/抖音_文案.txt`（见下文）。

### 抖音文案生成（本 skill 负责）

article-to-video 不产出 `抖音_文案.txt`，本 skill 需在 Phase 9c 前生成。格式（`---` 分隔）：
```
口播文案内容（取播客脚本前 100 字或文章摘要）...
---
描述：今日 AI 资讯精选：{3-5 个关键事件的一句话概括}
话题：#AI日报 #人工智能 #{具体话题1} #{具体话题2}
```
- 口播文案：从 `_podcast/播客_脚本.txt` 提取开场段，或从 `公众号_摘要.txt` 取。
- 描述：50 字内，概括榜单 top 3-5 事件。
- 话题：固定 `#AI日报 #人工智能` + 从资讯标题提取 2-3 个具体话题词。
- 标题：限 30 字（从文章 H1 截断）。

### 步骤（委派 browser-publisher 执行）
1. 导航 `https://creator.douyin.com/creator-micro/content/upload`
2. 检测登录
3. 上传 `<article_dir>/抖音_短视频.mp4`
4. 等待上传完成
5. 选封面（第一帧）
6. 填标题（从文案提取，限 30 字）
7. 填描述（`---` 之后的"描述："内容）
8. 添加话题（`#话题` 后必须跟空格）
9. 设置保存权限=不允许
10. 智能章节（短视频可跳过）
11. 截图确认
12. 详见 `browser-publisher/references/douyin.md`

### 定时发布（可选）
- `publish_mode: timed` + `scheduled_at`（窗口 now+2h ~ +14d）。
- 由 config 或用户本次输入指定。

### 完成后
- `state.json.publish.tracks.douyin.status = "published"`，记 `video_url`。

---

## 发布顺序建议

1. **9a 公众号草稿**（最快，API，不依赖浏览器）——先跑，确认文章格式 OK。
2. **9b 喜马拉雅**（浏览器，需集号）——公众号确认后跑。
3. **9c 抖音**（浏览器，最慢，视频上传）——最后跑。

每步发布前截图确认，失败则停在该平台，不阻塞其它平台（各平台 tracks 独立）。

## 平台开关

`config.platforms.{platform}.enabled` 控制是否发布该平台：
- `false` → `state.json.publish.tracks.{platform}.status = "skipped"`，跳过。
- `true` → 正常发布流程。

默认三平台全开（`gongzhonghao/boker/douyin` 均 `enabled: true`）。
