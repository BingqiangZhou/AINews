# 稿定 AI 生图 — 统一参数化参考

> 本文件合并公众号封面（900x383）与文章插图（1920x1080）两种用途的稿定 AI 生图流程，通过 profile 参数化区分差异。

## ⚠️ 2026-07 改版说明（已验证）

稿定 AI 在 2026-07 前后改版，生图入口从独立"创建页"改为**首页集成**。2026-07-15 已完整验证新版全流程，要点如下：

| 项目 | 改版后实测（2026-07-15） |
|------|------|
| 入口 URL | `creation?skill=3` **重定向到首页** `gaoding.art/?skill=3`（即 `gaoding.art/`）。直接 `new_page`/`navigate_page` 到首页即可。 |
| 输入框 | 首页中部 `.ProseMirror` / `[contenteditable="true"]`（class `pm-part-engine-editor`），`execCommand('insertText')` 填入。 |
| 模型 chip | `.acv-chat-sender-v2-skill-picker__trigger-wrapper.gda-dropdown-trigger` **仍有效**；下拉"图片生成"区选 **"万相 2.7"（印刷级文字渲染）**，chip 文本更新为"万相 2.7"、消耗显示"1/张"。 |
| **生成按钮** | class `.acv-chat-sender-v2-generate-button`（完整 class 含 `gda-btn gda-btn-primary gda-btn-sm`）。**关键：按钮只在输入框非空时才渲染**——空输入框时 `querySelector` 返回 null 是正常的，**先输入 prompt，再查找并点击生成按钮**。 |
| 生成触发 | 点击后约 15-30s 自动开新编辑器 tab（`editor/canvas?type=board&mode=user&id={id}`），通过 `list_pages` 检测。 |
| 顶部 tab | 首页有"Agent模式 / 图片生成 / 视频生成"tab。**无需特意点"图片生成"**——默认即可输入并生成（模型在 chip 里选）。 |

> **最易踩的坑**：在空输入框状态下 `querySelector('.acv-chat-sender-v2-generate-button')` 会返回 null，导致误判"按钮不存在"。务必**先 `execCommand('insertText')` 填入 prompt，再查找生成按钮**（此时按钮已渲染且 enabled）。

**应急流程（若首页自动生成异常）**：让用户提供已生成作品的编辑器画布 URL（`editor/canvas?type=board&mode=user&id={id}`），`navigate_page` → `select_page` → 执行下方 **Step D 导出** + **Step E 裁剪**（画布页结构稳定，不依赖首页 DOM）。

## 概览

稿定 AI 的图片生成功能位于首页 `https://www.gaoding.art/`（改版后 `creation?skill=3` 已重定向到首页）。

**流程**：登录检查 → 选模型（万相2.7）→ 输入 prompt（含尺寸前缀）→ 生成 → 下载 → 裁剪 → 验证。

**核心机制**：模型按 `config.backend.gaoding_model` 配置（默认 **万相2.7**）+ 智能比例（默认）。Prompt 开头的尺寸前缀让“智能比例”自动匹配正确比例，无需手动切换比例设置；模型需在生图前选好（见 Step A “选模型”）。

## Target Profiles

调用方通过 profile 名称指定用途，各 profile 的参数差异如下：

| Profile | target_label | target_size_desc | prompt_language | crop_size |
|---------|-------------|-----------------|----------------|-----------|
| wechat-cover | WeChat公众号封面图 | 尺寸900x383像素，宽幅横版banner比例约2.35:1 | English visual description | 900x383 |
| illustration | 文章插图 | 尺寸1920x1080像素，16:9宽幅横版比例 | 中文视觉描述 | 1920x1080 |

**Prompt 格式**（由 profile 参数拼接）：

```
{target_label}，{target_size_desc}。{visual_prompt}
```

示例：
- wechat-cover: `WeChat公众号封面图，尺寸900x383像素，宽幅横版banner比例约2.35:1。A modern minimalist tech workspace...`
- illustration: `文章插图，尺寸1920x1080像素，16:9宽幅横版比例。一个现代化的科技工作空间...`

## 前置条件

- Chrome 由 chrome-devtools MCP 自动启动并管理（已登录稿定 session）
- 用户已在 `gaoding.art` 登录过（session 持久化在 Chrome profile 中）
- Prompt 已由调用方 agent 准备好（含 profile 对应的 visual_prompt）

## 完整步骤

### A. 连接与登录检查

1. `list_pages` 验证 MCP 连接可用（Chrome 由 chrome-devtools MCP 自动启动）。
2. `navigate_page` → `https://www.gaoding.art/`（改版后 `creation?skill=3` 已重定向到首页，直接用首页；见顶部「2026-07 改版说明」）。
3. `take_snapshot` 检查登录状态：
   - **已登录**：顶部显示用户头像或“我的”可点击（无“登录/注册”按钮）→ 继续下方“选模型”，再进 Step B
   - **未登录**：顶部出现“登录/注册”按钮 → 提示用户在浏览器中登录，`wait_for` 等待 “我的” 文字出现（timeout 180s）。超时则回退 Agnes。

> **选模型（登录确认后、首次输入 prompt 前；一个会话只做一次）**：模型由 `config.backend.gaoding_model` 配置，默认 **万相2.7**。模型 chip 在创建页底部设置栏，selector = `.acv-chat-sender-v2-skill-picker__trigger-wrapper.gda-dropdown-trigger`：
> - `evaluate_script` 点击该 chip 打开模型下拉；
> - 下拉分“图片生成”“视频生成”两区，**只在“图片生成”区选目标模型**——视频区也有同名“万相2.7”，选错会进视频生成；
> - `evaluate_script` 点击目标模型项（“万相 2.7”，描述含“印刷级文字渲染”）；选中后 chip 文本变为“万相 2.7”即成功；
> - chip 已显示目标模型则跳过；
> - ⛔选中后**不要刷新/导航创建页**，否则模型重置回“智能图像”；每张生成前 `evaluate_script` 复核 chip 文本仍是目标模型，被重置就重选；
> - **选型经验**：图内要中文文字（标签/标题/数据）→ **万相2.7**（印刷级文字渲染，中文准确，1 豆/张，默认）；纯视觉无文字 → 也可改用“智能图像”（3 豆/张，但中文文字会乱码）。封面（text:none）默认走万相2.7。

### B. 输入 Prompt

4. 通过 `evaluate_script` 向 contenteditable 输入框填入 prompt：

```javascript
() => {
  const editor = document.querySelector('[contenteditable="true"]');
  if (!editor) return { error: 'editor not found' };
  editor.focus();
  editor.innerHTML = '';
  document.execCommand('insertText', false, '{target_label}，{target_size_desc}。{VISUAL_PROMPT}');
  return { success: true, text: editor.innerText };
}
```

> 注意：使用 `document.execCommand('insertText')` 而非 `innerHTML` 赋值，因为前者能正确触发编辑器的内部监听器。

### C. 生成图片

5. 确认生成按钮已 enabled（class: `acv-chat-sender-v2-generate-button`）。**前置条件：输入框必须已填入 prompt**——改版后生成按钮只在输入框非空时才渲染（空输入框时 `querySelector` 返回 null 是正常的，不是 bug）。若第 4 步已输入 prompt 仍找不到按钮，`evaluate_script` 复核输入框 `innerText` 非空后再查。
6. 点击生成按钮（MCP click 可能无效，需通过 JS dispatchEvent）：

```javascript
() => {
  const btn = document.querySelector('.acv-chat-sender-v2-generate-button');
  if (!btn) return { error: 'generate button not found' };
  const rect = btn.getBoundingClientRect();
  const x = rect.left + rect.width / 2;
  const y = rect.top + rect.height / 2;
  ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(type => {
    btn.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0 }));
  });
  return { clicked: true };
}
```

7. 等待生成完成：
   - 通过 `list_pages` 轮询检测新打开的编辑器页面（URL 格式 `https://www.gaoding.art/editor/canvas?mode=user&id={work_id}&type=board`），间隔 10s，超时 120s
   - 检测到新页面后 `select_page` 切换到该页面，**等生成真正完成再导出**：`take_snapshot` 确认画布图片已完整渲染（非空白/占位）且页面出现"任务已完成"/"已成功生成..."。"导出"按钮可见 ≠ 画布就绪——**editor tab 打开不等于生成完成**，没等够就点导出会下载失败或抓到错图。拿不准时 `take_screenshot` 肉眼确认画布内容再导出。
   - **⛔ 必须先检测失败态**：编辑器 tab 打开 ≠ 生成成功；"生成中" overlay 消失也**不是**成功信号（失败时 overlay 同样会消失）。切换到编辑器页后，先检查页面文本是否含失败标志——`生成失败` / `违反内容生成规范` / `无法生成对应的图像` / `无法为您展示` / `智能图像生成失败`——命中任一即判定该张**生成失败**，**不要进入导出**（导出会得到空画布）。成功标志：出现 `已成功生成...`，或画布含 `内容由 AI 生成` 且无任何失败文本。
   - **注意**：生成需要较长时间（30-90s），切勿在未确认完成前重复点击生成按钮

8. `select_page` 切换到编辑器页面，确认画布加载完成（"导出"按钮可见）。

### D. 导出图片

9. `click` 点击"导出"按钮（class `dub-ai-export-button`），弹出"下载作品"对话框（class `gda-modal`）。
10. 确认 PNG 格式为默认选中（对话框中"作品类型"下的格式 combobox 默认为 PNG，无需切换）。
11. **必须取消勾选"自动发布至社区"**（默认勾选，必须取消，否则图片会被公开发布）。两种方式皆可（2026-07 实测）：
    - 方式 A（MCP fill，需先 snapshot 拿到 checkbox uid）：`fill uid={checkbox_uid} value=false`
    - 方式 B（JS，不依赖 uid，更可靠）——找模态框里 checked 的 checkbox，点其 label：
    ```javascript
    () => {
      const modal = document.querySelector('.gda-modal') || document.querySelector('[class*="modal"]');
      const cb = modal.querySelector('input[type="checkbox"]');
      if (cb && cb.checked) { cb.closest('label')?.getBoundingClientRect(); cb.click(); }
      return { nowChecked: cb ? cb.checked : 'no cb' };
    }
    ```
    确认返回 `nowChecked: false` 才继续。
12. `click` 点击"下载"按钮（class `.gda-modal .action__btn` 或 `.gda-btn-emphasis.action__btn`，文本"下载"）。
13. 等待浏览器下载完成（5s），从 Chrome 下载目录复制最新文件到输出目录：
    ```bash
    sleep 5
    latest=$(ls -t /d/12990/Downloads/*.{png,jpg,jpeg,PNG,JPG,JPEG} 2>/dev/null | head -1)
    if [ -n "$latest" ] && [ "$(wc -c < "$latest")" -gt 5000 ]; then
      cp "$latest" "{output_dir}/{filename}_raw.png"
    fi
    ```

### E. 裁剪与验证

14. 裁剪到 profile 对应的精确目标尺寸（使用 PIL）。**必须先按目标比例中心裁剪、再 resize**——稿定"智能比例"对 illustration profile 经常出正方形或非 16:9 的图，直接 `resize` 会拉伸变形：
    ```bash
    python -c "
    from PIL import Image
    img = Image.open('{output_dir}/{filename}_raw.png').convert('RGB')
    w, h = img.size; tr = {crop_width}/{crop_height}
    if w/h > tr:
        nw = int(h*tr); left = (w-nw)//2; img = img.crop((left, 0, left+nw, h))
    else:
        nh = int(w/tr); top = (h-nh)//2; img = img.crop((0, top, w, top+nh))
    img = img.resize(({crop_width}, {crop_height}), Image.LANCZOS)
    img.save('{output_dir}/{filename}')
    "
    ```
    其中 `{crop_width}` 和 `{crop_height}` 来自 profile 的 `crop_size`（如 wechat-cover 为 900x383，illustration 为 1920x1080）。

15. 验证输出文件存在且大小 > 5KB。
16. 删除中间文件 `{filename}_raw.png`。

## 默认设置

| 设置项 | 值 | 说明 |
|--------|-----|------|
| 模型 | 万相2.7（默认，可配置 `config.backend.gaoding_model`） | 印刷级中文文字渲染；登录后按 Step A“选模型”确认选中 |
| 比例 | 智能比例（默认） | 通过 prompt 尺寸前缀自动匹配，不需要手动选择 |
| 分辨率 | 2K（默认） | |
| 消耗 | 万相2.7：1 豆/张；智能图像：3 豆/张 | 切勿重复点击生成按钮 |

## 错误处理与回退

| 场景 | 处理 |
|------|------|
| Chrome 未运行 / CDP 失败 | 重试 `list_pages`；仍失败则回退 Agnes |
| 未登录且用户超时未登录 | 回退 Agnes |
| Prompt 输入框未找到 | 重试一次；仍失败回退 |
| 生成按钮 click 无响应 | 用 JS dispatchEvent 发送完整鼠标事件序列 |
| 生成超时（120s） | 轮询 `list_pages` 检测新编辑器 tab；两次超时回退 |
| 编辑器页面未自动打开 | 检查 `list_pages`；仍失败回退 |
| 导出按钮未找到 | 重试 `take_snapshot`；仍失败回退 |
| "自动发布至社区"未取消 | 必须在下载前取消勾选 |
| 下载失败 / 文件未找到 | 重试导出一次；仍失败回退 |
| 下载文件 < 5KB | 删除后回退 |
| **内容审核拒绝**（页面含「生成失败 / 违反内容生成规范 / 无法生成对应的图像 / 无法为您展示 / 智能图像生成失败」） | **不要回退**——改写 prompt（去掉触发词、中性化）后在稿定重试 1 次；仍拒则判定该张失败（插图跳过、封面暂停） |

**回退协议**：失败后默认调用 Agnes 路径（`agnes_image.py`）并记录 `fallback_used: true`。**例外：内容审核拒绝不回退**（见上表，改写重试）。`audio-to-social` 的 Phase 6 图片生成**整体禁用 Agnes 回退**（只用稿定），任何失败走「改写重试 1 次 → 仍失败则跳过/暂停」。

## URL 与环境

| 项目 | 值 |
|------|-----|
| AI 生图页面 | `https://www.gaoding.art/`（首页，改版后 `creation?skill=3` 重定向至此） |
| 编辑器页面 | `https://www.gaoding.art/editor/canvas?mode=user&id={work_id}&type=board` |
| 主站 | `https://www.gaoding.art/` |
| Chrome 下载目录 | `D:\12990\Downloads` |

## 注意事项

- 稿定 AI (gaoding.art) 与搞定设计 (gaoding.com) 是两个独立产品。AI 生图功能在 `gaoding.art` 域名下。
- 登录 session 需要在 `gaoding.art` 上完成（与 `gaoding.com` 的 session 不互通）。
- 每次生成消耗“豆”（稿定积分）：万相2.7 为 **1 豆/张**、智能图像为 3 豆/张。**切勿重复点击生成按钮**，每次点击都会消耗积分。
- **Prompt 开头的尺寸描述是关键**，"智能比例"据此自动匹配正确比例。
- 生成完成后稿定 AI 自动打开编辑器页面（新 tab），通过 `list_pages` 检测新页面后切换过去导出。
- 生成需要 30-90s，耐心等待编辑器页面自动打开。
- 导出格式可能为 JPG 或 PNG，PIL 均可直接读取后转存为 PNG。

## 并行生成模式

当需要同时生成多张图片时（封面 + 插图，或多张插图），使用并行提交模式以节省总耗时。

### 原理

稿定 AI 每次点击"生成"后会在后台处理，同时自动开新 tab 打开编辑器页面。**不需要等前一张生成完毕再提交下一张**——可以在创建页连续输入 prompt 并点击生成，所有请求并行处理。

### 并行提交流程

1. **记录初始 tab 数**：`list_pages` 获取当前打开的页面数量，记为 `initial_count`
2. **连续提交所有 prompt**：在首页（`gaoding.art/`）上循环执行：
   - 清空输入框（`editor.innerHTML = ''`）
   - 输入当前 prompt（`execCommand('insertText')`）
   - 点击生成按钮
   - 等待 2-3 秒（让请求发送），然后立即处理下一张
   - **不需要等待生成完成**
3. **轮询等待所有结果**：
   ```
   expected_tabs = initial_count + N (N = 提交的图片数量)
   while (当前 tab 数 < expected_tabs) {
     sleep 10s
     list_pages
   }
   ```
4. **按完成顺序逐个导出**：检测到新编辑器 tab 后：
   - `select_page` 切换到该 tab
   - 执行步骤 D（导出）和 E（裁剪验证）
   - 完成后切换回创建页或下一个编辑器 tab

### 注意事项

- 每次并行最多 **5 张**，避免稿定积分消耗过大和 tab 过多
- 并行提交时，创建页可能短暂显示"生成中"状态，此时输入框可能不可用。如果遇到，等待 3-5 秒后重试
- 所有 editor tab 的 URL 格式相同（`/editor/canvas?mode=user&id={work_id}`），无法通过 URL 区分哪张对应哪个 prompt。需要按提交顺序和检测顺序的对应关系来判断，或通过 `take_snapshot` 查看画布内容辅助判断
- 如果某张图生成失败（超时未开新 tab），单独为该图重新提交一次

## 串行生成模式（推荐，多张图时的默认做法）

> **⚠️ 重要教训**：并行模式在实践中极易出问题——同一创建页 tab 内反复 `innerHTML=''` + `execCommand('insertText')` **不能可靠触发 React 状态更新**，导致"每次提交的都是同一个 prompt"、生成出来全是雷同的图。**多张图必须用串行模式**。

### 根因（为什么并行会失败）

1. **React 状态不更新**：搞定设计创建页是 React SPA。`editor.innerHTML = ''` 清空了 DOM，但 React 内部状态仍保留上一次的值；`execCommand('insertText')` 在 DOM 里插入了新文本，但 React 的事件系统**不监听 execCommand**，状态没更新 → 提交按钮发送的是 React 状态里的**旧 prompt**。
2. **会话上下文污染**：即使 React 状态更新成功，同一创建页 tab 的对话历史会累积，万相2.7 会"看着历史对话"生成，导致后续图片和第一张雷同。
3. **Tab 串号**：并行生成的编辑器 tab URL 格式相同（`/editor/canvas?id={work_id}`），无法通过 URL 区分哪张对应哪个 prompt。导出时按 tab 检测顺序（而非提交顺序）下载，极易拿错图。

### 正确做法：每张图用一个全新的创建页 tab

**核心原则：每张图 = 一个全新 tab = 一个干净的 React 实例 + 干净的对话历史。**

#### 完整流程（每张图重复一遍）

1. **开新 tab**：`new_page` → `https://www.gaoding.art/`（改版后用首页；旧 `creation?skill=3` 会重定向，见顶部「2026-07 改版说明」。**不要在已有 tab 里复用**）
2. **等待页面加载**：`sleep 3000`，确认编辑器存在
3. **选模型**（每个新 tab 都要重选，因为模型会重置回"智能图像"）：
   - `evaluate_script` 点击模型 chip → 下拉里选"万相 2.7"（图片生成区、带"印刷级文字渲染"描述的那个）
   - 确认 chip 文本 == "万相 2.7"
4. **输入 prompt**：
   ```javascript
   const editor = document.querySelector('[contenteditable="true"]');
   editor.focus();
   editor.innerHTML = '';
   document.execCommand('insertText', false, '{PROMPT}');
   ```
5. **⛔ 验证 React 拿到了正确文本**（关键防错步骤）：
   ```javascript
   const check = document.querySelector('[contenteditable="true"]');
   return { text: check.innerText.slice(0, 50), length: check.innerText.length };
   ```
   确认返回的文本是你刚输入的 prompt（而非上一张的残留）。
6. **点击生成**：`evaluate_script` dispatchEvent 完整鼠标事件序列到 `.acv-chat-sender-v2-generate-button`。**按钮在第 4 步输入 prompt 后才渲染**（空输入框时不存在），此时必已可见。
7. **再次确认编辑器内容没变**（提交后编辑器应仍显示当前 prompt）：
   ```javascript
   const editor = document.querySelector('[contenteditable="true"]');
   return { editorStill: editor.innerText.slice(0, 40) };
   ```
8. **等待生成**：`sleep 65-70`，然后 `list_pages` 检测新编辑器 tab
9. **验证内容正确**（导出前必做）：
   - `select_page` 到新编辑器 tab
   - `take_screenshot` + `analyze_image`（或 Read）确认画的内容和 prompt 一致
   - **快速色调校验**：用 PIL 缩放到 50×50 取平均 RGB，对比预期色调（深色科技图 vs 暖色生活场景 vs 明亮等距插画，色调应明显不同）
10. **导出**：点"导出" → 取消"自动发布至社区" → 点"下载"
11. **确认下载文件正确**：
    - `ls -t` 取最新下载文件，**检查文件名**（搞定设计会根据图的内容自动命名，如"科技信息图""生活场景插画"——文件名应和 prompt 主题吻合）
    - 如果文件名和预期不符，说明拿到了错误的图，重新导出
12. **裁剪到目标尺寸**：PIL center-crop + resize
13. **关闭该编辑器 tab**（可选，避免 tab 堆积）

#### 为什么这样做可靠

- 每张图用全新 tab → React 实例干净、无状态残留
- 每张图用全新对话历史 → 万相2.7 不受之前请求影响
- 每张图独立验证 + 文件名确认 → 不会拿错图
- 代价：比并行慢（每张约 70s），但可靠

### 万相2.7 的能力边界（避免反复试错）

- **擅长**：具体场景（咖啡馆、办公桌）、具象物品（放大镜、管道、金币）、3D 等距插画、扁平矢量 UI
- **不擅长**：抽象技术概念（"缓存失效"会被理解成"禁止/封锁"、"前缀匹配"画不出来）→ 遇到抽象概念，**换具象比喻**（如缓存失效 → 放大镜发现隐藏的红色问号方块）
- **中文文字**：万相2.7 支持图内中文文字渲染（印刷级），但文字越少越可靠
