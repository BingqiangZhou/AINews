# 抖音 (douyin)

URL 参考：`references/platform-urls.md`

## 文案格式

`抖音_文案.txt` 使用 `---` 分隔口播文案和发布信息：
```
口播文案内容...
---
描述：短描述（50字以内）
话题：#话题1 #话题2 #话题3
```
发布时只取 `---` 之后的描述和话题，`---` 之前是口播文案（已合成到视频里）。

## 发布步骤

1. **导航到上传页**：`navigate_page` → `https://creator.douyin.com/creator-micro/content/upload`
   - 如果之前在编辑页面，导航时会触发 `beforeunload` 对话框，需 `handle_dialog accept` 确认离开

2. **检测登录**：`take_snapshot` — 如果页面包含"登录"相关元素，提示用户登录后继续

3. **上传视频**：`upload_file` 上传 `抖音_短视频.mp4`
   - **重传处理**：如 upload_file 后 React 重渲染清空了文件输入，必须重新导航到上传页从干净页面重新上传，不要在已有草稿上重试

4. **等待上传**：使用 `wait_for` 等待上传完成标志出现（如"上传完成"、"100%"、"发布"按钮可用），避免固定间隔轮询。如果 `wait_for` 不支持目标文字，退回 `take_snapshot` 轮询（间隔 10 秒）

5. **选择封面**：视频第一帧即为封面帧（大标题居中设计，已适配裁剪）。直接选第一帧即可

6. **填标题**：从文案第一行提取标题，`fill` 填入标题输入框（限 30 字）

7. **填描述**：取 `---` 之后的 `描述：` 内容。`click` 激活描述编辑器，`type_text` 输入（50 字以内）

8. **添加话题**：点击 `#添加话题`，逐个输入话题关键词（取 `话题：` 内容），从下拉列表选择匹配话题。每个 `#话题` 后**必须跟一个空格**，确保正确识别为话题标签

9. **设置保存权限**：在"发布设置"区域，`click` 选择 **不允许** 保存

10. **开启智能章节**：在"视频章节"区域，点击"智能生成"。短视频（< 2分钟）可能生成 0 个章节，此时关闭对话框跳过即可

11. **截图确认**：`take_screenshot` 截图展示给用户确认

12. **发布**：用户确认后点击发布按钮（见下方"发布按钮"，立即发布用 MCP `click`，定时发布用 `evaluate_script`）

---

## 定时发布模式（timed publish）

当编排器传入 `social_metadata.publish_mode == "timed"`（带 `scheduled_at`）时，在第 9 步（保存权限选"不允许"）之后、点发布之前，额外做定时设置。抖音定时仅支持 **当前时间 +2 小时 ~ +14 天** 的区间，超出会被前端拒收——排期阶段必须先校验。

### 9b. 勾选"定时发布"

"发布时间"区域有"立即发布 / 定时发布"两个 React checkbox。MCP `click` 常因遮挡超时，用 `evaluate_script` 文本点击链降级（点文本节点 + 向上遍历父级 label/div 各 click 一次，确保 React 收到事件）：

```javascript
() => {
  const leafs = [...document.querySelectorAll('*')].filter(e => {
    const own = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join('');
    return own === '定时发布';
  });
  if (!leafs.length) return '定时发布 not found';
  let el = leafs[0];
  for (let i = 0; i < 5 && el; i++) { el.click(); el = el.parentElement; }
  return 'clicked';
}
```

勾选后会显示一个"日期和时间" input（placeholder 含"日期和时间"），默认值为 now+2h。

### 9c. 设定日期时间

日期 input 是 React 受控元素，直接设 `.value` 不触发 onChange，必须用 native setter，值格式 `"YYYY-MM-DD HH:MM"`（注意是空格分隔、24 小时制）。**文本必须内联进 function body**，不能走 `args`（Chrome MCP 的 args 只收元素 uid）：

```javascript
() => {
  const el = document.querySelector('input[placeholder*="日期和时间"]')
    || [...document.querySelectorAll('input')].find(i => /^\d{4}-\d{2}-\d{2}/.test(i.value));
  if (!el) return 'date input not found';
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(el, '2026-06-23 06:00');   // ← 内联目标时间
  el.dispatchEvent(new Event('input', {bubbles:true}));
  el.dispatchEvent(new Event('change', {bubbles:true}));
  el.dispatchEvent(new Event('blur', {bubbles:true}));
  return 'date set: ' + el.value;
}
```

### 发布按钮（定时/立即通用降级）

发布按钮被"高清发布"等元素遮挡时，MCP `click(uid)` 会报 "did not become interactive" 超时。统一用 `evaluate_script` 找文本 === "发布" 的 button，`scrollIntoView({block:'center'})` 后 click。可把"校验日期 + 点击发布"合并成一个脚本，减少往返：

```javascript
() => {
  const d = document.querySelector('input[placeholder*="日期和时间"]');
  const dateVal = d ? d.value : 'none';
  const btn = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === '发布');
  if (!btn) return JSON.stringify({error:'no publish btn', dateVal});
  btn.scrollIntoView({block:'center'});
  btn.click();
  return JSON.stringify({clicked:true, dateVal});
}
```

### 成功标志与复核

- **提交成功**：页面跳转到 `content/manage?enter_from=publish`（点发布后立即跳转 = 成功提交）。
- **落袋复核**：刚提交的作品在 manage 列表渲染有延迟（snapshot 可能暂时不显示），**重载** `content/manage` 后用 `evaluate_script` 查 `document.body.innerText` 是否含目标日期（如 `2026年06月23日 06:00`）与标题；并看顶部"共 N 个作品"的 N 是否 +1。
- **状态流转**：定时作品先显示"审核中"→ 审核通过转"定时发布中" → 到点上线。属正常，无需干预。

> 保存权限"不允许"也可用同样的文本点击链（找文本"不允许"，向上遍历点击），MCP click 失效时降级。
