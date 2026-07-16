# 即梦 AI 生图 — Agent 模式 + 锁定模型参考

> 本文件描述即梦（jimeng.jianying.com）的图片生成流程。采用 **Agent 模式 + 关闭"自动"开关 + 锁定模型 4.7** 的组合：让 Agent 理解 prompt 自动选比例，但锁定模型避免 Agent 在模型可用性上反复降级试探。

## 概览

即梦 AI 的图片生成功能位于 `https://jimeng.jianying.com/ai-tool/image-generate`（会重定向到 `/ai-tool/home`，需从首页点"图片"快捷入口进入生成界面）。

**流程**：进图片生成界面 → 确认 Agent 模式 → 关闭"自动"开关 + 锁定模型 4.7 → 输入 prompt → 生成 → 等待"已完成" → 点结果图开大图查看器 → 下载 → 裁剪 → 验证。

**核心机制**：
- **Agent 模式**：即梦的对话式生成模式，Agent（LLM）先理解 prompt（含用途、比例、风格），自动选合规参数后调模型。优点是 prompt 可含自然语言用途描述（如"公众号封面图，宽幅横版"），Agent 会自动匹配最佳比例；缺点是默认"自动"模式下 Agent 会自行挑模型，非会员账号会触发 5.0Pro→4.5 的降级循环。
- **关闭"自动"+ 锁定模型**：在"生成偏好"面板关闭"自动"开关（底部按钮文字从"自动"变"自定义"），并手动选模型为"图片 4.7"。这样 Agent 仍理解 prompt，但**不再自行改模型**，避免降级循环，且 4.7 仅消耗 1 积分/张（5.0Pro 非会员不可用，4.5/4.0 效果不如 4.7）。

## 与搞定设计（Gaoding）的关键差异

| 维度 | 搞定设计（万相2.7） | 即梦（图片 4.7） |
|---|---|---|
| 入口 | `gaoding.art/creation?skill=3` 直接进 | 重定向到 home，需点"图片"快捷入口 |
| 模式 | 直接输入 prompt 生成 | Agent 模式（LLM 先理解再调模型） |
| 模型选择 | 创建页底部 chip 下拉 | "生成偏好"面板 → 关闭"自动" → 模型按钮 |
| 比例 | "智能比例"，靠 prompt 尺寸前缀驱动 | Agent 自动选（21:9/16:9/...），或"生成偏好"面板手动选 |
| prompt 尺寸前缀 | **必须**含精确像素（900x383） | **不要**含精确像素（会触发 Agent 尺寸合规循环）；只描述用途+比例 |
| 结果展示 | 生成后自动开新 tab 编辑器 | 当前页内联展示（对话流式） |
| 下载 | 进编辑器 → 导出 → **取消"发布社区"** → 下载 | 点结果图 → 大图查看器 → "下载"按钮（无社区发布坑） |
| 成本 | 万相2.7 = 1 豆/张 | 图片 4.7 = 1 积分/张（非会员 5.0Pro 不可用） |
| 生成耗时 | 30-90s/张 | 30-60s/张（Agent 思考 + 生成） |
| 多图 | 串行，每张开新 tab | 串行，每次新对话（避免 Agent 上下文污染） |

## Target Profiles

复用搞定设计的 profile 机制，但 **prompt 格式不同**（即梦不含精确像素，只描述用途+比例，让 Agent 自动选合规尺寸）：

| Profile | target_label | 比例描述 | prompt_language | crop_size | Agent 自动选比例 |
|---------|-------------|---------|----------------|-----------|----------------|
| wechat-cover | 微信公众号封面图 | 宽幅横版banner比例约2.35:1 | 中文视觉描述 | 900x383 | 21:9（≈2.333） |
| illustration | 文章插图 | 16:9宽幅横版比例 | 中文视觉描述 | 1920x1080 | 16:9 |

**Prompt 格式**（由 profile 参数拼接，**不含精确像素**）：

```
生成一张{target_label}，{比例描述}。画面：{visual_prompt}
```

示例：
- wechat-cover: `生成一张微信公众号封面图，宽幅横版banner比例约2.35:1。画面：一个现代简约的科技工作空间，干净的书桌上有一台笔记本电脑，柔和的暖色光线，蓝色和橙色作为强调色，扁平化矢量插画风格。`
- illustration: `生成一张文章插图，16:9宽幅横版比例。画面：...`

> ⛔ **禁止在 prompt 中包含精确像素尺寸**（如"900x383像素"）。即梦 Agent 会读到精确尺寸并试图用该尺寸生成，但模型对尺寸有硬约束（2K 分辨率下宽高均需 1296-3024），会导致 Agent 反复重算合规尺寸，消耗大量时间和积分。只描述用途+比例，Agent 会自动选最近的合规比例（21:9 → 3024x1296）。

## 前置条件

- Chrome 由 chrome-devtools MCP 自动启动并管理（已登录即梦 session）
- 用户已在 `jimeng.jianying.com` 登录过（字节系账号：抖音/剪映/头条通用；session 持久化在 Chrome profile 中）
- Prompt 已由调用方 agent 准备好（含 profile 对应的 visual_prompt，**不含精确像素**）

## 完整步骤

### A. 连接、进入图片生成界面、登录检查

1. `list_pages` 验证 MCP 连接可用（Chrome 由 chrome-devtools MCP 自动启动）。
2. `navigate_page` → `https://jimeng.jianying.com/ai-tool/image-generate`（会重定向到 `/ai-tool/home`）。
3. `take_snapshot` 检查页面状态：
   - **已登录**：顶部右侧显示用户头像/用户名（如"Octo"）+ 积分（如"63 开会员"），无"登录"按钮 → 继续
   - **未登录**：顶部出现"登录"按钮 → 提示用户在浏览器中登录（字节系账号），`wait_for` 等待用户名/积分文字出现（timeout 180s）。超时则回退 Agnes。
4. 进入图片生成界面：从首页点"图片"快捷入口（`take_snapshot` 找含"图片 5.0 Pro"或"图片 5.0"文字的 button，`click` 它）。
   - 导航后 URL 变为 `https://jimeng.jianying.com/ai-tool/generate?enter_from=...&ai_feature_name=image`
   - 页面显示：左侧"开启创作"+对话历史，中间"你好，想创作什么？"+输入框，底部工具栏

### B. 确认 Agent 模式 + 锁定模型 4.7

> **每张图生成前都要复核这两项**：Agent 模式可能因导航重置，模型可能被重置回默认。

5. `take_snapshot` 确认底部工具栏的模式 combobox 显示"Agent 模式"。
   - 若不是"Agent 模式"（如显示"图片生成"）：`evaluate_script` 点击该 combobox → listbox 选"Agent 模式"。
6. **打开"生成偏好"面板**：`evaluate_script` 点击底部工具栏的"自动"按钮（button，innerText === "自动"）。
   - 面板展开后出现：`生成偏好` 标题 + `自动` switch + 图片/视频 radio + 比例选择 + `其他设置` + 模型 button + 分辨率 combobox。
7. **关闭"自动"开关**：`evaluate_script` 点击 `自动` switch（`[role="switch"]`）。
   - 关闭后：底部工具栏的按钮文字从"自动"变为"自定义"。
   - **这一步是关键**：关闭"自动"后，Agent 仍理解 prompt，但不再自行改模型/比例，避免降级循环。
8. **选模型 4.7**：
   - `evaluate_script` 点击"其他设置"下方的模型 button（innerText 含"图片"，如"图片 4.0"/"图片 5.0 Pro"）。
   - 展开 listbox（`[role="listbox"]`），含 9 个模型选项（5.0 Pro / 5.0 Lite / 4.7 / 4.6 / 4.5 / 4.1 / 4.0 / 3.1 / 3.0）。
   - `evaluate_script` 点击 listbox 中 `[role="option"]` 文本含"图片 4.7"的项。
   - 确认模型 button 文字变为"图片 4.7"。
   - 模型由 `config.backend.jimeng_model` 配置（默认 **图片 4.7**）。若需其他模型，按相同步骤选。
9. （可选）选比例：若 profile 明确要求某比例（如 wechat-cover 要求 21:9），在面板的比例 radio 中选对应项；否则保持"智能"让 Agent 自动选。
10. `press_key` Escape 关闭"生成偏好"面板。

> **选型经验**：
> - **图片 4.7**（默认，推荐）：画质全面优化，指令响应能力强，1 积分/张，非会员可用。
> - **图片 5.0 Pro**：商业设计/影视/高密度图文场景效果最好，但**非会员不可用**（Agent 会自动降级）。
> - **图片 3.0**：影视质感，文字渲染准，直出 2K 高清图——若图内需中文文字可考虑。

### C. 输入 Prompt

11. 通过 `evaluate_script` 向 contenteditable 输入框填入 prompt（**不含精确像素**）：

```javascript
() => {
  const editor = document.querySelector('[contenteditable="true"]');
  if (!editor) return { error: 'editor not found' };
  editor.focus();
  editor.innerHTML = '';
  document.execCommand('insertText', false, '生成一张{target_label}，{比例描述}。画面：{VISUAL_PROMPT}');
  return { success: true, text: editor.innerText.slice(0, 50), length: editor.innerText.length };
}
```

> 注意：使用 `document.execCommand('insertText')` 而非 `innerHTML` 赋值，前者能正确触发即梦 React 编辑器的内部监听器（已验证有效）。

12. `take_snapshot` 确认输入框 value 已更新，且底部发送按钮（`button`，`lv-btn-primary` class，约 36x36）已 enabled（不再 disabled）。

### D. 生成图片

13. 点击发送按钮（MCP click 可能对 React 按钮无效，用 JS dispatchEvent）：

```javascript
() => {
  const editor = document.querySelector('[contenteditable="true"]');
  const container = editor?.closest('[class*="input"], [class*="sender"], [class*="chat"], form');
  const btns = container ? Array.from(container.querySelectorAll('button')).filter(b => {
    const r = b.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && !b.disabled;
  }) : [];
  // 发送按钮：class 含 lv-btn-primary 的最右按钮
  const sendBtn = btns.find(b => (typeof b.className === 'string' && b.className.includes('lv-btn-primary')))
    || btns.sort((a,b) => b.getBoundingClientRect().right - a.getBoundingClientRect().right)[0];
  if (!sendBtn) return { error: 'send button not found' };
  const rect = sendBtn.getBoundingClientRect();
  const x = rect.left + rect.width/2, y = rect.top + rect.height/2;
  ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(type => {
    sendBtn.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0 }));
  });
  return { clicked: true };
}
```

14. 等待生成完成：
    - 通过 `wait_for` 检测 "已完成" / "生成失败" / "内容违规" / "重新生成" 文字（timeout 180s）。
    - 生成过程中页面会显示 Agent 的流式"思考中"推理文本（逐字输出）+ "生成中..." 状态。
    - **⛔ 必须检测失败态**：若出现"生成失败"/"内容违规"/"无法生成"等文字，判定该张失败，不进入下载。
    - 成功标志：出现"已完成" + "本次消耗 N 积分" + 结果图渲染（4 张缩略图，21:9 横版）。
    - **注意**：生成需要 30-60s（Agent 思考 + 模型生成），切勿在未确认完成前重复点击发送按钮（每次都会消耗积分）。

### E. 下载图片

15. 点击第一张结果图打开大图查看器：
    - `evaluate_script` 找页面上可见的大尺寸 img（`getBoundingClientRect().width > 200 && height > 100`），dispatchEvent 完整点击事件序列到第一张。
    - 或 `take_snapshot` 找结果区的 `generic roledescription="draggable"` button（4 张图都是 draggable），`click` 第一个。
16. 大图查看器（dialog modal）弹出后，`take_snapshot` 定位"下载"按钮（button，innerText === "下载"）。
17. `click` 点击"下载"按钮 → 浏览器直接下载到 `chrome_download_dir`（无需进编辑器、无需取消社区发布）。
18. 等待下载完成（`sleep 5`），从 Chrome 下载目录取最新文件复制到输出目录：
    ```bash
    sleep 5
    latest=$(ls -t "${AINews_DOWNLOAD_DIR:-$HOME/Downloads}"/jimeng-*.{png,jpg,jpeg,PNG,JPG,JPEG} 2>/dev/null | head -1)
    if [ -n "$latest" ] && [ "$(wc -c < "$latest")" -gt 5000 ]; then
      cp "$latest" "{output_dir}/{filename}_raw.png"
    fi
    ```
    > 即梦下载文件名格式：`jimeng-{YYYY-MM-DD}-{序号}-{prompt片段}.png`，用 `jimeng-` 前缀过滤可避免误取其他来源的图。
19. `press_key` Escape 关闭大图查看器。

### F. 裁剪与验证

20. 裁剪到 profile 对应的精确目标尺寸（使用 PIL）。**必须先按目标比例中心裁剪、再 resize**——即梦 21:9 输出 3024x1296（2.333:1），与封面目标 900x383（2.35:1）略有差异，直接 resize 会轻微变形：
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
    其中 `{crop_width}` 和 `{crop_height}` 来自 profile 的 `crop_size`（wechat-cover 为 900x383，illustration 为 1920x1080）。

21. 验证输出文件存在且大小 > 5KB。
22. 删除中间文件 `{filename}_raw.png`。

## 默认设置

| 设置项 | 值 | 说明 |
|--------|-----|------|
| 模式 | Agent 模式（默认） | 即梦的对话式生成，LLM 理解 prompt 后调模型 |
| 自动开关 | **关闭**（手动锁参数） | 避免 Agent 自行改模型导致降级循环 |
| 模型 | 图片 4.7（默认，可配置 `config.backend.jimeng_model`） | 画质优化+指令响应，1 积分/张，非会员可用 |
| 比例 | 智能或 21:9/16:9 | Agent 自动选，或在"生成偏好"面板手动选 |
| 分辨率 | 高清 2K（默认） | 4.7 模型不支持标清 1K；输出 3024x1296（21:9） |
| 消耗 | 图片 4.7：1 积分/张 | 切勿重复点击发送按钮 |

## 错误处理与回退

| 场景 | 处理 |
|------|------|
| Chrome 未运行 / CDP 失败 | 启动 Chrome；仍失败则回退 Agnes |
| 未登录且用户超时未登录 | 回退 Agnes |
| 模型被重置（导航后） | 每张生成前 `take_snapshot` 复核，被重置就重选 4.7 |
| "自动"开关被重置（变回"自动"） | 每张生成前复核，是则重新关闭+重选模型 |
| Prompt 输入框未找到 | 重试一次；仍失败回退 |
| 发送按钮 disabled | 确认 prompt 已正确写入（React 状态更新）；用 `execCommand('insertText')` 而非 `innerHTML` |
| 生成超时（180s） | `wait_for` 检测完成/失败文字；两次超时回退 |
| **内容审核拒绝**（页面含「生成失败 / 内容违规 / 无法生成」） | **不要回退**——改写 prompt（去掉触发词、中性化）后在即梦重试 1 次；仍拒则判定该张失败（插图跳过、封面暂停） |
| 下载失败 / 文件未找到 | 重试下载一次；仍失败回退 |
| 下载文件 < 5KB | 删除后回退 |
| 大图查看器未弹出 | 重试点击结果图；仍失败回退 |

**回退协议**：失败后默认调用 Agnes 路径（`agnes_image.py`）并记录 `fallback_used: true`。**例外：内容审核拒绝不回退**（见上表，改写重试）。与搞定设计的回退策略一致。

## URL 与环境

| 项目 | 值 |
|------|-----|
| 入口（重定向到 home） | `https://jimeng.jianying.com/ai-tool/image-generate` |
| 首页 | `https://jimeng.jianying.com/ai-tool/home` |
| 图片生成界面（点快捷入口后） | `https://jimeng.jianying.com/ai-tool/generate?enter_from=...&ai_feature_name=image` |
| 主站 | `https://jimeng.jianying.com/` |
| Chrome 下载目录 | 浏览器默认下载目录（或 `config.chrome_download_dir` / `AINews_DOWNLOAD_DIR` 指定） |
| 下载文件名格式 | `jimeng-{YYYY-MM-DD}-{序号}-{prompt片段}.png` |

## 注意事项

- 即梦是字节跳动产品，登录用字节系账号（抖音/剪映/头条通用），登录 session 由 chrome-devtools MCP 的 user-data-dir 持久化。
- **Agent 模式的"思考"是正常行为**：生成过程中页面会流式显示 Agent 的推理文本（逐字输出"思考中..."），这是 LLM 在理解 prompt 并选参数，不是卡死。耐心等到"已完成"。
- **关闭"自动"开关的意义**：开启时 Agent 全自动决策（含模型），非会员会触发 5.0Pro→4.5 降级循环（消耗时间和积分）；关闭后 Agent 仍理解 prompt 但锁定模型，稳定高效。
- **prompt 不含精确像素是关键**：即梦 Agent 会读到精确尺寸并试图用该尺寸生成，但模型对尺寸有硬约束（2K 下宽高均需 1296-3024），导致反复重算。只描述用途+比例（如"宽幅横版banner比例约2.35:1"），Agent 自动选 21:9（3024x1296）。
- 每次生成消耗积分：图片 4.7 为 **1 积分/张**。**切勿重复点击发送按钮**，每次点击都会消耗积分。
- 下载比搞定设计简单：点结果图 → 大图查看器 → "下载"按钮，**无需进编辑器、无需取消社区发布勾选**。
- 生成结果默认一次 4 张（21:9 横版时），但只需下载第一张（或选最满意的一张）。翻页用大图查看器的导航按钮（显示"1/4"）。
- 生成完成后即梦会自动给结果命名（如"现代简约科技办公场景图"），左侧对话历史可见。

## 串行生成模式（多张图时的默认做法）

> **⚠️ 重要**：与搞定设计一样，多张图必须**串行**，每张图用一个全新的对话（`新对话` 或重新进入图片生成界面），避免 Agent 的对话上下文污染（后续图会受前一张 prompt 影响，导致风格/内容雷同）。

### 根因（为什么不能在同一对话连发）

1. **Agent 上下文累积**：即梦 Agent 模式下，同一对话的 prompt 历史会累积，Agent 会"看着历史对话"生成，导致后续图片和第一张雷同或被历史风格带偏。
2. **React 状态残留**：同一输入框内反复 `innerHTML='' + execCommand('insertText')` 不能可靠触发 React 状态更新（与搞定设计同构问题）。

### 正确做法：每张图用一个全新的对话

**核心原则：每张图 = 一个新对话 = 干净的 Agent 上下文。**

#### 完整流程（每张图重复一遍）

1. **开新对话**：
   - 方式 A（推荐）：`navigate_page` → `https://jimeng.jianying.com/ai-tool/image-generate` → 点"图片"快捷入口重新进入（最干净）
   - 方式 B：`click` 左侧"新对话"按钮（若有）
2. **等待页面加载**：`sleep 3000`，确认输入框存在
3. **复核并锁定参数**（每个新对话都要重做，因为状态会重置）：
   - 确认模式 = "Agent 模式"（Step B-5）
   - 打开"生成偏好" → 关闭"自动" → 选模型"图片 4.7"（Step B-6~8）
   - 关闭面板（Step B-10）
4. **输入 prompt**（Step C-11）
5. **⛔ 验证 React 拿到了正确文本**：
   ```javascript
   const check = document.querySelector('[contenteditable="true"]');
   return { text: check.innerText.slice(0, 50), length: check.innerText.length };
   ```
   确认返回的文本是当前 prompt（而非上一张残留）。
6. **点击发送**（Step D-13）
7. **等待"已完成"**（Step D-14）
8. **下载**（Step E-15~19）
9. **裁剪到目标尺寸**（Step F-20）

#### 为什么这样做可靠

- 每张图用全新对话 → Agent 上下文干净、无风格污染
- 每张图独立锁定模型 4.7 → 不会降级循环
- 每张图独立验证 + 文件名确认（`jimeng-` 前缀）→ 不会拿错图
- 代价：比并行慢（每张约 40-70s），但可靠

### 图片 4.7 的能力边界（避免反复试错）

- **擅长**：具体场景（咖啡馆、办公桌）、具象物品、扁平矢量插画、3D 等距插画、中文文字渲染（印刷级，但文字越少越可靠）
- **不擅长**：抽象技术概念（同搞定设计万相2.7）→ 遇到抽象概念，换具象比喻
- **中文文字**：图片 4.7 支持图内中文文字渲染，但若需大量密集文字，可考虑改用图片 3.0（"文字更准，直出2k高清图"）
