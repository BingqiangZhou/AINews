---
name: image-generator
version: "1.0.0"
description: 图像生成后端执行器——封装搞定设计（Gaoding）/即梦（Jimeng）浏览器自动化与 Agnes/Pollinations API 多条光栅图像生成路径，含裁剪/验证/重试/批量机制。本 skill 不负责内容设计（维度/风格/配色由调用方决定），只负责"拿 prompt 文件 → 出图 → 返回可用 PNG"。当其他 skill（article-cover-image-generator / article-illustrator）或编排器的批量生图场景需要生成光栅图片时委托本 skill。**触发场景**：生成图片、出图、render image、Gaoding 生图、Jimeng 生图、即梦生图、Agnes 生图、批量生图。
metadata:
  backend: agnes
---

# Image Generator

图像生成**后端执行器**。接收 prompt 文件 + 目标尺寸 + 后端选择，产出验证过的 PNG。不关心画什么（那是调用方的维度模型的事），只关心怎么把 prompt 变成可用的图。

## 关联 Skills

- **article-cover-image-generator**：封面专用编排器，构建好封面 prompt 后委托本 skill 出图
- **article-illustrator**：文章插图，构建好插图 prompt 后委托本 skill 出图
- **批量生图场景**（编排器如 ai-news-digest 的 image-batch-generator 子流程）：直接引用本 skill 的 `references/gaoding-image-generation.md`（Gaoding）或 `references/jimeng-image-generation.md`（即梦）作为操作手册（不经过 skill 调用层，自行操作浏览器）
- **agnes-ai**（已移除）：`scripts/agnes_image.py` 原从 agnes-ai 复制而来，现已自包含独立（agnes-ai skill 已删除）

## 后端

四条生成路径，由 `provider` 参数或 `config.backend.provider` 决定：

| 后端 | 机制 | 适用 | 成本 |
|---|---|---|---|
| **Gaoding**（搞定设计，默认） | Chrome DevTools 自动化 `gaoding.art/creation?skill=3` | 含中文文字的图（万相2.7 印刷级文字渲染）；需要高质量 | 万相2.7 = 1 豆/张 |
| **Jimeng**（即梦） | Chrome DevTools 自动化 `jimeng.jianying.com`（Agent 模式 + 锁定图片 4.7） | 含中文文字的图（即梦中文文字/设计感 SOTA）；Agent 理解 prompt 自动选比例；需要高质量 | 图片 4.7 = 1 积分/张 |
| **Agnes** | API 直调 `scripts/agnes_image.py` | 快速出图；无文字或英文文字；Gaoding/Jimeng 不可用时回退 | 免费（截至 2026-06 永久免费） |
| **Pollinations** | API 直调 `scripts/pollinations_image.py`（flux/turbo） | 免费 B-roll/概念图；双 key 轮换；按小时配额 | 免费（按小时花粉配额，402 停） |

**回退策略**：Gaoding/Jimeng 失败时，仅当 `config.backend.fallback_to_agnes == true`（默认 `false`）才回退 Agnes；否则报告失败由调用方决定。Pollinations 独立使用（不参与 Gaoding/Jimeng 回退链）。Jimeng 独立于 Gaoding（两者不互相回退，各自失败各自报告）。

## 输入

| 参数 | 必选 | 说明 |
|---|---|---|
| `prompt_file` | 二选一 | prompt 文件路径（含 YAML frontmatter + 正文，推荐方式） |
| `prompt` | 二选一 | 内联 prompt 文本（当无文件时） |
| `output_path` | 是 | 输出 PNG 完整路径 |
| `target_size` | 是 | 输出尺寸 `WxH`，如 `900x383`、`1920x1080` |
| `provider` | 否 | `gaoding`（默认）/ `jimeng` / `agnes` / `pollinations`；未传则读 `config.backend.provider` |
| `references` | 否 | 参考图片路径列表（img2img；仅 Agnes 支持） |

## 输出

**单图模式**：

```json
{
  "success": true,
  "data": {
    "image_path": "...",
    "provider": "gaoding | jimeng | agnes",
    "original_size": "1923x818",
    "final_size": "900x383",
    "fallback_used": false,
    "fallback_reason": null
  }
}
```

**批量模式**（`images` 数组输入）：

```json
{
  "results": [
    { "success": true, "data": { "image_path": "...", "provider": "..." } },
    { "success": false, "error": "...", "image_id": "..." }
  ]
}
```

## 流程

```
接收 prompt + target_size + provider
→ 选后端（provider 参数 > config.backend.provider）
→ Gaoding 路径 / Jimeng 路径 / Agnes 路径 / Pollinations 路径
→ 后处理（验证 >5KB + PIL 裁剪到 target_size）
→ 返回结构化结果
```

### Gaoding 路径（当 provider == "gaoding"）

读取 [references/gaoding-image-generation.md](references/gaoding-image-generation.md)，按步骤执行浏览器自动化：
- Step A 连接登录检查 + 选模型（默认万相2.7，`config.backend.gaoding_model` 可配）
- Step B 输入 prompt（JS dispatchEvent）
- Step C 生成（点击一次，轮询 `list_pages` 等编辑器 tab，检测失败态）
- Step D 导出（取消"自动发布至社区"勾选，下载 PNG）
- Step E 裁剪验证（PIL center-crop + resize 到 target_size，>5KB 校验）

**关键规则**：
- ⛔ 生图按钮只点击一次（每次消耗豆），通过 `list_pages` 轮询等待
- ⛔ 导出时必须取消勾选"自动发布至社区"
- ⛔ 同一时刻只能一个 agent 操作 Gaoding（共享 chrome-devtools MCP 启动的 Chrome 实例）
- ⛔ 多张图必须**串行**，每张开全新 tab（详见 gaoding-image-generation.md「串行生成模式」）
- 内容审核拒绝（生成失败/违反内容生成规范）**不回退**——改写 prompt 去掉触发词后重试一次

### Jimeng 路径（当 provider == "jimeng"）

读取 [references/jimeng-image-generation.md](references/jimeng-image-generation.md)，按步骤执行浏览器自动化：
- Step A 连接、进入图片生成界面、登录检查
- Step B 确认 Agent 模式 + 关闭"自动"开关 + 选模型（默认图片 4.7，`config.backend.jimeng_model` 可配）
- Step C 输入 prompt（JS execCommand；**不含精确像素尺寸**，只描述用途+比例）
- Step D 生成（点击发送，`wait_for` 等"已完成"，检测失败态）
- Step E 下载（点结果图开大图查看器 → 点"下载" → 从下载目录复制）
- Step F 裁剪验证（PIL center-crop + resize 到 target_size，>5KB 校验）

**关键规则**：
- ⛔ 发送按钮只点击一次（每次消耗积分），通过 `wait_for` 等待"已完成"
- ⛔ prompt **不含精确像素尺寸**（如"900x383像素"）——即梦 Agent 会据此尝试精确尺寸生成，但模型对尺寸有硬约束（2K 下宽高均需 1296-3024），导致反复重算。只描述用途+比例（如"宽幅横版banner比例约2.35:1"）
- ⛔ **关闭"自动"开关**：即梦 Agent 模式默认"自动"会自行挑模型，非会员触发 5.0Pro→4.5 降级循环。关闭"自动"+ 锁定图片 4.7 后稳定高效
- ⛔ 同一时刻只能一个 agent 操作 Jimeng（共享 chrome-devtools MCP 启动的 Chrome 实例）
- ⛔ 多张图必须**串行**，每张用一个全新对话（避免 Agent 上下文污染）
- ⛔ 每张生成前复核：模式=Agent 模式、自动=关、模型=图片 4.7（导航后可能重置）
- 内容审核拒绝（生成失败/内容违规/无法生成）**不回退**——改写 prompt 去掉触发词后重试一次
- 下载比 Gaoding 简单：点结果图 → 大图查看器 → "下载"按钮（无需进编辑器、无需取消社区发布）

### Agnes 路径（当 provider == "agnes"，或 Gaoding/Jimeng 失败回退时）

```bash
{config.conda_python} skills/image-generator/scripts/agnes_image.py \
  --prompt "{prompt}" --model "{config.default_image_model}" \
  --size "{target_width}x{target_height}" \
  --output "{output_path}" --json
```

脚本自包含（`scripts/lib/utils.py` 提供 download/get_api_key/load_config），读 `image-generator/config.json` 的 `base_url`/`default_image_model`/`env_var`（AGNES_API_KEY）。支持 img2img（`references` 参数 → `--image`，仅 Agnes）。

### Pollinations 路径（当 provider == "pollinations"）

```bash
{config.conda_python} skills/image-generator/scripts/pollinations_image.py \
  --prompt "{prompt}" --model flux \
  --size "{target_width}x{target_height}" \
  --output "{output_path}" --json
```

脚本自包含（内置双 key 轮换：`load_keys`/`KeyRotator`），读环境变量 `POLLINATIONS_API_KEY_sick-snake` + `POLLINATIONS_API_KEY_precise-koi`（按小时刷新额度）。传 `--api-key` 则进单 key 模式。

**约束**：
- 按小时花粉配额（非滚动）：HTTP 402 = 账户耗尽（停止本轮等整点刷新）；429 = 单 key 限流（自动切 key）
- 默认 seed=42（固定可复现）；`--seed` 可指定
- 输出统一转 PNG（jpeg 字节经 PIL 另存）
- 文字渲染差（招牌/文字会乱码）——适合无文字的概念图/B-roll，不适合含中文标签的封面

### 后处理

1. 验证输出文件存在且 > 5KB（否则视为失败）
2. PIL 按比例 center-crop 后 resize 到精确 `target_size`（LANCZOS）
3. 删除 `_raw` 中间文件

## 批量生成

当调用方需要多张图时：

```json
{
  "images": [
    { "prompt_file": "...", "output_path": "...", "target_size": "900x383", "image_id": "cover" },
    { "prompt_file": "...", "output_path": "...", "target_size": "1920x1080", "image_id": "01-xxx" }
  ],
  "provider": "gaoding"
}
```

**规则**：
- 所有 prompt 必须先落盘到文件，再开始生成
- 并发上限 **5 张**
- 支持混合尺寸、混合后端（每条自带 target_size；provider 在顶层或逐条指定）
- Gaoding 多图**必须串行**（每张全新 tab，~70s/张），不能并行提交
- Jimeng 多图**必须串行**（每张全新对话，~40-70s/张），不能并行提交
- Agnes 多图可后台并行（每个 `agnes_image.py` 独立进程）
- 失败项重试一次，不重跑成功项

## config.json 字段

| 字段 | 用途 |
|---|---|
| `conda_python` | Python 解释器路径（Agnes 调用用） |
| `base_url` | Agnes API 端点（脚本读） |
| `default_image_model` | Agnes 模型名（脚本读） |
| `env_var` | API key 环境变量名（`AGNES_API_KEY`） |
| `chrome_download_dir` | Gaoding 下载目录 |
| `backend.provider` | 默认后端（`gaoding`/`agnes`/`pollinations`） |
| `backend.gaoding_model` | Gaoding 模型（默认万相2.7） |
| `backend.jimeng_model` | Jimeng 模型（默认图片 4.7） |
| `backend.fallback_to_agnes` | Gaoding/Jimeng 失败是否回退 Agnes（默认 false） |
| `backend.pollinations_model` | Pollinations 模型（默认 flux） |
| `backend.pollinations_base` | Pollinations API 端点 |

## 环境变量

| 变量 | 必要性 | 用途 |
|---|---|---|
| `AGNES_API_KEY` | Agnes 后端必须 | Agnes 图像 API 认证 |
| `POLLINATIONS_API_KEY_sick-snake` | Pollinations 后端（优先 key） | 双 key 轮换之一（额度更充裕） |
| `POLLINATIONS_API_KEY_precise-koi` | Pollinations 后端（备用 key） | 双 key 轮换之二 |

Gaoding 通过 Chrome 已登录 session 操作，无需额外变量。Jimeng 同样通过 Chrome 已登录 session 操作（字节系账号：抖音/剪映/头条通用），无需额外变量。Pollinations 两个 key 都没设时会报错（或用 `--api-key` 单 key 模式）。

## 按需读取

| 文件 | 用途 | 加载时机 |
|---|---|---|
| `references/gaoding-image-generation.md` | Gaoding 浏览器自动化完整步骤 | provider == gaoding 时 |
| `references/jimeng-image-generation.md` | Jimeng（即梦）浏览器自动化完整步骤 | provider == jimeng 时 |
