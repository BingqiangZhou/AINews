---
name: browser-publisher
version: "1.0.3"
description: 浏览器自动化发布工具。通过 Chrome DevTools MCP 工具驱动由 MCP 自动启动并管理登录态的 Chrome，自动将内容发布到小红书、抖音、微信公众号、喜马拉雅。当用户提到发布内容、发布到平台、浏览器发布、自动发布、Chrome 发布、上传视频/音频到平台时使用此 skill。即使用户只提到某个平台名称加上发布/上传等关键词，也应触发此 skill。
---

# browser-publisher

通过 Chrome DevTools MCP 工具驱动 Chrome 浏览器（由 MCP 自动启动并管理登录态），将内容发布到社交媒体平台。

## 支持平台

| 平台 | 标识 | 内容类型 | 详细步骤 |
|------|------|---------|---------|
| 小红书 | `xiaohongshu` | 视频笔记（视频 + 文案描述） | `references/xiaohongshu.md` |
| 抖音 | `douyin` | 短视频（mp4 + 标题描述） | `references/douyin.md` |
| 微信公众号 | `wechat_mp` | 图文文章（Markdown + 封面图） | `references/wechat-mp.md` |
| 喜马拉雅 | `ximalaya` | 音频节目（mp3 + 标题描述） | `references/ximalaya.md` |
| 微信视频号 | `wechat_channels` | 短视频（mp4 + 标题描述，PC 端仅能从视频帧选封面） | `references/wechat-channels.md` |

平台 URL 汇总见 `references/platform-urls.md`。

## 输入文件约定

从项目目录中自动查找对应平台的文件：

| 平台 | 需要的文件 |
|------|-----------|
| 小红书 | `小红书_文案.md` + `抖音_短视频.mp4` |
| 抖音 | `抖音_短视频.mp4` + `抖音_文案.txt` |
| 公众号 | `公众号_文章.md` + `公众号_封面.png` + `公众号_摘要.txt`（可选） |
| 喜马拉雅 | `播客_TTS.mp3` + `播客_标题与描述.txt` |
| 视频号 | `视频号_文案.txt` + 视频文件（优先 `_video/公众号_视频.mp4`，回退 `抖音_短视频.mp4`） |

## 配置

读取 `config.json`（skill 目录下）获取频率限制。Chrome 实例由 chrome-devtools MCP 自动启动并管理（登录态由 MCP 的 user-data-dir 持久化），本 skill 不负责启动 Chrome。

---

## 工作流

### 0. 确定发布平台

从用户传入的参数（`ARGUMENTS`）中解析项目目录路径。

用 Glob 扫描项目目录，检查哪些平台有对应的内容文件，列出找到的文件。询问用户要发布到哪些平台。

### 1. 频率检查

检查目标平台今日发布次数（通过观察页面状态判断）：
- 每平台每天不超过 `config.rateLimit.maxPostsPerDay`（默认 3）
- 同平台间隔不少于 `config.rateLimit.minIntervalMinutes`（默认 60 分钟）

超限则告知用户并跳过该平台。

### 2. 内容审核

对每个要发布的平台，用 Read 工具读取内容文件，展示摘要让用户确认：

- 标题
- 正文预览（前 500 字）
- 文件列表
- 标签（如有）

用户输入 y 继续，n 取消，e 修改后重试。

### 3. 确保 Chrome 连接可用

Chrome 由 chrome-devtools MCP 自动启动并管理（登录态由 MCP 的 user-data-dir 持久化）。用 `mcp__chrome-devtools__list_pages` 验证 MCP 连接是否可用。

如可用，用 `mcp__chrome-devtools__navigate_page` 打开目标平台登录页，截图让用户登录。登录完成后继续。

**Chrome MCP 连接故障排查**：如果 `list_pages` 等工具无响应或报错，可能是 Chrome 进程残留/卡死。终止旧进程后重试（MCP 会重新拉起 Chrome）：
```bash
tasklist | grep chrome | head -5  # 确认有残留进程
taskkill //F //IM chrome.exe 2>/dev/null  # 终止所有 Chrome 进程
```

### 4. 逐平台发布

按用户选择的平台顺序，逐一执行发布。**每个平台的详细步骤在对应的 reference 文件中** — 发布到某平台时，先 Read 该平台的 reference 文件，然后按步骤执行。

平台间等待 1 分钟（避免频率限制）。

### 5. 写发布记录 publish.json

**每平台发布完成后（无论成功/失败）必须写一条记录**到 `<article_dir>/publish.json`——这是「某篇文章发到哪些平台、各是什么状态」的唯一权威记录，`articles/README.md` 的发布状态列对齐它。Schema 与约定见 [publish-record.md](references/publish-record.md)。

用工具脚本写入（合并写，保留其它平台 track，原子写，输入校验）：

```bash
<py> {skill_dir}/scripts/update_publish_record.py \
  --article-dir "<article_dir>" \
  --platform <wechat_mp|ximalaya|douyin|xiaohongshu|wechat_channels> \
  --status <draft|published|scheduled|failed|skipped> \
  --url "<结果页URL，可选>" \
  --media-id "<公众号media_id，可选>" \
  --episode "<喜马拉雅集号，可选>" \
  --error "<失败原因，failed时用>"
```

- **成功**：`--status published` + `--url`（公众号草稿建成用 `--status draft`；抖音定时用 `--status scheduled`）。
- **失败**：`--status failed` + `--error "<原因>"`，方便后续重试和 README 反映真实状态。
- **公众号两阶段**：`wechat-mp-draft.py` 建草稿成功记 `draft`；用户后续扫码真正发表后，再用本脚本更新为 `published`（发表动作在扫码环节，自动化不到）。

#### 写入分工（谁负责写 publish.json）

| 发布动作 | 谁写 publish.json | 说明 |
|---------|------------------|------|
| `wechat-mp-draft.py` 建草稿 | **脚本自动写**（`wechat_mp`/`draft`） | 脚本成功返回时自动调用 `update_publish_record.update_record`，agent 无需再写 |
| `wechat-mp-update-draft.py` 改标题/封面 | **脚本自动刷新**（传了 `--project-dir` 时；保持 `draft`） | 同上，刷新 media_id/title |
| 用户扫码群发公众号 | **agent 手动写**（`wechat_mp`/`published`） | 扫码是人工动作，API 不到；发表后由 agent/用户调本脚本更新为 `published` |
| 浏览器发布喜马拉雅/抖音/小红书/视频号 | **agent 手动写** | 这些平台走浏览器自动化（无独立发布脚本），agent 在发布成功后调 `update_publish_record.py` 写对应 track |

> 脚本自动写用 try/except 包裹，**写失败只 warn，不影响发布主流程**（publish.json 是记录，不是发布本身）。

### 6. 提示同步 README（收尾，仅一次）

**所有目标平台都发完、各自的 publish.json 都落盘后**，向用户提示一次（不要每个平台都提示）：

> ✅ 已写发布记录到 `<article_dir>/publish.json`。别忘了同步 `articles/README.md` 该篇的发布状态列（✅/📝）——README 是半自动视图，状态以 publish.json 为准。

README 的系列归属、一句话点评是人写的导读，本次只提示作者把发布状态列对齐 publish.json，不自动改 README。

---

## 通用操作模式（React 页面元素）

各平台页面多为 React 控制，`click`/`fill` 常失效。**发布前必读 [js-patterns.md](references/js-patterns.md)**，掌握 5 个降级技巧（click 降级 / React checkbox / native setter 注入 / contenteditable 注入 / 隐藏 file input 显示）及 `evaluate_script` 的 args 用法。

---

## 反封号措施

- **人类节奏** — 操作间适当等待 2-5 秒，不连续快速操作
- **实时感知** — 通过 snapshot/screenshot 实时观察页面状态，遇到异常立即停止

其余（复用已登录浏览器、频率控制、用户确认）已由工作流 Step 1/2/3 程序化保证。

## 故障处理

| 场景 | 处理 |
|------|------|
| 上传超时 | 等待用户在浏览器中确认后继续 |
| 元素未找到 | 重新 take_snapshot 定位，仍失败则暂停让用户手动操作 |

Session 过期、文件缺失、Chrome MCP 连接失败分别由 Step 0（文件扫描）与 Step 3（登录/连接）覆盖，见工作流。

## 发布结果回传

当编排器（如 `ai-news-digest`）调用本 skill 发布时，发布完成后回传结构化结果给编排器。

### 输入参数（编排器传入）

| 参数 | 说明 | 示例 |
|------|------|------|
| project_dir | 项目目录绝对路径 | `E:/Projects/Works/SelfMediaTools/articles/2026-07-12_...` |
| video_path | 视频文件绝对路径 | `<project_dir>/_video/公众号_视频.mp4` |
| cover_path | 封面图绝对路径 | `<project_dir>/公众号_封面.png` |
| social_metadata | 标题、描述、标签 | `{ "title": "...", "description": "...", "tags": [...] }` |
| target_platform | 目标平台标识 | `douyin` / `xiaohongshu` / `wechat_mp` / `wechat_channels` / `ximalaya` |

**定时发布（仅 douyin）**：`social_metadata` 额外携带 `publish_mode: "timed"` + `scheduled_at`（ISO，如 `"2026-06-23T06:00:00+08:00"`）。此时不立即发布，而是按 `references/douyin.md` 的「定时发布模式」勾选"定时发布"、设日期 input（值 `"YYYY-MM-DD HH:MM"`，限 now+2h ~ +14 天），再提交。返回结果用 `status: "scheduled"`、`published_at = scheduled_at`。**调用方负责保证 `scheduled_at` 落在 2h~14 天窗口内**，否则抖音前端会拒收。

### 发布完成后的动作

每个平台发布完成后（无论成功或失败）：

1. 获取当前页面 URL 作为发布结果 URL
2. 返回以下结构化结果给编排器：
   ```json
   {
     "platform": "douyin",
     "status": "published",
     "url": "https://creator.douyin.com/...",
     "published_at": "<ISO timestamp>"
   }
   ```
   定时发布成功时 `status` 为 `"scheduled"`、`published_at` 为 `scheduled_at`：
   ```json
   {
     "platform": "douyin",
     "status": "scheduled",
     "url": "https://creator.douyin.com/creator-micro/content/manage",
     "published_at": "2026-06-23T06:00:00+08:00"
   }
   ```
   或失败时：
   ```json
   {
     "platform": "douyin",
     "status": "failed",
     "error": "上传超时",
     "published_at": "<ISO timestamp>"
   }
   ```

3. **本 skill 统一负责将结果写入 `<project_dir>/publish.json`**（无论直接调用还是编排器调用）。写入用 Step 5 的 `update_publish_record.py`（合并写、原子写、输入校验），编排器**不再**二次写。Schema 与约定见 [publish-record.md](references/publish-record.md)。

### 发布流程适配

从编排器调用时（有 `social_metadata` 参数）：`social_metadata.title` → 平台标题、`.description` → 正文/描述（公众号为摘要）、`.tags` → 标签（抖音）。各平台字段细节见对应 reference。

`video_path` / `cover_path` 为绝对路径时直接使用，为项目相对路径时拼接 `project_dir`。
