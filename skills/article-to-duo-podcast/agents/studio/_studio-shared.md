# Studio 共享定义 - article-to-duo-podcast 编剧室

所有 studio 子 agent 先读本文件，再读 `agents/_shared.md`（skill 级共享，含反虚构/备份/错误码/角色标注格式；其通用底座在 `ai-news-digest/agents/_shared_base.md`），再读 `references/craft.md`（双人对话写作心法真源），再读各自合约。

## 路径常量（继承自 _shared.md）

OUTPUT_DIR = `<文章目录>/_podcast`（由 state.json.output_dir 给出）；TEMP_DIR = `{OUTPUT_DIR}/temp`；PROMPTS_DIR = `{OUTPUT_DIR}/prompts`。

## 草稿与产物命名

- 蓝图：`temp/blueprint.md`（含双主持戏份分配）
- 钩子/正文中间件：`temp/hooks.txt`、`temp/body.txt`（均含 `A：`/`B：` 角色标注）
- 草稿迭代：`temp/draft_v1.txt`、`temp/draft_v2.txt`、`temp/draft_v3.txt`…（每棒产出递增版本号，均含角色标注）
- 主播审听报告：`scorecards/host-listen-round-{n}.json`
- 最终脚本：`播客_脚本.txt`（由主 agent 在 host-listen 放行后从最终 draft 复制，覆盖前备份；含 `A：`/`B：` + `[SECTION:N]`）

## 反虚构硬约束（最高优先级，继承自 _shared.md）

所有事实/数据/结论/细节必须 100% 来自 `temp/source.txt`（经 `temp/blueprint.md` 标注的事实清单传递）。禁止编造、禁止源文外知识、禁止"补全"。趣味性（比喻/夸张/人设/交锋/接梗）**只允许改表达，不允许加事实**——**双人互动不许 B 自己编数据"补充" A**。

## 角色标注格式（双人对话核心约定，所有 studio 产出必须遵守）

- 每段台词以 `A：` 或 `B：` 开头（**全角冒号 `：`**，紧贴行首，冒号后即台词内容）。
- `A` = 主播A（苏打），`B` = 主播B（冰糖）。
- `[SECTION:N]` 标记行（独占一行）**不带**角色标注——它是结构信号，非台词。
- 角色轮换频繁（连续同角色 ≤3 段），A/B 戏份大致平衡（字数占比 ∈ [35%, 65%]），总轮次 ≥15。
- 角色标注是 TTS 双音色分配的信号：`A：`→苏打音色，`B：`→冰糖音色。duo_tts 据此切段合成。

## 统一返回格式

成功: `{ "success": true, "data": { "<role>_file": "<绝对路径>", ... }, "error": null, "message": "说明" }`
失败: `{ "success": false, "data": null, "error": "<ERROR_CODE>: 详情", "message": "用户可读说明" }`

## craft 规则（要点，真源见 references/craft.md）

- **Cold open 双人优先**：A 抛钩 → B 立刻接话，快速建立"两人在聊"→ 落钩后再报家门。
- **对话张力硬规则**：有来有回、轮换频繁、禁长独白、角色平衡、互动真实、禁机械分工。
- **反 AI 味禁令**：禁三段及以上排比收尾（含 A-B 工整对句）、禁路标编号、禁套式连接词反复、禁 AI 高频词。
- **趣味性 hard mandate**：比喻/类比 ≥2、口语夸张 ≥2、**双主持交锋/接梗/吐槽 ≥2**、人设观点、具体场景。
- 每段 ≤80 字（含角色标注的冒号不计入字数），无 Markdown，无机器味词。

## 错误码（继承 + 新增）

| 错误码 | 含义 | 处理 |
|--------|------|------|
| FILE_NOT_FOUND | 输入文件不存在 | 检查路径 |
| WRITE_FAILED | 写入失败 | 重试 1 次 |
| INVALID_CONTENT | 字数/段落/角色标注/轮次/角色平衡/Markdown/机器词/反AI套路不达标 | 本 agent 就地修复后重写 |
| FIDELITY_VIOLATION | 检出虚构/源文外事实 | 删除或改回源文事实 |
| HOST_LISTEN_REJECT | host-listen 打回 | 按定向意见改后产出下一版 draft |
