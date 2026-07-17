# Studio 共享定义 - article-to-solo-podcast 编剧室

所有 studio 子 agent 先读本文件，再读 `agents/_shared.md`（skill 级共享，含反虚构/备份/错误码；其通用底座在 `ai-news-digest/agents/_shared_base.md`），再读 `references/craft.md`（写作心法真源），再读各自合约。

> **本 skill 是专业资讯播报取向（快报 + 深读双层结构）**：客观陈述为主、信息密度高、清晰准确优先。不写闲聊腔、不堆比喻夸张、不要人设态度。第三人称客观陈述是正常腔调。结构上对标声动早咖啡：多条要闻快报 + 1 条信息量最充足的深读。

## 路径常量（继承自 _shared.md）

OUTPUT_DIR = `<文章目录>/_podcast`（由 state.json.output_dir 给出）；TEMP_DIR = `{OUTPUT_DIR}/temp`；PROMPTS_DIR = `{OUTPUT_DIR}/prompts`。

## 草稿与产物命名

- 蓝图：`temp/blueprint.md`
- 钩子/正文中间件：`temp/hooks.txt`、`temp/body.txt`
- 草稿迭代：`temp/draft_v1.txt`、`temp/draft_v2.txt`、`temp/draft_v3.txt`…（每棒产出递增版本号）
- 主播审听报告：`scorecards/host-listen-round-{n}.json`
- 最终脚本：`播客_脚本.txt`（由主 agent 在 host-listen 放行后从最终 draft 复制，覆盖前备份）

## 反虚构硬约束（最高优先级，继承自 _shared.md）

所有事实/数据/结论/细节必须 100% 来自 `temp/source.txt`（经 `temp/blueprint.md` 标注的事实清单传递）。禁止编造、禁止源文外知识、禁止"补全"。澄清（术语解释/重要性定调/自然判断）**只允许改表达或用源文已有信息，不允许加事实**。今日深读的背景/时间线/反向风险**只允许用源文已有信息或常识性解释**。

## 统一返回格式

成功: `{ "success": true, "data": { "<role>_file": "<绝对路径>", ... }, "error": null, "message": "说明" }`
失败: `{ "success": false, "data": null, "error": "<ERROR_CODE>: 详情", "message": "用户可读说明" }`

## craft 规则（双层结构要点，真源见 references/craft.md）

- **开场直接入题**：点当日最重磅事实 + 重要性定调 → 再报家门（开头 ~20s 内）→ **路线图**（预告亮点条目 + 深读主题）。
- **双层资讯简报结构**：开场→路线图→**快报**（对应文章 ## 章节，结论先行，详略起伏）→**今日深读**（标 `[SECTION:DEEPDIVE]`，数据切入+背景+三维分析+反向风险）→收束小结→CTA。
- **今日深读选题**：从快报选信息量最充足的 1 条（源文提供背景/数据/多方观点 ≥2 项）。素材不足则全快报模式（不写 DEEPDIVE 段，标 degraded）。
- **清晰度规范**：术语首次出现有解释/上下文、每条结论先行、重磅资讯有重要性定调、详略取舍有节奏。允许克制的单点类比讲清抽象概念。
- **判断机制**：关键处用**自然判断句式**（"这里值得多看一眼""要我说"），**不再用"点评："书面标签**（全篇 ≤2-3 处），必须基于已陈述事实，不夸大/不预测。
- **信源表达**：自然嵌入（"据 XX 报道"），同日新闻开场统一交代覆盖日期，同源多条合并。禁"信源是 XX，X 月 X 号"机械句式反复（全篇 ≤2 次）。
- **反 AI 味禁令**：禁工整三段及以上排比收尾、禁套式连接词反复、禁 AI 高频词（反认知/反直觉/值得注意等）。节段切换词（先看…/再看…）是结构信号，不视为套路；**深读段用维度名起句做三维分析，不用"首先/其次/最后"字面词**（brand-config.md 禁用词，validate 机械匹配报警）。自然双元素对比可保留。
- 第三人称客观陈述为主，每段 ≤80 字，无 Markdown，无机器味词。

## 错误码（继承 + 新增）

| 错误码 | 含义 | 处理 |
|--------|------|------|
| FILE_NOT_FOUND | 输入文件不存在 | 检查路径 |
| WRITE_FAILED | 写入失败 | 重试 1 次 |
| INVALID_CONTENT | 字数/段落/Markdown/机器词/反AI套路不达标 | 本 agent 就地修复后重写 |
| FIDELITY_VIOLATION | 检出虚构/源文外事实 | 删除或改回源文事实 |
| HOST_LISTEN_REJECT | host-listen 打回 | 按定向意见改后产出下一版 draft |
