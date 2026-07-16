# AINews

一条端到端的 AI 内容自动化流水线，打包为可通过 GitHub 安装的 **Claude Code / ZCode 插件**（插件名 `ainews-pipeline`，含 11 个 skill）。每天把 RSS 信源采集的 AI 资讯，自动加工成**公众号文章 + 播客音频 + 横版视频**，并以草稿形式发布到**微信公众号 / 喜马拉雅 / 抖音**三平台。

```
RSS 信源 → 规则预筛 → 模型打分 → 事实素材 → 公众号文章 → 封面+插图+播客+视频 → 三平台草稿
```

> ⚠️ 本仓库不是传统代码项目，而是 **Claude Code / ZCode 插件**——没有 build/lint/test 流程。每个 skill 自带 Python 脚本，由 Python 解释器直接调用。给 agent 看的架构与约定见 [`AGENTS.md`](AGENTS.md)，安装说明见下方 [安装](#安装)，本 README 面向使用者。

---

## 安装

本仓库本身就是一个 Claude Code plugin marketplace（`.claude-plugin/marketplace.json` 指向自身）。两种安装方式：

### 方式一：Claude Code / ZCode（推荐）

在本仓库根目录或任意项目里：

```bash
# 1. 把本仓库注册为 marketplace
claude plugin marketplace add https://github.com/BingqiangZhou/AINews.git

# 2. 安装插件（会在 /plugin 菜单里出现 ainews-pipeline）
claude plugin install ainews-pipeline@ainews-pipeline-marketplace
```

安装/启用时，Claude Code 会弹出 **userConfig** 配置框，填三项（均可留空走默认）：

| 配置项 | 作用 | 留空时的默认 |
|--------|------|-------------|
| `conda_python` | Python 解释器绝对路径（conda/miniconda） | `python`（用 PATH 上的） |
| `ffmpeg_path` | ffmpeg 可执行文件绝对路径 | `ffmpeg`（用 PATH 上的） |
| `font_path` | CJK 字体文件（视频字幕用，如 `msyh.ttc`） | 留空=按平台自动选 |

填好后，插件的 `SessionStart` 钩子会把这些值注入 `CLAUDE_ENV_FILE`，所有 skill 的 Python 脚本通过 `AINews_PYTHON` / `AINews_FFMPEG` / `AINews_FFPROBE` / `AINews_FONT` 环境变量读取。**无需手改任何 config.json。**

### 方式二：非 Claude Code 用户（手动跑 / 纯 ZCode）

```bash
git clone https://github.com/BingqiangZhou/AINews.git
cd AINews
```

机器相关路径走环境变量（在 shell 里 export，或写进 `.envrc`/系统环境变量）：

```bash
export AINews_PYTHON="D:/Development/miniconda3/python.exe"   # 可选，默认 python
export AINews_FFMPEG="ffmpeg"                                  # 可选，默认 ffmpeg
export AINews_FONT="C:/Windows/Fonts/msyh.ttc"                 # 可选，视频字幕用
```

或者固定到某个 skill：把 `skills/<skill>/config.json` 复制为 `skills/<skill>/config.local.json`（已 gitignored）再编辑里面的 `conda_python`/`ffmpeg_path`/`font` 等字段。

### 必装系统依赖

- **Python 3.10+**（conda/miniconda 推荐）
- **ffmpeg**（含 ffprobe）——视频/音频处理必需
- **CJK 字体**——视频字幕烧录用（Windows: `msyh.ttc`；macOS: PingFang；Linux: Noto Sans CJK）
- **conda / pip 依赖**：每个 skill 的 `scripts/` 按需 `import`（`feedparser`、`faster-whisper`、`PIL`、`requests` 等），首次跑缺什么装什么即可

### 必填密钥（发布用，环境变量）

| 变量 | 用途 |
|------|------|
| `WECHAT_MP_APPID` / `WECHAT_MP_APPSECRET` | 微信公众号草稿 API |
| `MIMO_API_KEY` | MiMo TTS |
| `AGNES_API_KEY` | Agnes 图像 API |

浏览器登录态（喜马拉雅/抖音等）存于 `skills/browser-publisher/configs/browser-auth/`（gitignored），首次发布时浏览器交互登录后会自动落盘。

---

## 两个入口

| 命令 | 入口 skill | 输入 | 产出 |
|------|-----------|------|------|
| `/ai-news-digest` | **ai-news-digest**（纯编排器） | 当日 RSS AI 资讯 | AI 日报文章 + 播客 + 视频 + 三平台草稿 |
| `/audio-to-social` | **audio-to-social**（纯编排器） | 录音 / URL / YouTube / Markdown | 文章 + 播客 + 视频 + 公众号/喜马拉雅发布 |

两者共享同一套下游内容生产 skill，只是输入来源不同（RSS 自动采集 vs. 录音转录）。

---

## Skill 目录

共 11 个 skill，按职能分四类：

### 🎯 编排器（orchestrator）——只调度，不生产内容
| Skill | 职责 |
|-------|------|
| **ai-news-digest** | AI 日报主编排：RSS 采集 → 规则预筛 → 模型打分 → 事实素材 → 委派下游 → 归档 → 发布。唯一入口 `/ai-news-digest` |
| **audio-to-social** | 录音转内容包：输入归一化 → Whisper 转录 → 委派下游。也是 **配置/资产复用中枢**——很多 skill 只读复用它的 `config.json`（品牌/封面/图像/TTS） |

### ✍️ 内容生产
| Skill | 职责 |
|-------|------|
| **article-studio** | 核心写作 skill。6 类公众号文章（观点/干货/故事/资讯/人物/测评），双主编并行审查门禁。`transcript` 模式跳过联网检索、把传入文件当作唯一权威源——是编排器之间的核心胶水 |
| article-cover-image-generator | 公众号封面图（900×383），六维方法论 + 26 个风格预设 |
| article-illustrator | 文章插图（Type × Style × Palette 三维），两步委派（prepare 产 prompt + 分段定义 → render 生图回写文章） |

### 🔄 格式转换
| Skill | 职责 |
|-------|------|
| article-to-solo-podcast | 文章 → 单人独白播客脚本 + TTS 音频，10 维 rubric + 评价修正循环，迭代到市场可用。占用集号 |
| article-to-video | 文章 + 插图 + 播客音频 → 横版 16:9 视频（Ken Burns 缩放 + 字幕烧录，FFmpeg 全本地合成） |

### 📤 发布 & 🔧 共享媒体工具
| Skill | 职责 |
|-------|------|
| **browser-publisher** | **唯一**发布逻辑所在。公众号 API 建草稿 + 喜马拉雅/抖音浏览器自动化上传。任何发布需求都必须委派到这里 |
| image-generator | 图像生成后端：搞定设计（Gaoding）/ 即梦（Jimeng）浏览器自动化 + Agnes/Pollinations API |
| tts-generation | MiMo TTS 文本转语音（含语音克隆 voice profiles） |
| whisper-transcribe | Faster Whisper 音频转录（CUDA 加速，word-level 时间戳） |

---

## 流水线总览

以 `/ai-news-digest` 为例（`audio-to-social` 结构类似，把 Phase 1-5 换成转录 + transcript 模式写作）：

```
[Phase 0] 初始化：读 config → 建 articles/{YYYY-MM-DD}_AI日报/ → state.json
   ▼
[Phase 1-2] 采集 + 预筛：RSS 并发轮询 → 去重 + 源质量加权 → top 80（纯规则，零 AI 成本）
   ▼
[Phase 3] AI 打分：主模型逐条打分排序 → top 20
   ▼
[Phase 4-5] 榜单 + 事实素材：digest.md（扫一眼）+ _research/事实素材与来源.md（写作权威源）
   ▼  ⏸️ 建议此处向用户展示榜单、确认是否继续（重资产生成前的人工 gate）
[Phase 6] 文章：委派 article-studio（news + transcript + AI小周人设）→ 公众号_文章.md
   ▼
[Phase 7] 多格式并行：
   ├─ 封面（cover-generator）
   ├─ 插图（illustrator：prepare → render 回写文章）
   ├─ 播客（solo-podcast，占集号）
   └─ 视频（to-video：等插图回写 + 播客音频完成）
   ▼
[Phase 8] 归档：校验产物 + 图片压缩 + 一致性检查
   ▼  ⏸️ 发布前必须截图确认三平台
[Phase 9] 发布（可选，草稿模式）：公众号 API / 喜马拉雅浏览器 / 抖音浏览器
```

每个 skill 都内置**状态机 + 断点续跑**——`state.json` 是唯一真源，每步完成即回写，崩溃后重入自动跳过已完成阶段。

---

## 产物布局

每次运行在 `articles/{YYYY-MM-DD}_AI日报/` 下产出一整套内容（该目录已 gitignore）：

```
articles/{YYYY-MM-DD}_AI日报/
├── 公众号_文章.md          # 终稿文章（含插图引用）
├── 公众号_摘要.txt         # 一句话摘要
├── 公众号_封面.png         # 900×383 公众号封面
├── _research/
│   └── 事实素材与来源.md    # 事实底座（article-studio 的权威源）
├── imgs/                   # 文章插图 + prompts/ + outline.md + segments.json
├── _podcast/               # 播客脚本 + 标题描述 + TTS.mp3
├── _video/公众号_视频.mp4   # 横版视频
├── temp/                   # 中间产物（采集/打分/榜单）
├── prompts/                # 打分 prompt + 结果
└── state.json              # 编排器状态机
```

---

## 数据源

`configs/bestblogs-sources/sources.json` —— **1686 条 RSS 信源**（抓取自 [bestblogs.dev](https://www.bestblogs.dev)，2026-07-03 更新），其中文章类 1217 条，AI 类约 170+ 条。`sources.md` 是可读的源清单索引。

`configs/ai-news-digest/state.json` 记录每源的 `last_seen_link` 增量游标（已 gitignore，每次运行自动重写）。

---

## 环境与依赖

### 运行环境
- **平台**：Windows（win32，亦可在 macOS/Linux 运行）
- **Python**：`<py>` = 插件解析的解释器（`AINews_PYTHON` 环境变量 → 各 skill `config.environment.conda_python` → `python`）。Claude Code 下由 userConfig 自动注入。
- **ffmpeg / ffprobe**：`AINews_FFMPEG`/`AINews_FFPROBE` 环境变量 → config → PATH 上的 `ffmpeg`/`ffprobe`（视频合成、音频处理用）
- **Chrome**：由 chrome-devtools MCP 自动启动并管理登录态（图像生成 + 浏览器发布依赖）
- **Whisper**：推荐 CUDA GPU 加速（CPU 可用但慢）

### 必需环境变量
| 变量 | 用途 |
|------|------|
| `WECHAT_MP_APPID` / `WECHAT_MP_APPSECRET` | 公众号 API 草稿上传 |
| `MIMO_API_KEY` | MiMo TTS（播客 + TTS） |
| `AGNES_API_KEY` | Agnes 图像后端（回退时） |
| `POLLINATIONS_API_KEY_*` | Pollinations 图像后端（可选，双 key 轮换） |

浏览器登录态（稿定/即梦/公众号/喜马拉雅/抖音）由 Chrome 的 user-data-dir 持久化，存于 `browser-publisher/configs/browser-auth/`（已 gitignore）。

---

## 快速开始

1. **安装插件**：按上方 [安装](#安装) 任一方式装好（Claude Code 用户 `claude plugin install`；手动用户 `git clone` + 设置 `AINews_PYTHON` 等环境变量）。
2. **配置环境变量**（见上表）——Claude Code 用户在 `/plugin` userConfig 里填，手动用户 export `AINews_PYTHON`/`AINews_FFMPEG` 等。
3. **登录浏览器**：在 Chrome 里登录稿定 / 即梦 / 公众号 / 喜马拉雅 / 抖音。
4. **跑日报**：
   ```
   /ai-news-digest
   ```
   或把一段录音转成内容包：
   ```
   /audio-to-social <录音文件路径>
   ```

---

## 核心架构原则（不可违反）

1. **编排器不生产内容。** `ai-news-digest` 和 `audio-to-social` 只跑脚本 + 委派下游 skill。
2. **发布逻辑单一来源。** 所有发布代码都在 `browser-publisher`，其它 skill 一律委派，不重写。
3. **`article-studio` transcript 模式是编排器之间的胶水。** 传 `source_mode: "transcript"` + `source_file`，它跳过联网检索、把传入文件当作唯一权威源（零外部事实）。
4. **集号单一来源。** 播客集号统一读 `audio-to-social/config.json` 的 `platforms.boker_next_episode`。`ai-news-digest` 与 `audio-to-social` 共享它——**同一天不要同时跑两者**（会争集号）。只有 `bump_episode.py` 在发布成功后递增。
5. **反虚构硬约束。** 日报内容只能来自当日真实 RSS 条目，每条引用保留原信源 URL。不编造新闻、不补造事件日期。

---

## 目录结构

```
.
├── .claude-plugin/         # Claude Code / ZCode 插件清单（plugin.json + marketplace.json + hooks/）
├── skills/                 # 11 个 skill（SKILL.md + config.json + scripts/ + references/ + agents/）
├── configs/                # 运行时配置与数据（tracked，state.json 除外）
│   ├── bestblogs-sources/  # RSS 信源表（1686 条）+ 可读索引
│   └── ai-news-digest/     # RSS 增量游标 state.json（gitignored）
├── articles/               # 每次运行的产出目录（gitignored）
├── AGENTS.md               # 给 agent 看的架构与约定
└── README.md               # 本文件（给人看）
```

每个 skill 文件夹结构一致：`SKILL.md`（流程真源）+ `config.json` + `scripts/` + `references/`（按需加载）+ `agents/`（子 agent 合约），部分还有 `assets/` 或本地 `AGENTS.md`。
