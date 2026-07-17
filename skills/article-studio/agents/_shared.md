# 共享定义 - article-studio

所有子代理先读本文件，再读各自合同。

> **继承关系**：通用跨 skill 规则（`<py>`/ffmpeg 解析、返回格式、文件写入 5 条、通用错误码、禁用词单一源）的权威底座在 `ai-news-digest/agents/_shared_base.md`。本文件 inline 保留关键不变量，并补充本 skill 专属内容（RESEARCH_FILE 信源、分寸红线、6 类文章 profile、专属错误码 FIDELITY_VIOLATION/REDLINE_VIOLATION 等）。

## 路径常量

| 常量 | 路径 |
|------|------|
| PROJECT_ROOT | 当前工作目录（项目根目录） |
| SKILL_ROOT | `{PROJECT_ROOT}/skills/article-studio` |
| DIGEST_SCRIPTS | `{PROJECT_ROOT}/skills/ai-news-digest/scripts`（backup_file.py 在此） |
| OUTPUT_DIR | 项目目录（`articles/{YYYY-MM-DD}_{标题}/`，由 state.json.output_dir 给出） |
| RESEARCH_DIR | `{OUTPUT_DIR}/_research` |
| RESEARCH_FILE | `{RESEARCH_DIR}/事实素材与来源.md` |
| ARTICLE_FILE | `{OUTPUT_DIR}/公众号_文章.md` |
| DIGEST_FILE | `{OUTPUT_DIR}/公众号_摘要.txt` |
| PROMPTS_DIR | `{OUTPUT_DIR}/prompts` |
| SCORECARDS_DIR | `{OUTPUT_DIR}/scorecards` |
| TEMP_DIR | `{OUTPUT_DIR}/temp` |

## 统一返回格式

成功: `{ "success": true, "data": {}, "error": null, "message": "说明" }`
失败: `{ "success": false, "data": null, "error": "ERROR_CODE: 详细错误", "message": "用户可读的失败说明" }`

## 配置来源

- **本 skill 的 `config.json`**：`content`（字数/段落/小节默认阈值）、`article_types`（6 类枚举）、`default_article_type`、`type_content_overrides`（按类型的字数/小节覆盖）、`evaluation`（修正轮数/门槛/红线开关）、`research`（检索引擎/信源要求）、`environment`（复用脚本路径）、`archive`（归档根/无系列序号）。
- **`references/type-profiles.md`**：6 类文章 profile（结构骨架/rubric_focus/红线子集/voice/CTA/标题套路/字数覆盖/取材重点），按 `article_type` 加载。
- **本 skill 的 `references/brand-config.md`**：禁用 AI 腔短语 blocklist，`validate_content_quality.py` 运行时解析（品牌配置与内容质量校验脚本已随资产重分配迁入本 skill）。

`<py>` = `config.environment.conda_python`；`<scripts>` = 本 skill 的 `scripts/`（validate_content_quality.py 已随资产重分配迁入）。

## 反虚构硬约束（最高优先级）

**本 skill 的事实底座是 `_research/事实素材与来源.md`**（`stance_research` 模式=联网检索产物；`transcript` 模式=转录原文），不是 LLM 内置知识。文章代表真人作者发布，编造事实直接损害可信度。

- **文章所有事实、数据、版本号、日期、引文必须 100% 来自 `RESEARCH_FILE`**。
- 每条事实写作时必须能在 `RESEARCH_FILE` 找到对应（stance_research 模式找 bullet + 信源 URL；transcript 模式找转录原文）。
- **超出 `RESEARCH_FILE` 的细节**（如未检索到/转录中未提及的版本号、日期、引文）必须用"据……""有报道称"等模糊措辞，或删去。
- **禁止引入 `RESEARCH_FILE` 以外的知识**——即便 LLM 自己知道，也不许写进文章（transcript 模式下尤其禁止引入外部网络事实）。
- 数字/型号/引文宁可照搬 `RESEARCH_FILE` 原文，不要为顺口而改写失真。

> transcript 模式细节见 [transcript-mode.md](../references/transcript-mode.md)。

违反 = `FIDELITY_VIOLATION`（hard_block）。

## 分寸红线约束（hard_block，最高优先级，按 article_type 启用子集）

详见 `references/redlines.md`。**红线分两级，按当前 `article_type` 启用子集**（子集对照见 `references/type-profiles.md` 各 profile 的 `redlines` 字段）：

**[通用] 红线（所有类型启用）**：
1. **区分事实与观点**：不把主观判断伪装成客观事实
2. **限定词使用**：未经官方坐实的论断用"据报道/被扒出来/有报道称"；区分"风险评估"与"板上钉钉"
6. **AI 生成声明 + 时效标注**：注明信息来源与检索日期

**[立场类] 红线（仅 opinion/review 全启用；其他类型按需）**：
3. **不一边倒**：承认对方优点、承认自己工具不完善、不"全面碾压/全面替代"
4. **不阴谋论/不上纲上线**：批评基于事实，不上升到无依据的人身/政治攻击；对未回应方留余地
5. **对同行工具公平**：不贬低、具体说"哪个场景更好"、承认迁移成本与学习曲线

writer 在 DRAFT/FIX 时按当前类型子集自查，content-editor（内容主编）在 2b 评分时按当前类型子集强制检查并触发 hard_block。**不得用未启用的红线卡文章**。

## 子 Agent 文件写入规则

1. 子 agent 的 goal 中写死完整输出路径（子 agent 忽略上下文里的路径提示）。
2. 子 agent 返回后，主 agent 立即 read_file 验证输出存在且非空。
3. 验证失败 → 带错误上下文重新委托同一 agent（1 次重试）；仍失败 → 记录 state.json 并跳过。
4. **覆盖任何非 `temp/` 文件前先备份**：`<py> ../ai-news-digest/scripts/backup_file.py --file "<目标>"`（共享备份脚本，最多 3 份）。备份后才写。
5. 更新 `state.json`：先完整读取，只改目标字段，再写回整个文件。

## 禁用 AI 腔短语（blocklist）

**单一权威源**：`article-studio/references/brand-config.md` 的 `## 禁用 AI 腔短语` 段（跨 skill 共享，article-to-duo-podcast 的 `validate_duo_script.py` 也解析同一文件）。`validate_content_quality.py` 运行时从该文件解析（**非硬编码**）。生成前必读该文件；不在本文件罗列禁用词，以免与权威源漂移。

## Prompt 先落盘

所有内容 prompt（写作 prompt、修正指令）写入 `PROMPTS_DIR/` 再调用 LLM（可追溯、可重放）。

## 常见错误码

| 错误码 | 含义 | 恢复 |
|--------|------|------|
| FILE_NOT_FOUND | 输入文件不存在 | 检查路径 |
| WRITE_FAILED | 写入失败 | 检查磁盘/权限，重试 1 次 |
| INVALID_CONTENT | 字数/段落/Markdown/AI腔/>引用块 不达标 | writer 在当前生成内就地修复后重写 |
| FIDELITY_VIOLATION | 检出 `_research` 外事实 / 无信源论断 | 必须 FIX 修正，不可放行（hard_block） |
| REDLINE_VIOLATION | 分寸红线违反（6 类，见 redlines.md） | 必须 FIX 修正，不可放行（hard_block） |
| GAP_BLOCKED | `_research` 覆盖不足，关键事实缺口 | 阻塞，补检索后重跑 Phase 0 |
| RESEARCH_FAILED | 联网取材失败（检索无结果/读取失败） | 换关键词重试，或降级到已有素材 |
| QUALITY_NOT_READY | 主编评分未达门槛 | 进 fix 循环（带 scorecard） |
| SCORE_BELOW_BAR | 任一维度 < min_per_dimension | 进 fix 循环 |
