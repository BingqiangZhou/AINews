# Phase 2 — 双主编并行审查门禁

> 主 agent 加载本文件编排审查 + 修正循环。content-editor 和 reader 两个 agent 也要读各自合约。

## 总览：三层门禁（双主编并行）

```text
ARTICLE_FILE
    │
    ▼
[2a 机器预检]  ← validate_content_quality.py（确定性硬检）
    │ error 清零？
    ├─ 否 → 回 Phase 1 就地修（writer DRAFT 重生成）
    └─ 是 ↓
[2b 双主编并行评分]
    ├─ content-editor（5 维度 + 红线）→ scorecards/content-round-N.json
    └─ reader（3 维度）              → scorecards/reader-round-N.json
    │ （两者并行，互不依赖）
    ▼
[2c 汇总判定]
    ├─ 任一家 hard_block → revise，合并两家 fix_directives
    ├─ 两家都 pass       → pass
    └─ round≥max 仍 revise → pass with notes
```

> **双主编机制**（v2.1+）：内容主编（`agents/content-editor.md`）审**事实/逻辑/结构/分寸**（5 维度 + 红线），读者代表（`agents/reader.md`）审**阅读体验/获得感/读得下去**（3 维度）。两者**并行审查同一稿**，各自独立出 scorecard，维度不重叠。汇总时两家 hard_block 取或。

## 2a — 机器预检（确定性硬检）

复用 `article-studio/scripts/validate_content_quality.py`，**必须按当前 `article_type` 合并阈值后通过 CLI 覆盖传给脚本**（否则脚本用默认值，会与 profile 的 `content_overrides` 冲突，误报 error）。

### 阈值合并（主 agent 调用前计算）

从 `config.json` 读：
1. 基础默认：`content` 段（title_min_chars / title_max_chars / digest_max_chars / body_min_chars / body_max_chars / min_sections / max_sections）
2. 类型覆盖：`type_content_overrides.{article_type}` 段（如有则覆盖基础默认的同名字段）

合并后得到本篇文章的最终阈值，逐字段转成 CLI 参数（与本 skill 调用 `validate_content_quality.py` 的同名做法一致）。

> ⚠️ **清单模式必须合并 `type_content_overrides.news`**（`body_min_chars: 400`）。脚本的 `body_min` 默认值是 900——若忘记合并，400 字的资讯清单会被 `gongzhonghao.body_length` 硬 fail 误杀。`source_mode: transcript` + `article_type: news` 时务必走 `type_content_overrides.news` 的阈值。

### 调用命令

```bash
<py> <scripts>/validate_content_quality.py \
  --output-dir "{OUTPUT_DIR}" \
  --platform gongzhonghao \
  --report "{TEMP_DIR}/validate-round-{N}.json" \
  --title-min   {merged.title_min_chars}  --title-max   {merged.title_max_chars} \
  --summary-max {merged.digest_max_chars} \
  --body-min    {merged.body_min_chars}   --body-max    {merged.body_max_chars} \
  --min-sections {merged.min_sections}    --max-sections {merged.max_sections} \
  --min-illustrations 0
```

> `--min-illustrations 0` 是因为本 skill 不生成插图（留给下游 `article-image-studio`），避免恒定 warning 噪声。
> `{merged.X}` 由主 agent 在调用前按上一节"阈值合并"算出后替换为字面数字。
> ⚠️ **`--max-sections` 不被脚本代码强制**（`validate_content_quality.py` 只检查 `min_sections`，不检查 max）。它仅作 LLM 审查参考——多几个 `##` 主题组不该硬 fail，由内容主编的 structure 维度软性把控。

检查项（`--platform gongzhonghao`，阈值按合并后的）：
- 标题：第一行 `# ` 开头，字数在合并后的 title 范围
- 摘要：`公众号_摘要.txt` 存在，≤ 合并后的 digest 字数
- 正文：字数在合并后的 body 范围（如 howto/story/news/profile/review 上限放宽到 3000）
- 小节：`##` 数在合并后的 section 范围（如 story 可低到 1、news 可高到 8）
- AI 腔短语（动态加载 `article-studio/references/brand-config.md` 的 blocklist）
- severity：error（必须清零）/ warning

**额外检查**（本 skill 新增，主 agent 自行 grep）：
- 无 Markdown `>` 引用块（**文末 AI 声明除外**）：`grep '^>' 公众号_文章.md | grep -vE 'AI 辅助|AI 生成|RSS 采集|转录改写|作者手写|整理排版'` 必须无输出。继承 browser-publisher 公众号规范（正文不得有 `>` 引用块），但清单/盘点/转录模式要求的文末 AI 生成声明（`>` 引用块样式）是合规的，排除掉不误报。

### 2a 失败处理

- error 非空 → 不进 2b，回 Phase 1 让 writer 在当前生成内就地修复后重写（不耗 fix_round）
- 反复 2 次 2a 不过 → 进 fix 循环，记 round

### ⚠️ state.json schema 校验（已修）

`validate_content_quality.py` 的 `_validate_state_schema` 现已用白名单接受 `audio-to-social-v3`/`audio-to-social-v4`/`article-studio-v1`，且 `requested_platforms` 不再是必需键。article-studio 复用时不再触发 `STATE_SCHEMA` 误报，主 agent 直接看 `passed` 即可，无需忽略该 failure。

## 2b — 双主编并行评分（LLM 语义）

2a 通过后，主 agent **同时并行派生两个子 agent**（参照仓库 studio-flow.md 的并行调度模式）：

### 并行调度

| 子 agent | 合约 | 输入 | 输出 scorecard |
|---------|------|------|---------------|
| **内容主编** | `agents/content-editor.md` | ARTICLE_FILE + RESEARCH_FILE + article_type + round + output_dir | `scorecards/content-round-N.json` |
| **读者代表** | `agents/reader.md` | ARTICLE_FILE + article_type + round + output_dir（**不需要 RESEARCH_FILE**） | `scorecards/reader-round-N.json` |

**调度约定**（参照仓库 studio-flow.md §子 agent 调用约定 + `agents/_shared.md` 子 Agent 文件写入规则）：

1. **goal 写死完整输出路径**：两个子 agent 的 goal 里分别写死 `{OUTPUT_DIR}/scorecards/content-round-{N}.json` 和 `{OUTPUT_DIR}/scorecards/reader-round-{N}.json`（子 agent 忽略上下文路径提示）。
2. **prompt 先落盘**：两个子 agent 的审查 prompt 分别落盘 `{PROMPTS_DIR}/content-editor-round-{N}.md` 和 `{PROMPTS_DIR}/reader-round-{N}.md`（可追溯可重放）。
3. **并行触发**：在**同一条消息里**同时派生两个子 agent（一条 message 两个 Task tool call），让它们并行跑，不要串行等待。
4. **返回后立即校验**：两个子 agent 各自返回后，主 agent 立即 read_file 验证对应 scorecard 存在且非空。
5. **失败重试**：校验失败（文件不存在/为空/JSON 无效）→ 带错误上下文重新委托同一 agent（1 次重试）；仍失败 → 主 agent 自己补位生成该 scorecard（按该 agent 合约的 schema 手动填）。

> 两个子 agent **互不依赖**（读者代表不读 RESEARCH_FILE，不需要等内容主编）。它们写不同的 scorecard 文件，无写冲突。

### 内容主编评分（5 维度 + 红线）

委托 `agents/content-editor.md`。内容主编：
1. 通读 `ARTICLE_FILE`
2. 对照 `RESEARCH_FILE` 核查事实
3. 按 `references/editor-rubric.md` 给 5 维度打分（structure/accuracy/voice/format/honesty，每维 1-10，含 evidence + gaps），**各维具体锚点按 `article_type` 对应 profile 的 `rubric_focus`**（见 [type-profiles.md](type-profiles.md)）
4. 按 `references/redlines.md` 检查**本类型启用的红线子集**（见 profile 的 `redlines` 字段）
5. 落盘 `scorecards/content-round-N.json`

### 读者代表评分（3 维度）

委托 `agents/reader.md`。读者代表：
1. 模拟手机端读者通读 `ARTICLE_FILE`
2. 按 3 维度打分（reading_experience/takeaway/engagement，每维 1-10，含 evidence + gaps），标准对照 [writing-craft.md](writing-craft.md)
3. 落盘 `scorecards/reader-round-N.json`

### content-round-N.json schema（内容主编）

```json
{
  "round": 1,
  "reviewer": "content-editor",
  "article_type": "opinion",
  "redlines_active": [1, 2, 3, 4, 5, 6],
  "verdict": "pass | revise | pass with notes",
  "hard_block": false,
  "score": {
    "structure":  {"score": 8, "evidence": "第1-2段钩子开场...", "gaps": []},
    "accuracy":   {"score": 9, "evidence": "版本号 v2.1.36 与 _research §四-补2 一致", "gaps": []},
    "voice":      {"score": 7, "evidence": "第一人称在场...", "gaps": ["第4段略书面"]},
    "format":     {"score": 8, "evidence": "无 > 引用块", "gaps": []},
    "honesty":    {"score": 7, "evidence": "对 Anthropic 批评基于事实", "gaps": ["第3段'全面碾压'略一边倒"]}
  },
  "overall": 7.8,
  "min_dimension": 7,
  "issues": [
    "第3段'全面碾压 Claude Code'：REDLINE_VIOLATION 不一边倒",
    "第5段'据称翻两次船'：accuracy 可保留但建议补'据称'"
  ],
  "fix_directives": [
    {
      "target": "第3段'全面碾压 Claude Code'那句",
      "problem": "REDLINE_VIOLATION: 不一边倒——'全面碾压'未承认 CC 仍有优势",
      "fix": "改成'在我这个场景里比 CC 更顺手'，并在同段补一句承认 CC 仍领先的点（如顺畅度）"
    }
  ],
  "summary": "结构清晰、事实扎实，主要问题在第3段立场过于一边倒，改后可过。"
}
```

### reader-round-N.json schema（读者代表）

```json
{
  "round": 1,
  "reviewer": "reader",
  "article_type": "opinion",
  "verdict": "pass | revise | pass with notes",
  "hard_block": false,
  "score": {
    "reading_experience": {"score": 8, "evidence": "第1-5段节奏好，第6段略长", "gaps": ["第6段单段约140字，建议拆分"]},
    "takeaway": {"score": 7, "evidence": "能记住'工具决定下限，习惯决定上限'这句", "gaps": ["第3段略空"]},
    "engagement": {"score": 6, "evidence": "开头'随着AI发展'较平淡，第4段有走神感", "gaps": ["开头钩子弱，建议换反差/提问式", "全文仅1个记忆点，中段偏平"]}
  },
  "overall": 7.0,
  "min_dimension": 6,
  "hard_block_dimensions": ["engagement"],
  "issues": [
    "开头第1段：ENGAGEMENT_ISSUE 平铺直叙式开场，第1段就劝退",
    "第6段：READING_ISSUE 单段约140字，手机端阅读劝退"
  ],
  "fix_directives": [
    {
      "target": "开头第1段'随着 AI 的快速发展'",
      "problem": "ENGAGEMENT_ISSUE: 平铺直叙式开场，空洞宏大叙事",
      "fix": "换成提问/反差/场景代入钩子（见 writing-craft.md），opinion 推荐反差或金句钩子"
    },
    {
      "target": "第6段（约140字那段）",
      "problem": "READING_ISSUE: 单段过长，手机端一堵墙",
      "fix": "拆成2-3段，每段≤120字，长论证拆短句"
    }
  ],
  "summary": "内容扎实但开头劝退、中段节奏偏平，改钩子和拆段后体验会上来。"
}
```

> `hard_block_dimensions`（reader 独有）：触发 hard_block 的维度，只可能是 `reading_experience` 或 `engagement`（`takeaway` 低分不 block）。`hard_block==false` 时为 `[]`。

## 2c — 汇总判定

主 agent 读两个 scorecard 后，按下式汇总：

```
hard_block = content_editor.hard_block OR reader.hard_block

if round >= config.evaluation.max_fix_rounds and hard_block:
    verdict = "pass with notes"   # 避免无限循环，带保留意见放行
elif hard_block:
    verdict = "revise"             # 进 Phase 3 修正循环
else:
    verdict = "pass"               # 两家都无 hard_block → Phase 4
```

**hard_block 不可妥协**：任一家 hard_block（红线/事实编造/维度低分/阅读体验严重不足），无论第几轮都先 revise；只有"已达 max_fix_rounds 仍改不干净"才允许 `pass with notes`（且 summary 必须注明保留意见）。

### 各家 hard_block 规则

| 家 | hard_block 触发条件 |
|----|-------------------|
| **内容主编** | 任一【本类型启用的】红线违反（REDLINE_VIOLATION）OR 事实编造/夸大（FIDELITY_VIOLATION）OR 内容主编任一维度 < `pass_bar.min_per_dimension` |
| **读者代表** | `reading_experience` < `pass_bar.min_per_dimension` OR `engagement` < `pass_bar.min_per_dimension`（**`takeaway` 低分不触发**——获得感是建议性问题） |

> 设计：**事实/分寸问题归内容主编 block，阅读体验严重不足归读者代表 block**。两家维度不重叠，不会对同一问题重复 block。takeaway（获得感）低分只给 fix_directive 建议，不强制打回（文章可能本就轻量）。

## Phase 3 — 修正循环

`verdict == "revise"` 时触发：

1. **合并两家 fix_directives**：读 `scorecards/content-round-N.json` 和 `scorecards/reader-round-N.json` 的 `fix_directives`，**按优先级合并**：
   - 第一优先：内容主编的 REDLINE_VIOLATION / FIDELITY_VIOLATION（hard_block，必须改干净）
   - 第二优先：内容主编的 SCORE_BELOW_BAR + 读者代表的 READING_ISSUE / ENGAGEMENT_ISSUE（hard_block 维度）
   - 第三优先：读者代表的 TAKEAWAY_ISSUE + 两家的其他 gaps（建议性，能改就改）
2. 委托 `article-writer.md` 切 **FIX 模式**，传**合并后的 fix_directives 数组**（保持原 `article_type`）
3. writer FIX 前，**主 agent 先备份旧稿**：
   ```bash
   <py> ../ai-news-digest/scripts/backup_file.py --file "{ARTICLE_FILE}"
   ```
4. writer 覆盖 `ARTICLE_FILE` 后，重跑 2a + 2b（双主编并行），出 `scorecards/content-round-(N+1).json` + `scorecards/reader-round-(N+1).json`
5. 循环直到 `pass` / `pass with notes` 或达 `max_fix_rounds`

### fix_rounds 计数

- 2a 失败回 Phase 1 重生成 → **不计** fix_round（机器可检问题不耗主编配额）
- 任一家 revise 进 FIX → **计** 1 个 fix_round
- 默认上限 `config.evaluation.max_fix_rounds`（3）

## Phase 4 — 完成

`verdict in ("pass", "pass with notes")`：

1. 写 `公众号_摘要.txt`（writer 已写，主编可建议修订）
2. 打印报告（**汇总两家**）：
   - 审查轮次、各轮两家分数轨迹（从 `scorecards/content-round-*.json` + `scorecards/reader-round-*.json` 汇总）
   - 最终 verdict、两家 overall、各家维度分
   - 若 `pass with notes`：列出两家未解决的 notes
3. **明确告知后续步骤需手动调其他 skill**：
   - 配图/封面 → `article-image-studio`（illustrate 模式 / cover 模式）
   - 公众号草稿 → `browser-publisher`（先按其 wechat-mp.md 检查 `>` 引用块等规范）
   - 播客 → `article-to-solo-podcast`
4. `state.json.phase = "editor_passed"`
