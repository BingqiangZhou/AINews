# 共享定义 - audio-to-social（纯编排器）

所有子代理先读本文件，再读各自的合同。

> **继承关系**：通用跨 skill 规则（`<py>`/ffmpeg 解析、返回格式、文件写入 5 条、通用错误码、集号单一源、默认不回退）的权威底座在**本 skill** 的 `agents/_shared_base.md`。本文件 inline 保留关键不变量，并补充本 skill 专属内容（转录信源、a2s 路径常量、品牌名）。本 skill 既是编排器，也是共享资产/脚本/config 的复用枢纽（见 AGENTS.md）。

> 本 skill 是**纯编排器**：内容生产（文章/播客/封面/插图/视频）全部委派下游 skill。本 skill 自身只剩 `audio-engineer` 一个子 agent（Phase 1 转录编排）。下游委派契约见 `references/delegation-contracts.md`。

## 路径常量

| 常量 | 路径 |
|------|------|
| PROJECT_ROOT | 当前工作目录（项目根目录） |
| SKILL_ROOT | `{PROJECT_ROOT}/skills/audio-to-social` |
| OUTPUT_DIR | `articles/{YYYY-MM-DD}_{标题}`（具体值来自 state.json.output_dir；Phase 2 由 article-studio 建目录后回填） |
| SCRIPTS_DIR | `{SKILL_ROOT}/scripts` |
| TEMP_DIR | `{OUTPUT_DIR}/temp` |
| PROMPTS_DIR | `{OUTPUT_DIR}/prompts` |
| CACHE_DIR | `{OUTPUT_DIR}/cache` |
| SOURCE_ASSETS_DIR | `{OUTPUT_DIR}/temp/source_assets` |

## 日期获取规则

- 当前日期由系统提供，格式 YYYY-MM-DD
- 输出目录格式：`articles/{YYYY-MM-DD}_{标题}`（article-studio 原生布局）

## 统一返回格式

成功: `{ "success": true, "data": {}, "error": null, "message": "说明" }`
失败: `{ "success": false, "data": null, "error": "ERROR_CODE: 详细错误", "message": "用户可读的失败说明" }`

## 配置来源

所有配置统一从 `config.json` 读取，按分组组织：`brand`（品牌/存储根）、`platforms`（平台 + 集号计数器）、`content`（风格/预设）、`tts`（语音，被 article-to-solo-podcast 间接用）、`cover`（封面后端，被 cover-generator 用）、`image`（图片尺寸）、`publishing`（发布）、`environment`（工具路径/模型/API）。

## 反虚构硬约束

转录文本是 Phase 2 文章的唯一事实源。本编排器不直接生产内容（由下游 skill 保证），但传递给 article-studio 的转录必须完整、未杜撰。完整约束见 `references/platform-prompts.md` 反虚构硬约束 + `article-studio/references/transcript-mode.md`。

## 子 Agent 文件写入规则

1. 子 agent 的 goal 中写死完整输出路径
2. 子 agent 返回 completed 后，主 agent 用 read_file 验证文件存在且内容非空
3. 验证失败时：
   a. 带错误上下文重新委托同一个子 agent（1 次重试）
   b. 重试仍失败 → 主 agent 记录到 state.json（`stages.{stage}.status = "failed"`），跳过该步骤
4. 覆盖任何非 `temp/` 目录下的已有文件前，主 agent 先执行备份：
   `<py> {skill_dir}/scripts/backup_file.py --file "{目标文件路径}"`
   备份完成后才写入新内容。
5. 更新 `state.json` 时，先完整读取当前内容，只修改目标字段，再写回整个文件。禁止只写入部分字段覆盖整个文件。

## 品牌名

品牌名从 `config.json` 的 `brand.name` 读取。

## 集号管理

`config.platforms.boker_next_episode` 是集号单一来源。article-to-solo-podcast 读它定集号；`scripts/bump_episode.py` 在 Phase 7 发布成功后递增并清空 `state.json.episode_number_claimed`。中途崩溃时下次初始化复用 `episode_number_claimed`，避免集号空洞/复用。

## 禁用 AI 腔短语

权威列表见 `references/brand-config.md` 禁用 AI 腔短语（`validate_content_quality.py` 运行时从该文件解析，被 article-studio 复用做机器预检）。本文件不再内联副本，以免漂移。

## 常见错误码

| 错误码 | 含义 | 恢复策略 |
|--------|------|---------|
| FILE_NOT_FOUND | 输入文件不存在 | 检查路径；音频文件请用户重新提供 |
| WRITE_FAILED | 文件写入失败 | 检查磁盘空间和权限；重试一次 |
| VALIDATION_FAILED | 产物验证失败 | 带错误上下文重新委托子 agent/下游 skill（1 次重试）；仍失败则记录 `stages.{stage}.status="failed"` 并跳过 |
| CONFIG_NOT_FOUND | 未找到 config.json 或缺少必需配置段 | 触发引导式配置流程 |
| CACHE_INVALID | 转录缓存缺失或不可解析 | 从头重新运行，重新生成缓存 |
| SOURCE_FETCH_FAILED | URL/YouTube/Markdown 素材归一化失败 | 检查 URL 有效性；尝试手动下载；提供 Markdown 降级方案 |
| PREFLIGHT_FAILED | 发布前检查失败 | 修复报告的问题；重新运行 pre-flight 后再发布 |
| MEDIA_RECONCILIATION_FAILED | 封面/插图/引用不一致 | 修复失败项并重新运行 reconciliation |
| FFMPEG_FAILED | ffmpeg 命令失败（Phase 5 视频下游） | 验证 ffmpeg 在 PATH；检查输入文件完整性 |
