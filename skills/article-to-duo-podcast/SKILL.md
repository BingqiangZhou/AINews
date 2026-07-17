---
name: article-to-duo-podcast
version: "2.0.0"
description: 把一篇已有文章（Markdown/纯文本）改写成**双人对话播客**——双主持互问互答脚本 + 双音色 TTS 音频 + 标题描述。改写导向（书面文章→双主持口吻），内置 10 维 rubric（含对话化学反应/角色平衡）+ 评价→修正迭代循环，迭代到市场可用（每维≥4、零虚构）。双 MiMo 内置音色（主播A=苏打男、主播B=冰糖女）按角色标注分段合成 + ffmpeg 拼接，可接喜马拉雅发布（需确认）。**触发场景**：用户提到"双人播客""对话播客""双主持播客""文章转播客""把文章变成播客音频""文章转喜马拉雅播客""duo podcast""文字转播客音频"，或想把一篇现成文章/笔记/博客生成双人对话播客时使用。本 skill 的输入是**文章/文本**（改写导向），不是录音/音频。
metadata:
  platforms: [boker]
---

# 文章转双人播客

本文件是本 skill 的**唯一流程真源**。子代理合约见 `agents/*.md`（共享规则见 `agents/_shared.md`），写作心法见 `references/craft.md`，评分标准见 `references/rubric.md`，TTS 分段合成见 `references/tts-chunking.md`。

把一篇**已有文章**改写成一段**市场可用的双人对话播客**。双主持互问互答、互相补充、互相抛梗——不是单人独白，也不是净化口语转录。

## 关联 Skills / 资产

- **tts-generation**：`scripts/mimo_tts.py` 的 `synthesize()`，由本 skill 的 `scripts/duo_tts.py` import 做**按角色分段的逐 turn 合成**（双音色无法一次合成，必须切段逐 turn 合成 + ffmpeg 拼接）。
- **ai-news-digest（只读复用，不改动）**：`scripts/backup_file.py`（覆盖前备份）、`scripts/bump_episode.py`（集号自增）已随资产重分配迁入 ai-news-digest。集号真源 = `ai-news-digest/config.json` 的 `platforms.boker_next_episode`。
- **browser-publisher**：喜马拉雅上传/定时发布（仅用户明确确认时）。

## 流程概览

```text
config + 文章路径 → ingest(剥噪声) → 脚本生成(大纲→分段起草双主持对话, craft 导向)
→ 机器校验 → LLM rubric 评分 → [未达标] 定向修正循环(≤3 轮)
→ 按角色标注分段双音色 TTS 合成 + ffmpeg 拼接 → 音频校验 → [用户确认] 发布
```

## 关键规则

**状态与缓存**
1. **断点续跑 + 即时持久化**：`state.json` 跟踪每阶段状态，已完成跳过；每步完成立即回写。
2. **评分可追溯**：每轮评分卡落盘 `scorecards/round-N.json`，改进轨迹可见。

**内容生成（改写导向，双人对话）**
3. **心智模型**：把书面文章改写成"两个朋友对聊"的播客，双主持有来有回地推进——不是净化口语转录，不是一人念稿一人旁听。
4. **Prompt 先落盘**：所有 prompt 写入 `prompts/` 再调 LLM/TTS。
5. **反虚构硬约束**：脚本所有事实 100% 来自源文，零编造（详见 `agents/_shared.md`）。

**脚本格式（双人对话核心约定）**
6. **角色标注**：每段台词以 `A：` 或 `B：` 开头（全角冒号，紧贴行首），冒号后即台词内容。`A`=`主播A`(苏打)、`B`=`主播B`(冰糖)。
7. **对话张力**：角色轮换频繁，禁止一人长独白（连续同角色 ≤3 段）；总轮次 ≥15；A/B 字数占比 ∈ [35%, 65%]。
8. **`[SECTION:N]` 分节标记**：保留（与单人播客一致，供 article-to-video 按插图分段切场景），独占一行，section 切换不强制换角色。

**产物**
9. 输出目录 = `<文章目录>/_podcast/`（在 workspace 内，mp3 可直接 upload）。`temp/` 存中间件，`scorecards/` 存评分卡，`prompts/` 存 prompt。
10. 覆盖任何非 `temp/` 文件前先备份（复用 `backup_file.py`，最多 3 份）。

**发布**
11. **不自动发布**。产出可发布产物后，发布到喜马拉雅需用户在本会话明确确认（遵循 repo 约定）。

## 环境配置

`<py>` = 插件解析的 Python（`AINews_PYTHON` 环境变量 → `config.environment.conda_python` → `python`）；`<scripts>` = 本 skill 的 `scripts/`。需 `MIMO_API_KEY`。ffmpeg/ffprobe 在 PATH（或 `AINews_FFMPEG`/`AINews_FFPROBE` 环境变量）。

## 状态与产物布局

状态机：`initialized → ingested → scripted → evaluated(validate→factcheck→judge) → (fixing) → audio_synthesized → audio_checked → completed`。Phase 2 在 `state.json.phase2` 记 `{conductor, hook, body, assemble, punch_up, orality, host_listen:{round,status}, meta, degraded}`（见 `references/studio-flow.md`）；Phase 3 在 `state.json.phase3` 记子状态 `{validate, factcheck, judge}`；`degraded` 非空时发布前显式提醒用户（哪些素材未就绪）。

产物（`<文章目录>/_podcast/`；全局总览见 [docs/article-manifest.md](../../../docs/article-manifest.md)）：
- `播客_脚本.txt`（含 `A：`/`B：` 角色标注 + `[SECTION:N]` 分节标记）、`播客_标题与描述.txt`、`播客_TTS.mp3`
- `sections.json`（若文章有 ## 章节：每节在 clean 文本的字符偏移，供 article-to-video 按插图分段切场景）
- `temp/outline.md`、`temp/source.txt`（含 `[SECTION:N]` 章节锚点）、`temp/script_clean.txt`（TTS 前剥离 `[SECTION:N]` 标记 + 角色标注的纯文本，给 Whisper 字幕对齐）、`prompts/*`、`scorecards/round-N.json`、`state.json`

### 按插图分段（[SECTION:N] 分节标记）

分段定义由 article-illustrator 产出在 `imgs/segments.json`（文章 ## 章节与插图的权威映射，含 illustration_meta）。**ingest 纯清洗，不注入任何分段标记**——conductor 读 segments.json 按 segment 分组 body 要点，body-writer 每节段首标 `[SECTION:N]`，标记保留进 `播客_脚本.txt`。duo_tts 在 TTS 前用 `extract_sections.py` 剥离 `[SECTION:N]` 标记，**同时剥离 `A：`/`B：` 角色标注**，落盘 `sections.json`（基于 clean 文本的字符偏移）+ `temp/script_clean.txt`。下游 article-to-video 用 Whisper 把字符偏移映射成音频时间轴，实现「按插图分段切场景」（取代脆弱的文本匹配）。无 `imgs/segments.json`（文章无 ## 章节或未跑插图）时 conductor 退回平铺要点，不标 `[SECTION:N]`。

### 插图标签覆盖校验
conductor 产出蓝图后、writers 之前，跑 `scripts/check_illustration_coverage.py` 机械校验每个有 illustration_meta.labels 的 body segment，其 labels 是否在蓝图对应 Section 中出现。这是「图里画了什么，播客就讲到什么」的事后兜底——不靠 conductor 自觉，靠代码检查。详见 `references/studio-flow.md` 流水线步骤 2。

## 执行步骤

每阶段先查 `state.json`，已完成则跳过。

| Phase | 跳过条件 | 负责 | 检查点 |
|-------|---------|------|--------|
| 0 初始化 | — | 主 agent | 建 `_podcast/` + `state.json`；读 config；从 a2s config 读 `boker_next_episode` 作集号 |
| 1 Ingest | `phase1==completed` | `scripts/ingest_article.py` | `temp/source.txt` 非空，记录字数 |
| 2 脚本生成（studio） | `phase2.meta==completed` | `references/studio-flow.md` 编排 7 agent：conductor→(hook‖body)→缝合→punch-up→orality→host-listen（≤3 轮）→meta-writer；`config.studio.enabled=false`/`fast_fallback=true` 时退回 `agents/duo-scriptwriter.md` 单 agent | `播客_脚本.txt` + `播客_标题与描述.txt` 非空，host-listen pass（或 degraded 已提醒） |
| 3a 机器预检 | `phase3.validate==completed` | `scripts/validate_duo_script.py` | 确定性硬检通过（exit 0）：字数/段落/角色标注/轮次/角色平衡/Markdown/元数据 |
| 3b 事实核查 | `phase3.factcheck==completed` | `agents/duo-factchecker.md`（联网） | `scorecards/factcheck-round-N.json`；记 `hard_block` |
| 3c 叙事评分 | `phase3.judge==completed` | `agents/duo-script-judge.md` | `scorecards/round-N.json`；记 `market_ready` |
| 4 修正循环 | `market_ready==true` 或 轮次≥max | fix_directives 路由到 studio `punch-up`+`orality-polish`（见 `studio-flow.md`）→ host-listen + judge 循环 | 每轮新 scorecard；达标即停 |
| 5 音频合成 | `phase5==completed` | `scripts/duo_tts.py` | `播客_TTS.mp3` 非空，ffprobe 时长合理（10-14 min） |
| 6 音频校验 | — | 主 agent | 时长合理、响度 -16 LUFS、**双音色交替清晰、拼接处无突变/割裂** |
| 7 发布 | 用户明确要求 | `browser-publisher` + `bump_episode.py` | 上传成功 → bump 集号 |

### 评估/修正循环细则（"不断评价不断优化"的核心）

1. Phase 3 三步：
   - **3a** 跑 `validate_duo_script.py`（确定性硬检：字数/段落/角色标注格式/轮次/角色平衡/Markdown/元数据 + 机器词警告），不过则交 writer 就地修。
   - **3b** 委托 `duo-factchecker` 联网核查脚本+源文章的高风险事实（扫双人对白），出 `scorecards/factcheck-round-N.json`，记 `hard_block`。联网失败走 soft 回退（`network_ok=false`、不阻断），发布前显式提醒用户未核实。
   - **3c** 委托 `duo-script-judge` 出 `scorecards/round-N.json`，记 `market_ready`。
   - **合并门槛**：`market_ready = judge.market_ready AND NOT factcheck.hard_block`；`fix_directives` 由 `validate_factcheck_report.merge_directives(factcheck.fix_directives, judge.fix_directives)` 去重合并（factcheck 优先），一次交给 writer FIX。
2. 若 `market_ready==false`：把**合并后的** `fix_directives`（factcheck + judge，见 item 1 合并门槛）连同当前脚本交给 `duo-scriptwriter` 的 **FIX 模式**做定向改写 → 备份旧脚本 → 覆盖 → 再跑 **3a validate + 3b factcheck + 3c judge** 出 round-(N+1)。
3. 循环直到 `market_ready==true` 或达到 `config.evaluation.max_fix_rounds`（默认 3）。
4. **市场可用门槛**（`references/rubric.md`）：10 维每维 ≥4、总分 ≥4.0、**Fidelity 零虚构**。Fidelity 违反一票否决。

### 脚本调用示例

```powershell
# Phase 1 ingest
<py> <scripts>/ingest_article.py --input "<文章>" --output "<_podcast>/temp/source.txt"

# Phase 3a 机器预检
<py> <scripts>/validate_duo_script.py --script "<_podcast>/播客_脚本.txt" --meta "<_podcast>/播客_标题与描述.txt"

# Phase 3b 校验 factcheck 报告
<py> <scripts>/validate_factcheck_report.py --report "<_podcast>/scorecards/factcheck-round-1.json"

# Phase 5 audio（脚本优先迭代达标后才跑）
<py> <scripts>/duo_tts.py --input "<_podcast>/播客_脚本.txt" --output "<_podcast>/播客_TTS.mp3"
```

## 子代理调用约定

调用 `duo-scriptwriter` / `duo-script-judge` 时：
1. 先读 `agents/{name}.md`（+ `agents/_shared.md`）。
2. goal 中**写死完整输出路径**（子 agent 忽略上下文路径提示）。
3. goal 开头含**反虚构硬约束**（所有事实仅来自 `temp/source.txt`）。
4. 启动前建 `prompts/` 并把 prompt 元信息落盘。
5. 返回后立即 read_file 验证输出非空；失败带上下文重试 1 次。

## 确认规则

- **发布（Phase 7）始终需要用户明确确认**，除非用户说"直接发布"。
- 文本生成、评估、修正、TTS 合成按 config 默认执行，不单独询问（脚本优先迭代，音频末尾才合成）。

## 脚本目录

| 脚本 | 用途 |
|------|------|
| `scripts/ingest_article.py` | Markdown→干净正文（纯清洗，不注入分段标记） |
| `scripts/check_illustration_coverage.py` | 插图标签覆盖校验：检查蓝图/脚本是否讲全了每段图的 labels（图标签→播客文本匹配） |
| `scripts/validate_duo_script.py` | 确定性预检（字数/段落/角色标注/轮次/角色平衡/Markdown/元数据/机器词） |
| `scripts/duo_tts.py` | 按角色标注切段 → 双内置音色逐 turn 合成 + ffmpeg 拼接 + 全局 loudnorm |

## 按需读取

| 文件 | 用途 |
|------|------|
| `config.json` | 品牌/双主持/TTS 双音色/字数/轮次/角色平衡/评估门槛/事实核查/集号真源/环境 |
| `references/craft.md` | 双主持对话写作心法（writer 必读） |
| `references/rubric.md` | 10 维评分（含对话化学反应/角色平衡）+ 市场可用门槛 + scorecard schema（judge 必读） |
| `references/studio-flow.md` | Phase 2 studio 编排流程（主 agent 必读） |
| `agents/studio/*.md` | 7 个 studio agent 合约（conductor/hook-writer/body-writer/punch-up/orality-polish/host-listen/meta-writer） |
| `agents/duo-scriptwriter.md` | 单 writer **--fast 回退**（默认关；`studio.enabled=false` 或 `fast_fallback=true` 时用） |
| `agents/duo-factchecker.md` | 联网事实核查合约（factchecker 必读） |
| `references/tts-chunking.md` | 双音色分段合成（无法一次合成两种音色，turn 级合成 + 拼接） |
| `agents/_shared.md` | 共享规则（反虚构/写回/备份/错误码/角色标注格式） |

## 完成检查

`state.json` 全 phase `completed`（Phase 7 除外，按需）后回查：
1. `播客_脚本.txt` 通过市场可用门槛（最终 scorecard `market_ready==true`）。
2. `播客_TTS.mp3` 存在、时长 10-14 分钟、双音色交替清晰、拼接处无突变。
3. `播客_标题与描述.txt` 元数据达标。
4. `scorecards/` 轨迹可见（round-1 → final 单调改进）。
