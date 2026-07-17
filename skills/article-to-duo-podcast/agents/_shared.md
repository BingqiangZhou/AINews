# 共享定义 - article-to-duo-podcast

所有子代理先读本文件，再读各自合同。

> **继承关系**：通用跨 skill 规则（`<py>`/ffmpeg 解析、返回格式、文件写入 5 条、通用错误码、禁用词单一源、集号单一源）的权威底座在 `ai-news-digest/agents/_shared_base.md`。本文件 inline 保留关键不变量，并补充本 skill 专属内容（源文章信源、_podcast 路径常量、双人角色标注格式、专属错误码 TTS_FAILED/FACTCHECK_* 等）。

## 路径常量

| 常量 | 路径 |
|------|------|
| PROJECT_ROOT | 当前工作目录（运行 Claude Code 的项目根目录） |
| SKILL_ROOT | `{PROJECT_ROOT}/skills/article-to-duo-podcast` |
| OUTPUT_DIR | `<文章目录>/_podcast`（由 state.json.output_dir 给出，在 workspace 内） |
| SCRIPTS_DIR | `{SKILL_ROOT}/scripts` |
| TEMP_DIR | `{OUTPUT_DIR}/temp` |
| PROMPTS_DIR | `{OUTPUT_DIR}/prompts` |
| SCORECARDS_DIR | `{OUTPUT_DIR}/scorecards` |

## 统一返回格式

成功: `{ "success": true, "data": {}, "error": null, "message": "说明" }`
失败: `{ "success": false, "data": null, "error": "ERROR_CODE: 详细错误", "message": "用户可读的失败说明" }`

## 配置来源

统一从 `config.json` 读取分组：`brand`（品牌名 + 双主持 `hosts.{a,b}`，a=苏打/b=冰糖）、`tts`（mimo 双内置音色 `voices.{a,b}` + turn_gap_ms + 分段合成参数；**非 clone**）、`content`（字数/段落/轮次/角色平衡；机器词 blocklist 的**单一权威源**在 `article-studio/references/brand-config.md`，本 config 仅 `machine_word_blocklist_extra` 用于追加补充词）、`evaluation`（最大修正轮数/市场可用门槛）、`publishing`（集号真源/bump 脚本）、`environment`（conda_python/ffmpeg/MIMO_API_KEY）。

`<py>` = `config.environment.conda_python`；`<scripts>` = `SCRIPTS_DIR`。

## 反虚构硬约束（最高优先级）

所有内容代表真人品牌，编造事实直接损害可信度。**脚本中的所有事实、数据、结论、细节必须 100% 来自源文章**（A 和 B 的所有对白都要核对），源文模糊处保持模糊。禁止引入源文以外的知识、禁止"补全"源文没说的东西。数字/型号/结论宁可照搬源文，不要为顺口而改写失真。**双人互动不许 B 自己编数据"补充" A**——搭档反应里的补充事实也必须来自源文。

## 角色标注格式（双人对话核心约定，所有产出必须遵守）

- 每段台词以 `A：` 或 `B：` 开头（**全角冒号 `：`**，紧贴行首，冒号后即台词内容）。
- `A` = 主播A（苏打，config.brand.hosts.a），`B` = 主播B（冰糖，config.brand.hosts.b）。
- `[SECTION:N]` 标记行（独占一行）**不带**角色标注——它是结构信号，非台词。
- 角色轮换频繁（连续同角色 ≤ `config.content.max_consecutive_same_role`，默认 3），A/B 戏份大致平衡（字数占比 ∈ [35%, 65%]），总轮次 ≥ `config.content.min_turns`（默认 15）。
- 角色标注是 TTS 双音色分配的信号：`A：`→苏打音色，`B：`→冰糖音色。`duo_tts.py` 据此切段合成 + ffmpeg 拼接。`validate_duo_script.py` 运行时校验标注格式/平衡/轮次。

## 子 Agent 文件写入规则

1. 子 agent 的 goal 中写死完整输出路径（子 agent 忽略上下文里的路径提示）。
2. 子 agent 返回后，主 agent 立即 read_file 验证输出存在且非空。
3. 验证失败 → 带错误上下文重新委托同一 agent（1 次重试）；仍失败 → 记录 state.json 并跳过。
4. **覆盖任何非 `temp/` 文件前先备份**：`<py> ../ai-news-digest/scripts/backup_file.py --file "<目标>"`（复用 a2s 备份脚本，最多 3 份）。备份后才写。
5. 更新 `state.json`：先完整读取，只改目标字段，再写回整个文件。

## 禁用机器味短语（blocklist）

**单一权威源**：`article-studio/references/brand-config.md` 的 `## 禁用 AI 腔短语` 段（与 article-studio 的 `validate_content_quality.py` 同源，避免两份冲突列表）。`validate_duo_script.py` 运行时从该文件解析；`config.content.machine_word_blocklist_extra` 仅用于追加该列表之外的补充词（默认空）。生成前必读 `references/craft.md`。

## Prompt 先落盘

所有内容/媒体 prompt 写入 `PROMPTS_DIR/` 再调用 LLM/TTS（可追溯、可重放）。

## 常见错误码

| 错误码 | 含义 | 恢复 |
|--------|------|------|
| FILE_NOT_FOUND | 输入文件不存在 | 检查路径 |
| WRITE_FAILED | 写入失败 | 检查磁盘/权限，重试 1 次 |
| INVALID_CONTENT | 字数/段落/角色标注/轮次/角色平衡/Markdown/机器词不达标 | scriptwriter 在当前生成内就地修复后重写 |
| QUALITY_NOT_READY | rubric 未达市场可用门槛 | 进 fix 循环（带 scorecard） |
| FIDELITY_VIOLATION | 检出虚构/源文外事实（含 B 编造补充数据） | 必须修正，不可放行 |
| TTS_FAILED | 分段合成失败 | 检查 MIMO_API_KEY；串行重试（duo_tts 内置 3 次）；换内置音色 |
| FFMPEG_FAILED | ffmpeg 拼接失败 | 验证 ffmpeg 在 PATH；检查临时 wav 完整性 |
| FACTCHECK_NETWORK_FAILED | factcheck 联网探测失败 | soft 模式（默认）或阻断（config.evaluation.factcheck.soft_fail_on_network=false） |
| FACTCHECK_HARDBLOCK | 检出查无/过时硬事实 | hard_block=true → market_ready=false，进 FIX |
