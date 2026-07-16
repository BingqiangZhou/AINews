# Phase 0: 初始化 + Phase 1: 转录

> 本文件是 SKILL.md Phase 0（归一化）+ Phase 1（转录）的详细参考，由主流程按需加载。

## Phase 0 — 归一化（内联）

### 用户输入

需要用户提供：
- **输入源**（必需）：音频文件路径，或 URL / YouTube 链接 / 公众号文章 / Markdown 草稿路径
- **主题/标题**（可选，默认在 Phase 2 由 article-studio 从转录派生）
- **target_platforms**（可选，默认 `all`）

### target_platforms

- `all` → 文章 + 封面 + 插图 + 播客 + 视频（全链路）
- `gongzhonghao` → 文章 + 封面 + 插图（跳过播客/视频）
- `boker` → 文章 + 播客（跳过封面/插图/视频；但文章仍是播客前置）

### 执行步骤

0. **遗留状态检查**（在任何 stage 跳过检查之前执行）：
   - 如果存在旧版 `state.json`（`schema_version != "audio-to-social-v4"`，含 `phase1`-`phase7`/`requested_platforms`/`topic_pending` 等 v3 字段）→ 不要尝试迁移，提示用户删除该 `state.json` 重新初始化（v3→v4 结构不兼容）。
1. **配置检查**：
   - 读取 `config.json`。如果不存在或缺少必需字段，进入**引导式环境配置流程**（见下文）。
   - 如果用户说"重新配置"，重建 `config.json`。
2. 合并配置（字段级回退）：用户本次输入 > `config.json` 中的值 > SKILL.md 中的默认值。旧版扁平字段（顶层 `brand_name`/`storage_root` 等）自动迁移为分组格式并写回（幂等）。
3. **准备转录暂存区**（`transcript_workspace`）：在项目目录（Phase 2 才建）之前，转录需要一个落脚点。用 `{storage_root}/.audio-to-social-workspace/{cache_key}/`（或一个临时目录），下建 `temp/`、`cache/`、`temp/source_assets/`。
4. 归一化输入源到 `transcript_workspace`：
   - 音频文件：拷贝到 `transcript_workspace/temp/` 并用 `scripts/cache_key.py` 计算 `cache_key`（路径安全的 hex 哈希；**唯一算法**，禁止就地拼键）。
   - 普通 URL / 公众号文章 / 网页：调用或参考 `baoyu-url-to-markdown`，抓取为 Markdown，保存到 `transcript_workspace/temp/source_assets/source-001.md` + `index.json`。
   - YouTube：调用或参考 `baoyu-youtube-transcript`，优先获取字幕/章节/封面/元数据到 `temp/source_assets/`；若无字幕再下载音频进 Phase 1 Whisper。
   - Markdown 草稿：复制到 `temp/source_assets/source-001.md`。
   - 多素材：按顺序编号 `source-001.md`、`source-002.md`，`index.json` 标注 `role: primary | supporting`。
5. 写入 `state.json` 初始状态（`schema_version: "audio-to-social-v4"`，`stages.*.status: "pending"`，`stages.normalize.status: "completed"`，`cache_key`，`source_type`，`source_assets`，`output_dir` 暂空待 Phase 2 回填）。若 workspace 中存在未完成的 `state.json` 且含 `episode_number_claimed`，复用该集号。

> **注意**：Phase 0 **不建项目目录** `articles/{YYYY-MM-DD}_{标题}/`——它由 Phase 2 的 article-studio 建。Phase 0 只准备转录暂存区。主题/标题若用户未提供，留给 Phase 2 article-studio transcript 模式从转录派生（或编排器先读转录给出一句话主题再传 `topic`）。

---

## Phase 1 — 转录（内联，委托 whisper-transcribe）

委托 `agents/audio-engineer.md` 执行。audio-engineer 在 `transcript_workspace` 下产出：
- `temp/转录文本.txt`（纯文本，每行一个 segment）
- `cache/captions.json`、`cache/transcribe_metadata.json`
- `原始录音.m4a`（音频输入时）

可复用全局缓存（`{storage_root}/.audio-to-social-cache/{cache_key}/`）跳过 Whisper。

完成后写 `state.json.stages.transcribe.status = "completed"` + `transcript_file` 路径。

### 传递给 Phase 2

Phase 2 委派 article-studio 时，把 `{transcript_workspace}/temp/转录文本.txt` 作为 `source_file` 传入（article-studio 的 researcher 会读它落盘为 `_research/事实素材与来源.md`）。article-studio 建好 `{article_dir}` 后，编排器读其 `state.json.output_dir` 回填本编排器 `state.json.output_dir` + `stages.article.article_dir`。

## 引导式环境配置流程

当 `config.json` 不存在或缺少环境字段时，使用 `AskUserQuestion` 逐步引导：

1. **Conda Python 路径**：自动检测 `where python`，让用户确认
2. **FFmpeg 路径**：自动检测 `where ffmpeg`，让用户确认
3. **字体路径**：Windows 默认 `C:\Windows\Fonts\msyh.ttc`；自动检测 `python -c "import matplotlib; print(matplotlib.get_data_path())"`
4. **Whisper 模型和 batch size**：默认 `large-v3-turbo`、`16`
5. **MiMo API 环境变量名**：默认 `MIMO_API_KEY`

引导完成后写入 `config.json` 的 `environment` 分组并验证（ffmpeg/conda_python 可执行、font 路径存在）。

**关于 `voice_ref.wav`**：TTS 声音克隆的参考音频（生物特征资产）**不随插件分发**（gitignored）。仅当使用 `--clone` 模式时才需要：若 `skills/audio-to-social/scripts/voice_ref.wav` 不存在，提示用户自行放置一段自己的参考音频（3-10 秒清晰人声，wav），或用 `--ref <path>` 指定；不用 clone 模式（builtin voice）则无需此文件。

## 首次偏好设置流程

当 `config.json` 不存在时，按 `references/preferences-schema.md` 的分组逐组询问并填入，逐字段默认值以该文件为准。
