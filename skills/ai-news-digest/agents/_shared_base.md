# 跨 skill 子 agent 共享底座

> 本文件是所有带子 agent 的 skill（`ai-news-digest` /
> `article-studio` / `article-to-duo-podcast`）的**公共契约底座**，集中维护
> 容易跨 skill 漂移的通用规则。各 skill 的 `agents/_shared.md` 继承本文件，
> 只补充本 skill 专属内容（路径常量、人设、专属错误码、专属反虚构信源）。
>
> **阅读优先级**：本文件 = 通用底线；各 skill `_shared.md` = 专属增量。两者
> 冲突时以专属 `_shared.md` 为准（它可能针对本 skill 收紧规则）。

## `<py>` / ffmpeg / font 解析（运行时工具路径）

跨 skill 统一解析顺序（详见仓库根 `AGENTS.md` 的 "Command & runtime conventions"）：

- **`<py>`**（Python 解释器）：`AINews_PYTHON` 环境变量 → 本 skill `config.environment.conda_python` → `python` on PATH。**绝不硬编码绝对路径。**
- **ffmpeg**：`AINews_FFMPEG` 环境变量 → `config.environment.ffmpeg`（或旧扁平字段 `ffmpeg_path`）→ `ffmpeg` on PATH。
- **ffprobe**：同理，`AINews_FFPROBE` → `config.environment.ffprobe`（或 `ffprobe_path`）→ `ffprobe`。
- **CJK 字幕字体**：`AINews_FONT` → `config.font`（或 `environment.font`）→ 平台默认。

> 注：`whisper-transcribe/scripts/lib/utils.py` 的 `get_ffmpeg_path()` /
> `get_ffprobe_path()` 已兼容 `environment.*` 嵌套与旧扁平字段两种命名。

## 日期规则

- 所有日期取**今天**（北京时间 UTC+8），格式 `YYYY-MM-DD`。
- 采集/转录日期 = 今天；事件日期 = 素材源的原始日期（RSS `published` / 转录原文 / RESEARCH_FILE），缺失标注"（具体日期未公布）"，**不编造**。

## 统一返回格式（所有子 agent 必须遵守）

成功：`{ "success": true, "data": {...}, "error": null, "message": "一句话说明" }`
失败：`{ "success": false, "data": null, "error": "ERROR_CODE: 详情", "message": "给人读的错误说明" }`

## 子 Agent 文件写入规则（通用 5 条）

1. **goal 中写死完整输出路径**（绝对路径或相对 OUTPUT_DIR 的明确路径；子 agent 忽略上下文里的路径提示）。
2. 子 agent 返回后，主 agent 立即 `read_file` 验证输出产物存在且非空。
3. 验证失败 → 带错误上下文重新委托同一 agent（**1 次重试**）→ 仍失败记 `stages.{stage}.status="failed"` 并跳过。
4. **覆盖任何非 `temp/` 文件前先备份**：`<py> skills/ai-news-digest/scripts/backup_file.py --file "<目标>"`（共享备份脚本，最多 3 份）。备份后才写。
5. 更新 `state.json`：**先完整读取当前内容 → 只改目标字段 → 写回整个文件**（禁止部分写覆盖）。

## 反虚构硬约束（跨 skill 通用原则）

内容代表真人品牌，编造事实直接损害可信度。**所有事实、数据、版本号、日期、引文必须 100% 来自本 skill 的权威信源**（各 skill 的信源不同，见各自 `_shared.md`）：

- `ai-news-digest`：当日 RSS 采集条目（`temp/digest_ranked.json`），URL 原样保留。
- `article-studio`：`_research/事实素材与来源.md`（stance_research 检索产物 / transcript 模式转录原文）。
- `article-to-duo-podcast`：源文章（上游 article-studio 产物）。

通用底线：**禁止引入权威信源以外的 LLM 内置知识**；信源模糊处保持模糊；数字/型号/引文宁可照搬原文，不为顺口改写失真。

## 禁用 AI 腔短语（单一权威源）

**跨 skill 单一权威源**：`article-studio/references/brand-config.md` 的 `## 禁用 AI 腔短语` 段。

- `article-studio` 的 `validate_content_quality.py` 运行时解析该文件做机器预检。
- `article-to-duo-podcast` 的 `validate_duo_script.py` 运行时解析**同一文件**（不再读 config 的并行列表；`config.content.machine_word_blocklist_extra` 仅用于追加补充词）。
- 各 `_shared.md` / 写作工艺文档**不再内联禁用词列表**，以免与权威源漂移。扩充禁用词只改 brand-config.md 一处。

## 集号管理（episode 单一来源）

- **单一来源**：`ai-news-digest/config.json` 的 `platforms.boker_next_episode`。
- 只有 `ai-news-digest/scripts/bump_episode.py`（发布成功后）写它；其余 skill 只读。
- 播客开始前 claim 集号到 `state.json.episode_number_claimed`；发布成功后递增并清空。中途崩溃复用 `episode_number_claimed`，避免集号空洞/复用。

## "默认不回退"策略（媒体生成）

- 封面/插图/视频生成后端失败时，**默认显式上报失败、不静默降级**（不静默换后端/换风格）。
- 仅当 `config.cover.fallback_to_agnes == true`（默认 false）等显式开关打开时，才允许回退。
- 风格一致性优先于"总能出图"。

## 通用错误码（跨 skill 共享）

各 skill 在此基础上追加专属错误码（见各自 `_shared.md`）。

| 错误码 | 含义 | 通用恢复策略 |
|--------|------|-------------|
| `FILE_NOT_FOUND` | 输入文件不存在 | 检查路径 |
| `WRITE_FAILED` | 写入失败（权限/磁盘） | 检查磁盘空间和权限；重试 1 次 |
| `VALIDATION_FAILED` | 质检/校验不达标 | 带错误上下文重新委托（1 次重试）；仍失败记 failed 并跳过 |
| `CONFIG_NOT_FOUND` | config.json 缺失或字段非法 | 触发引导式配置流程 |
| `CACHE_INVALID` | 缓存（RSS 游标/转录缓存）损坏或不可解析 | 从头重新运行重建缓存 |
| `SOURCE_FETCH_FAILED` | 素材抓取/归一化失败（网络/源失效） | 检查 URL；换关键词；提供降级方案 |
| `PREFLIGHT_FAILED` | 发布前置检查失败 | 修复报告的问题后重跑 pre-flight |
| `MEDIA_RECONCILIATION_FAILED` | 归档一致性检查失败（封面/插图/引用不一致） | 修复失败项后重跑 reconciliation |
| `FFMPEG_FAILED` | ffmpeg/ffprobe 命令失败 | 验证 ffmpeg 在 PATH；检查输入文件完整性 |
| `DELEGATION_FAILED` | 下游 skill 委派失败 | 检查下游 skill 返回；1 次重试后跳过 |
