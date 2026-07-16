# Phase 6: 校验归档

> 本文件是 `SKILL.md` Phase 6（归档）的详细参考，由主流程按需加载。
>
> 注：旧版编号为 Phase 7；纯编排版把归档重编为 Phase 6（发布为 Phase 7）。

## Phase 6 — 校验归档（内联）

检查 `state.json.stages.archive.status == "completed"` → 跳过。

前置：Phase 3（媒体）+ Phase 4（播客）+ Phase 5（视频）均完成。

### 媒体一致性校验与图片压缩（并行）

> **并行加速说明**：reconciliation 只读取 PNG 验证维度和一致性，不修改图片；压缩生成新文件，不覆盖原图。两者互不依赖，可同时启动。

仅当 Phase 3（媒体）未跳过时执行。

**并行启动以下两个操作**：

#### 操作 A — 媒体一致性校验

```bash
<py> {skill_dir}/scripts/reconcile_media.py --output-dir "{article_dir}" --require-cover --require-illustrations --cover-size "{config.image.cover_size}" --report "{article_dir}/temp/media-reconciliation.json"
```

> `reconcile_media.py` 已适配新布局：在 `{article_dir}` 下校验 `公众号_封面.png`、`imgs/` 插图、文章 `![]()` 引用与 `imgs/outline.md` 一致。`--verify-prompt-hash` 在纯编排版可选（prompt hash 由下游 illustrator 管理，编排器不一定持有）。

失败时：更新 `state.json.stages.archive.reconciliation.status = "failed"` + failures；禁止发布；修复后重跑。

成功时更新 `state.json.stages.archive.reconciliation.status = "completed"`。

#### 操作 B — 图片压缩

1. 检测待压缩的 PNG（`公众号_封面.png`、`imgs/NN-*.png`）。
2. 无 PNG → `state.json.stages.archive.compression = "skipped"`。
3. 有 PNG → 执行：
   ```bash
   <py> {skill_dir}/scripts/compress_images.py {匹配到的 PNG 文件列表} --format "{config.image.output_format}" --quality "{config.image.quality}" --parallel
   ```
   `state.json.stages.archive.compression = "completed"`。

### 等待并行操作完成

等待 reconciliation 和 compression 都完成（或跳过）后再进入终检。

### 最终产物验证

逐项确认（按 target_platforms，默认全平台）：
- `公众号_文章.md`（含插图引用）+ `公众号_摘要.txt`
- `公众号_封面.png`
- `imgs/*.png`
- `_podcast/播客_脚本.txt` + `_podcast/播客_TTS.mp3`（boker/全平台）
- `_video/公众号_视频.mp4`（全平台）

任一缺失或为空 → 报告并标 `stages.archive.status = "failed"`。

### 归档

1. **临时文件清理**（归档后执行）：
   - 保留：`转录文本.txt`、`source_assets/*`、`media-reconciliation.json`（断点续跑/审计）
   - 删除：下游 skill 的 `temp/` 中间产物（如 TTS 分段、concat 列表）——由各下游 skill 自行管理，编排器不强制清理
2. 更新 `state.json.stages.archive.status = "completed"`。
3. 输出最终文件清单摘要给用户。
