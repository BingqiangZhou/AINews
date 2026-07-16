# AGENTS.md — ai-news-digest

ZCode agents 进入本 skill 的入口说明。本 skill 是**纯编排器**（`metadata.orchestrator: true`），自身不生产内容（文章/播客/视频/封面由下游 skill 产出），靠脚本 + 两个"主 agent 直接做"的语义环节 + 委派下游 skill 完成端到端流水线。

## Agent 一览

本 skill v1 采用**"主 agent 按契约行事"模式，不 dispatch 独立子 agent**。两处"AI 参与"都是主对话模型直接做：

- **Phase 3 打分**：主模型对候选逐条打分（无独立契约，prompt 内联在 SKILL.md）
- **Phase 4.5 榜单审核**：主 agent 按 [`agents/digest-reviewer.md`](agents/digest-reviewer.md) 契约扮演榜单审核员，复核 4 维度后调 `scripts/apply_review.py` 落地修正。这是替代之前"Phase 4 后人工确认 gate"的自动化关卡。

其余 Phase 1-2、4 是确定性脚本（无 LLM 语义判断），Phase 5 是确定性转换脚本，Phase 6-9 委派下游 skill（各下游 skill 有自己的 agent 契约）。

> 对比：audio-to-social v5 用 dispatch 内联子 agent（audio-engineer）；本 skill 的两个语义环节都由主 agent 直接做，更轻量。

## 数据流

```
config.json + sources.json
        │
        ▼
Phase 0: 建项目目录 articles/{YYYY-MM-DD}_AI日报/ + state.json
        │
        ▼
Phase 1: poll_feeds.py → temp/candidates_raw.json
        │
        ▼
Phase 2: prefilter.py → temp/candidates_prefiltered.json
        │
        ▼
Phase 3: build_digest.py prompt → prompts/scoring_prompt.md
        │   （主对话模型打分 → prompts/scoring_result.json）
        └── merge_scores.py → temp/digest_ranked.json
        │
        ▼
Phase 4: build_digest.py digest → temp/digest.md
        │
        ▼
Phase 4.5: 榜单审核（主 agent 按 agents/digest-reviewer.md 复核 4 维度）→ apply_review.py 修正
        │
        ▼
Phase 5: build_research_md.py → _research/事实素材与来源.md  ← article-studio 的权威源
        │
        ▼
Phase 6: 委派 article-studio (transcript + news + AI小周) → 公众号_文章.md
        │
        ▼
Phase 7: 并行委派（照搬 audio-to-social 时序）
   7a 封面 / 7b 插图(prepare→render) / 7c 播客 / 7d 视频
        │
        ▼
Phase 8: 归档（内联：校验 + 压缩 + reconcile）
        │
        ▼
Phase 9: 委派 browser-publisher（三平台草稿发布）
```

## 单一协议

- 所有委派契约（下游 skill 输入/输出/并行规则）在 `references/delegation-contracts.md`。
- 榜单审核 agent 契约在 `agents/digest-reviewer.md`（Phase 4.5，主 agent 按其行事）。
- 所有子 agent 共享规则在 `agents/_shared.md`。
- 状态机 schema 在 `references/state-schema.md`。
- config 字段在 `references/preferences-schema.md`。

## 委派校验

委派下游 skill 后立即 read_file 验证输出产物存在且非空；失败带上下文重试 1 次，仍失败记 `stages.{stage}.status="failed"` 跳过（详见 `agents/_shared.md` 的"子 Agent 文件写入规则"）。
