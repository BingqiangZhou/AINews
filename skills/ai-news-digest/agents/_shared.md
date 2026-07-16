# 共享规则（所有子 agent 先读）

> 本文件定义所有子 agent 共享的路径常量、返回格式、反虚构硬约束、错误码。子 agent 委派前先加载。
>
> **继承关系**：通用跨 skill 规则（`<py>`/ffmpeg 解析、返回格式、文件写入 5 条、通用错误码、集号单一源、默认不回退）的权威底座在 `audio-to-social/agents/_shared_base.md`。本文件 inline 保留关键不变量（子 agent 不一定 follow 相对链接），并补充本 skill 专属内容（RSS 信源、AI 小周人设、日报路径常量）。

## 路径常量

> 以下路径假设 agent 在**仓库根目录**运行（CWD = 仓库根）。仓库根 = `skills/`、`configs/`、`articles/` 所在目录。

- **PROJECT_ROOT**：当前工作目录（仓库根）
- **SKILL_ROOT**：`{PROJECT_ROOT}/skills/ai-news-digest`
- **A2S_ROOT**：`{PROJECT_ROOT}/skills/audio-to-social`（复用资产来源）
- **SCRIPTS_DIR**：`{SKILL_ROOT}/scripts`
- **A2S_SCRIPTS**：`{A2S_ROOT}/scripts`
- **OUTPUT_DIR**：`{storage_root}/articles/{YYYY-MM-DD}_AI日报/`（storage_root 从 config.brand 读；默认 = PROJECT_ROOT）
- **TEMP_DIR**：`{OUTPUT_DIR}/temp`
- **PROMPTS_DIR**：`{OUTPUT_DIR}/prompts`

## 日期规则

- 所有日期取**今天**（北京时间 UTC+8），格式 `YYYY-MM-DD`。
- 采集日期 = 今天；事件日期 = RSS 条目的 published（缺失留空，不编造）。

## 配置来源

- **本 skill `config.json`**：sources / scoring / article / media / platforms / environment。
- **`audio-to-social/config.json`（只读复用）**：brand / cover / image / tts / platforms.boker_next_episode。
- **`<py>`** = `config.environment.conda_python`。

## 统一返回格式

所有子 agent 返回 JSON：

成功：
```json
{"success": true, "data": {...}, "error": null, "message": "一句话说明"}
```

失败：
```json
{"success": false, "data": null, "error": "ERROR_CODE: 详情", "message": "给人读的错误说明"}
```

## 反虚构硬约束

1. **信源驱动**：日报内容只能来自当日 RSS 采集的真实资讯条目（`temp/digest_ranked.json`），不编造榜单外新闻。
2. **信源 URL 原样保留**：不改写、不截断、不替换。
3. **事件日期**：用 RSS 条目的 published；缺失时标注"（具体日期未公布）"，不编造日期。
4. **AI 摘要忠实**：打分时生成的 ai_summary 不改写事实（只概括，不添加）。
5. **LLM 内置知识禁用**：严禁把 LLM 内置知识当作采集结果写入。

## 子 Agent 文件写入规则

1. **goal 中写死完整输出路径**（绝对路径或相对 OUTPUT_DIR 的明确路径）。
2. 返回后主 agent 用 read_file 验证输出产物存在且非空。
3. 验证失败 → 带上下文重委托 1 次 → 仍失败记 `stages.{stage}.status="failed"` 跳过。
4. 覆盖非 `temp/` 文件前先调 `<a2s_scripts>/backup_file.py` 备份。
5. 更新 `state.json` 时**先完整读、改目标字段、写回整个文件**（禁止部分写覆盖）。

## 错误码表

| 错误码 | 含义 |
|--------|------|
| `FILE_NOT_FOUND` | 输入文件不存在 |
| `WRITE_FAILED` | 写文件失败（权限/磁盘） |
| `VALIDATION_FAILED` | 质检/校验不达标 |
| `CONFIG_NOT_FOUND` | config.json 缺失或字段非法 |
| `CACHE_INVALID` | RSS 游标 state 损坏 |
| `SOURCE_FETCH_FAILED` | RSS 抓取失败（网络/源失效） |
| `PREFLIGHT_FAILED` | 发布前置检查失败 |
| `MEDIA_RECONCILIATION_FAILED` | 归档一致性检查失败 |
| `FFMPEG_FAILED` | 视频合成失败 |
| `DELEGATION_FAILED` | 下游 skill 委派失败 |

## 人设

- **AI 小周**：AI 日报主播口吻——客观简洁传递事实，克制点评，不堆形容词。区别于个人随笔的第一人称。
- 详见 `audio-to-social/references/brand-config.md` 的"人设区分"段。

## 集号管理

- **单一来源**：`audio-to-social/config.json` 的 `platforms.boker_next_episode`。
- 本 skill 只读不写（写由 `bump_episode.py` 在 Phase 9b 发布成功后做）。
- Phase 7c 播客开始前 claim 集号到 `state.json.episode_number_claimed`；Phase 9b 发布成功后递增并清空。
- **与 audio-to-social 共享同一集号源，同一天不要同时跑两者**。
