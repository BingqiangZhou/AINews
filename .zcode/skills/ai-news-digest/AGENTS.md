# AGENTS.md — ai-news-digest

ZCode agents 进入本 skill 的入口说明。本 skill 是**纯编排器**（`metadata.orchestrator: true`），自身不生产内容，靠脚本（Phase 1-5）+ 委派下游 skill（Phase 6-9）完成端到端流水线。

## Agent 一览

本 skill **v1 不使用内联子 agent**——Phase 1-5 是确定性脚本（无 LLM 语义判断），Phase 6-9 是委派下游 skill（各下游 skill 有自己的 agent 契约）。唯一的"AI 参与"是 Phase 3 的打分（主对话模型直接做，不派子 agent）。

> 对比：audio-to-social v5 有 1 个内联子 agent（audio-engineer 做转录编排）；本 skill 因采集层全部脚本化，无需内联子 agent。

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
- 所有子 agent 共享规则在 `agents/_shared.md`。
- 状态机 schema 在 `references/state-schema.md`。
- config 字段在 `references/preferences-schema.md`。

## 委派校验

委派下游 skill 后立即 read_file 验证输出产物存在且非空；失败带上下文重试 1 次，仍失败记 `stages.{stage}.status="failed"` 跳过（详见 `agents/_shared.md` 的"子 Agent 文件写入规则"）。
