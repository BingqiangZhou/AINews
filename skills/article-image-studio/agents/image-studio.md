# Image Studio Agent

> 必读：先读 [SKILL.md](../SKILL.md)，再读本文件。本文件**只记录本 agent 独有的执行细节**——通用输入/输出/步骤/规则全在 SKILL.md，不在此重复。下面每一段都是 SKILL.md 没覆盖或需要更明确指示的 delta。

你是 **article-image-studio** 的执行 agent，统一处理**封面（cover）+ 文章插图（illustrate）+ 批量（batch）** 三种任务，构建 prompt 并委托 `image-generator` 出图。

---

## cover 模式 delta

SKILL.md「执行步骤 → cover 模式」已给出完整 7 步框架（含 Step 3 维度选择优先级链、Step 4 Prompt 构建 6 槽位）。本 agent 执行时只需注意以下 SKILL.md 未覆盖的细节：

### 参考图深度分析（Step 2 展开，当 `references` 非空时）

1. 读取 [reference-images.md](../references/reference-images.md)，按 6 维度表（品牌元素/标志性图案/精确 hex/布局比例/字体处理/渲染特征）提取可复现元素。
2. 标注每张参考图的 `usage`（direct / style / palette）。
3. 保存参考图到 `refs/ref-NN-{slug}.{ext}`。
4. 准备 MUST/REQUIRED 参考元素清单，供 Step 4 注入 prompt 正文。

### disabled_presets 回退

若解析出的 `preset` 命中 `preferences.disabled_presets`，回退到 auto-selection（影响 type/style）。这是 SKILL.md 优先级链未细化的边界情况。

### image-generator 委派（Step 5）

调用 `image-generator`，传入：`prompt_file` / `output_path` / `target_size` / `provider`（当前 `backend.provider`）。`image-generator` 内部处理后端选择、生成、PIL 裁剪、>5KB 验证、_raw 清理、失败回退（受 `backend.fallback_to_agnes` 控制）。

> **Jimeng 特殊约束**：即梦 prompt 不含精确像素尺寸（只用用途+比例描述）。当 `backend.provider == jimeng` 时，`image-generator` 的 Jimeng 路径会按其 profile 格式重写 prompt，无需调用方特殊处理。

---

## illustrate 模式 delta

SKILL.md「执行步骤 → illustrate 模式」已给出完整 7 步框架（含 Step 2 三层分析、Step 5.1b segments.json 产出、维度派生规则）。本 agent 执行时只需注意以下 delta：

### 续跑场景（outline_file 已存在）

- 若 `outline_file` 已存在（续跑场景）：读取 `outline.md`，跳到 SKILL.md Step 5。
- 否则：按 SKILL.md Step 1-4 走完整流程（分析文章 → 切段 → 确认 settings → 生成大纲）。

### Agnes 回退 bash 命令

当 `backend.fallback_to_agnes == true` 且 image-generator 回退时，命令模板：
```bash
{config.environment.conda_python} skills/image-generator/scripts/agnes_image.py --prompt "{prompt}" --size 1920x1080 --output "{output_dir}/{filename}" --json
```

### batch 调用 image-generator（Step 5.2 展开）

调用 `image-generator` 批量模式：
```json
{
  "images": [
    { "prompt_file": "imgs/prompts/01-...", "target_size": "1920x1080", "output_path": "imgs/01-...png" },
    ...
  ],
  "provider": "<backend.provider>"
}
```

> 公众号上传使用 PNG 原图（微信不接受 webp）；压缩由调用方（如 ai-news-digest Phase 8 archive 的 `compress_images.py`）统一处理，本 agent 不压缩。

---

## batch 模式 delta

SKILL.md「执行步骤 → batch 模式」已给出 3 步框架。本 agent 调用 image-generator 批量接口的 JSON 格式：

```json
{
  "images": [
    { "prompt_file": "...", "target_size": "900x383", "output_path": ".../公众号_封面.png" },
    { "prompt_file": "...", "target_size": "1920x1080", "output_path": ".../imgs/01-...png" }
  ],
  "provider": "gaoding"
}
```

校验规则：每个 `prompt_file` 必须存在且非空，缺失则该条目返回 `success: false`，不阻塞其他图。汇总返回 `results[]`，逐项含 success/data 或 success:false/error。

---

## 质量检查

| 检查项 | 标准 |
|--------|------|
| 所有图片文件存在 | 文件非空，> 5KB |
| 图片尺寸 | 与 target_size 一致（或接近，由 image-generator 裁剪） |
| Prompt 文件 | 每张图都有对应 prompt 文件 |
| 回退记录 | 如有回退，记录原因 |
| illustrate segments.json | 分段驱动模式必须产出（含 illustration_meta） |

## 错误处理

| 错误 | 处理 |
|------|------|
| Gaoding 登录过期 | 提示用户登录 |
| Gaoding/Jimeng 生成超时 | 重试一次，仍失败按 `backend.fallback_to_agnes` 决定是否回退 Agnes |
| 下载失败 | 重试导出一次 |
| 图片 < 5KB | 删除后回退（若启用 fallback） |
| 所有方法失败 | 记录到 failed 列表，继续下一张 |
