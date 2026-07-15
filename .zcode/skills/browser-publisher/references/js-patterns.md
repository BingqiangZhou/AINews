# 通用 JS 模式（React 控制页面元素）

各平台页面多为 React 控制，`mcp__chrome-devtools__click` / `fill` 常失效。以下 5 个 `evaluate_script` 降级技巧在各平台反复使用，发布前必读。

## 1. click 失效时的降级方案

当 `mcp__chrome-devtools__click` 点击按钮或链接无反应时（React 控制的元素常见），用 `mcp__chrome-devtools__evaluate_script` 降级：
```javascript
() => {
  const btn = [...document.querySelectorAll('button, a')].find(b => b.textContent.includes('目标文字'));
  if (btn) { btn.click(); return 'clicked'; }
  return 'not found';
}
```

## 2. React 控制的 checkbox

普通 `checkbox.click()` 在 React 控制的页面上无法触发状态更新。对于微信公众号的 weui 组件，需要点击 `.weui-desktop-icon-checkbox` 图标元素。

## 3. React 控制的 textarea/input

直接设置 `.value` 不会触发 React 的 onChange。必须使用 native setter：
```javascript
(valueText) => {
  const el = document.querySelector('textarea, input');
  if (el) {
    const nativeSetter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
    nativeSetter.call(el, valueText);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    return 'filled';
  }
  return 'not found';
}
```

> **⚠️ evaluate_script args 用法**：`args` 传的是字符串值（如摘要文本），不是元素 UID。不要与 `fill`/`click` 的 uid 参数混淆。如果需要操作特定元素，在函数体内用 `querySelector` 查找。

## 4. contenteditable 富文本注入

对于 `contenteditable="true"` 的编辑器（小红书），直接设置 innerHTML 并触发 input 事件：
```javascript
(htmlContent) => {
  const editor = document.querySelector('[contenteditable="true"]');
  if (editor) {
    editor.innerHTML = htmlContent;
    editor.dispatchEvent(new Event('input', { bubbles: true }));
    return 'content injected';
  }
  return 'editor not found';
}
```

## 5. 隐藏的 file input

上传文件时，如果 `take_snapshot` 中找不到 file input，用 evaluate_script 将其显示出来：
```javascript
() => {
  const input = document.querySelector('input[type="file"]');
  if (input) {
    input.style.display = 'block';
    input.style.opacity = '1';
    input.style.position = 'fixed';
    input.style.top = '0';
    input.style.left = '0';
    input.style.zIndex = '99999';
    return 'input made visible';
  }
  return 'input not found';
}
```

## 6. 文本点击链（checkbox/label 点击降级）

抖音发布设置里的"不允许""定时发布"等 React checkbox，MCP `click(uid)` 常报 "did not become interactive" 超时（被遮挡或 uid 在重渲染后失效）。降级：找到**自身直接文本**等于目标词的叶子节点，从它向上遍历父级（SPAN→LABEL→DIV…）逐个 `.click()`，确保 React 接收到事件：

```javascript
() => {
  const leafs = [...document.querySelectorAll('*')].filter(e => {
    const own = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join('');
    return own === '不允许';   // ← 内联目标词，如 '定时发布'
  });
  if (!leafs.length) return 'not found';
  let el = leafs[0];
  for (let i = 0; i < 5 && el; i++) { el.click(); el = el.parentElement; }
  return 'clicked';
}
```

要点：用"自身直接子文本节点 === 目标词"过滤，避免匹配到包含该词的更大容器（如整段"发布设置"）；目标词必须在 body 里唯一（"不允许""定时发布"都满足）。

## 7. 校验 + 动作合并脚本

点击发布（或提交）会立刻导航离开页面，想同时回带校验值（如刚设的日期）就和点击放一个脚本里：先读值，再点，return 时一起带回。导航在脚本返回后发生，返回值不丢：

```javascript
() => {
  const d = document.querySelector('input[placeholder*="日期和时间"]');
  const dateVal = d ? d.value : 'none';
  const btn = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === '发布');
  if (!btn) return JSON.stringify({error:'no btn', dateVal});
  btn.scrollIntoView({block:'center'});
  btn.click();
  return JSON.stringify({clicked:true, dateVal});
}
```

> **evaluate_script args 陷阱（重申）**：Chrome MCP 的 `args` 只接受元素 uid，传字符串会被当 uid 报 "not found"。任何要写入页面的文本（标题、日期、描述内容）都**内联进 function body**，不要走 args。
