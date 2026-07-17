# Studio 编排流程（Phase 2）

> SKILL.md Phase 2 的细化真源。主 agent 按此编排 studio。
> **双人对话版**：各 agent 产出的是**双主持对话**（`A：`/`B：` 角色标注），不是独白。

## 流水线
1. **conductor**（读 source + `imgs/segments.json`）→ `temp/blueprint.md`。
   - conductor 读 segments.json 按 segment 分组要点，据 illustration_meta（type/title_text/labels）让要点和图内容对齐。
   - **双人专属**：蓝图标注每节要点的**主推角色**（A/B）+ 搭档反应建议（追问/补充/反驳），供 body-writer 写对话往返。
2. **⛔ 插图标签覆盖校验**（conductor 之后，writers 之前）：跑 `scripts/check_illustration_coverage.py` 校验蓝图的每个 Section 是否覆盖了对应图的 labels。
   ```bash
   <py> scripts/check_illustration_coverage.py \
     --segments <文章目录>/imgs/segments.json \
     --script <output_dir>/temp/blueprint.md
   ```
   - 默认 warning：覆盖率 < 100% 时在报告里标出缺失标签，但**不中断**——把缺失清单反馈给 conductor 要求补充要点（重跑 conductor 一次）。仍不全则放行，记 `phase2.degraded=['label_coverage_incomplete']`。
   - `--strict` 模式：有缺失即中断，要求修正后才继续。
   - 无 segments.json 或无 illustration_meta → 跳过校验（向下兼容）。
3. **并行**：`hook-writer`（→ `temp/hooks.txt`，双人 cold open 对话）+ `body-writer`（→ `temp/body.txt`，双人正文对话），同读 blueprint。
4. **缝合**（主 agent，机械）：按 blueprint 顺序拼 → `temp/draft_v1.txt`：
   - 先取 hook-writer 的 `[COLD_OPEN]` + `[BRAND_INTRO]` 段（已是双人对话）。
   - 接 body-writer 的 `[BODY]` 段，其中 body-writer 留的 `[MIDHOOK@<位置标>]` 占位行，逐个用 hook-writer 同名 `[MIDHOOK@<位置标>]` 段的内容**替换**（去掉所有 `[COLD_OPEN]`/`[BODY]` 等结构性段标记，留纯文本 + 角色标注）。
   - **保留** body-writer 的 `[SECTION:N]` 分节标记——它们是「按插图分段」的结构信号，进最终脚本，TTS 前由 extract_sections 剥离。**只去掉 `[BODY]`/`[CLIMAX]`/`[CTA]`/`[COLD_OPEN]` 等结构性段标记，不去 `[SECTION:N]` 和 `[MIDHOOK@...]`（后者已被替换成内容）。**
   - **保留所有 `A：`/`B：` 角色标注**（双人对话的 TTS 音色分配信号）。
   - 再接 `[CLIMAX]` + `[CTA]`（双人共同推向高潮/对句收尾）。
   - **二次覆盖校验**：缝合后可再跑一次 `check_illustration_coverage.py --script draft_v1.txt`，确认 body-writer 改写后仍未漏 labels（writers 可能压缩/改写要点）。
5. **punch-up**（读 draft_v1 + blueprint）→ `temp/draft_v2.txt`：为对话加味（交锋/吐槽/接梗/补充金句）。
6. **orality-polish**（读 draft_v2）→ `temp/draft_v3.txt`：统一双主持语气 + 确保角色标注格式正确 + 对话自然衔接 + 反套路清理。
7. **host-listen**（读 draft_v3，round 1）→ `scorecards/host-listen-round-1.json`。
   - `revise` → 把 issues 按 route 分发给 punch_up/orality 改 → 产出 draft_v(N+1) → 重跑 host-listen（round+1）。≤ `config.studio.host_listen_max_rounds`（默认 3）轮。
   - `pass` → 把最终 draft 复制为 `播客_脚本.txt`（覆盖前 backup_file.py 备份）。
8. **meta-writer**（读终稿 + source）→ `播客_标题与描述.txt`（标题/简介/标签，craft §10）。**studio 唯一产出 meta 的环节**。Phase 2 完成。

## 子 agent 调用约定（继承 _shared）
- goal 写死绝对输出路径；prompt 落盘 `prompts/studio-{role}-round-{n}.md`。
- 返回后 read_file 验证非空；空输出重试 1 次；仍空 → 主 agent 直接补位（Windows Edit/Write fallback）或跳过+记 degraded。
- 并行调度 hook+body 时遵守"最多 5 并发子 agent"。

## 熔断
- 总调用硬上限 `config.studio.total_call_cap`（默认 20）：到顶取当前最优 draft、标 `phase2.degraded=['call_cap']`、放行 Phase 2。
- host-listen 用满轮数仍 revise → 接受当前最优 draft、标 `phase2.host_listen.status=degraded`、放行（发布前显式提醒）。

## Phase 2 state（state.json.phase2）
```json
"phase2": {
  "conductor": "completed",
  "hook": "completed", "body": "completed", "assemble": "completed",
  "punch_up": "completed", "orality": "completed",
  "host_listen": {"round": 2, "status": "passed"},
  "meta": "completed",
  "drafts": ["draft_v1.txt","draft_v2.txt","draft_v3.txt"],
  "degraded": []
}
```
每个子步完成立即回写，崩溃不丢进度。

## Phase 4 衔接（writer 已退役）
`market_ready==false` 时，把 factcheck + judge 合并的 `fix_directives` 路由到 **punch-up + orality-polish**（按 directive 性质分：趣味/对话张力→punch_up，口语/套路/角色平衡/事实→orality，事实失真优先 orality 删改）→ 产出新 draft → 重跑 host-listen + judge。≤ `config.evaluation.max_fix_rounds`（默认 3）轮。

## --fast 回退
`config.studio.enabled=false` 或 `studio.fast_fallback=true` → Phase 2 退回单 `duo-scriptwriter`（双人简化生成路径，仍是对话稿，不是独白；适合快稿/资讯播报场景）。
