# 微信公众号 (wechat_mp) — 混合模式（API 创建草稿 + 浏览器发表）

公众号通过 API 创建草稿（自动上传封面、填充正文），再用浏览器打开草稿完成设置并发表。

原因：浏览器自动化上传封面图片不稳定（React 重渲染清空文件 input），API 方式可靠。

## 前置条件

- **IP 白名单**：API 调用需要将当前机器的公网 IP 加入微信公众号后台白名单。路径：公众号后台 → 设置与开发 → 基本配置 → IP 白名单。如果脚本报错 `40164`，说明 IP 未加白名单，需先完成此配置

## 微信 HTML 兼容性要点

微信 API 会对草稿 HTML 进行二次处理，以下是不兼容的写法和推荐替代方案：

| 不兼容 | 推荐 | 原因 |
|--------|------|------|
| `<h2>` 标签 | `<section>` + `<p style="font-weight:bold">` + 左边框 | `<h2>` 在微信中样式渲染异常或被忽略 |
| `<section>` 全文包裹 | 不使用外层 `<section>` | 微信可能剥离或重组 `<section>` 结构 |
| HTML 中的空行 | 所有标签紧挨排列，无空行 | 空行被微信解析为 `<br>` 或导致结构断裂 |
| Markdown `![]()` 语法 | 必须转为 `<img>` 标签 | xiaohu（`md-to-wechat-html-xiaohu.py`）原生支持 |
| `<img src="imgs/...">` 本地路径 | 先通过 API 上传获取微信 URL，直接嵌入 | `process_inline_images` 可能匹配失败，微信二次处理会破坏含本地路径的 HTML |
| **Markdown `>` 引用块（blockquote）** | **可放心使用 `>`** | xiaohu 把 `<blockquote>` 转成 `<section data-role="blockquote">` 并注入内联样式（背景色/边框/圆角），规避微信原生引用块渲染问题，版式美观。需要引用原文时，也可用「普通段落 + 中文引号""+ 加粗」作为通用写法。 |

**推荐的小标题 HTML 模板**：
```html
<section style="margin:24px 0 12px;padding:4px 0 4px 12px;border-left:3px solid #2b2b2b;">
<p style="font-size:17px;font-weight:bold;color:#2b2b2b;margin:0;">小标题文本</p>
</section>
```

**推荐的图片 HTML**（使用微信 URL，不用本地路径）：
```html
<p style="text-align:center;"><img src="https://mmbiz.qpic.cn/..."></p>
```

## 第一阶段：API 创建/更新草稿

### 创建新草稿

1. **确保标题格式正确**：`公众号_文章.md` 中必须包含 `# 标题内容`（H1 格式）行。脚本取第一个 `# ` 开头的行作为标题，缺少标题会直接报错退出

2. **引用块可放心使用**。正文可包含 Markdown 引用块（`>` 开头的段落）、`> [!tip]` callout、`>>` 金句卡——xiaohu 会把它们转成带内联样式的 `<section>`，规避微信原生引用块渲染问题。详见上文「微信 HTML 兼容性要点」表。

3. 运行脚本（**不要传 `--html-file`**，让脚本用 xiaohu 直接转 markdown）：
   ```bash
   python skills/browser-publisher/scripts/wechat-mp-draft.py --project-dir "<项目目录>"
   # 文章文件名不是「公众号_文章.md」时，用 --md 指定（避免手动 cp 一份到约定文件名）：
   python skills/browser-publisher/scripts/wechat-mp-draft.py --project-dir "<项目目录>" --md "<文章路径>"
   # 指定主题（默认 github，可选 chinese/elegant-classic/newspaper 等 41 个）：
   python skills/browser-publisher/scripts/wechat-mp-draft.py --project-dir "<项目目录>" --theme github
   # 查看可用主题：ls skills/browser-publisher/scripts/xiaohu-format/themes/
   ```
   - 默认读取 `<project-dir>/公众号_文章.md`；用 `--md` 可指向任意 markdown 文件（绝对或相对路径）
   - 脚本读取环境变量 `WECHAT_MP_APPID` 和 `WECHAT_MP_APPSECRET`
   - 自动：xiaohu 解析 Markdown → 获取 token → **上传内嵌图片** → 上传封面 → 创建草稿
   - **Markdown 转 HTML**：使用 xiaohu（`md-to-wechat-html-xiaohu.py`），支持完整 markdown 语法包括 `![alt](path)` 图片、`## ` 标题、`>` 引用块
   - **摘要**：优先读 `<project-dir>/公众号_摘要.txt`，不存在时才用引擎截断版
   - **内嵌图片**：自动扫描 HTML 中 `<img src="imgs/...">` 引用，通过微信 `uploadimg` API 上传并替换为微信 URL
   - 封面可选：如 `公众号_封面.png` 不存在，会无封面创建草稿
   - 成功输出：`{"success": true, "media_id": "xxx", "title": "xxx", "author": "xxx", "has_cover": true/false, "inline_images": N}`

4. **避免使用 `--html-file`**：传入 `--html-file` 会跳过 xiaohu，直接使用手写 HTML。手写 HTML 容易出现图片语法未转换、标签不兼容微信等问题。只在特殊情况下使用。如果必须用 `--html-file` 且 HTML 中缺少 `<h1>` 标签，用 `--title` 参数提供标题：
   ```bash
   python skills/browser-publisher/scripts/wechat-mp-draft.py --project-dir "<项目目录>" --html-file "<HTML文件>" --title "文章标题"
   ```

5. 如果脚本失败（环境变量缺失、API 错误、标题缺失），向用户报告错误并停止

### 创建后验证（必须）

草稿创建后，**必须通过 API 回读草稿内容进行验证**，确认标题、图片、正文在微信端渲染正确。不要仅依赖脚本返回的 `success: true`——微信 API 会二次处理 HTML，可能导致图片丢失、标签转义、文本截断等问题。

验证方法：调用 `POST /cgi-bin/draft/get` 回读草稿，检查以下项：

```bash
# 用子 agent 执行验证，或直接调用：
python -c "
import json
from pathlib import Path
from urllib.request import urlopen, Request

TOKEN_CACHE = Path('skills/browser-publisher/configs/browser-auth/wechat-mp-token.json')
token = json.loads(TOKEN_CACHE.read_text(encoding='utf-8'))['access_token']
data = json.dumps({'media_id': 'MEDIA_ID_HERE'}).encode('utf-8')
req = Request(f'https://api.weixin.qq.com/cgi-bin/draft/get?access_token={token}', data=data, method='POST')
req.add_header('Content-Type', 'application/json')
resp = json.loads(urlopen(req, timeout=30).read())
item = resp['news_item'][0]
print('Title:', item['title'])
print('Images:', len(__import__('re').findall(r'<img[^>]*data-src=\"http', item['content'])))
print('Problems:', bool(__import__('re').search(r'&lt;|&gt;|imgs/', item['content'])))
"
```

**检查清单**：

| 检查项 | 通过条件 | 常见问题 |
|--------|---------|---------|
| 标题 | `title` 字段非空、无 HTML 标签 | `md-to-wechat-html-xiaohu` 未正确提取 |
| 图片数量 | `content` 中 `<img data-src="http...">` 数量与预期一致 | `process_inline_images` 未匹配到 `<img>` 标签（markdown `![]()` 未转 HTML） |
| 图片 URL | 所有 `data-src` 以 `https://mmbiz.qpic.cn/` 开头 | 上传失败或本地路径未替换 |
| 无转义残留 | `content` 中无 `&lt;`、`&gt;` | 微信二次处理导致 HTML 标签被转义 |
| 无本地路径 | `content` 中无 `imgs/` 引用 | 图片上传失败，保留原本地路径 |

**如果验证失败**：删除问题草稿，修复 HTML 后重新创建。避免在问题草稿上反复更新——直接删除重建更可靠。

### 更新已有草稿（标题/封面/摘要变更后）

当草稿已创建但需要修改标题、封面或摘要时，运行更新脚本：

```bash
python skills/browser-publisher/scripts/wechat-mp-update-draft.py \
  --media-id "<media_id>" \
  [--title "新标题"] \
  [--cover "封面图路径"] \
  [--digest "摘要"] \
  [--project-dir "<项目目录>"]
```

- `--media-id` 必填，创建草稿时返回的 media_id
- `--title`、`--cover`、`--digest` 按需传入，未传入的字段保持不变
- `--project-dir` 可选，如提供了项目目录且存在 `公众号_摘要.txt`，自动读取作为摘要（优先级低于 `--digest`）
- 成功输出：`{"success": true, "media_id": "xxx", "title": "xxx", "cover_updated": true/false}`

## 第二阶段：浏览器设置与发表

### 1. 导航到草稿箱

`navigate_page` → `https://mp.weixin.qq.com/`

- Session 过期处理：如果页面跳转到登录页，直接再次导航到 `https://mp.weixin.qq.com/` 即可恢复（无需重新扫码）
- 导航到草稿箱列表页

### 2. 找到并打开草稿编辑器

刚创建的草稿应在列表顶部。**不要点击草稿标题**（会打开预览页而非编辑器）。正确方式：hover 到草稿行上，点击出现的"发表"按钮。这会在新标签页打开编辑器

- MCP click 可能无法点击"发表"链接，用 evaluate_script 降级：
  ```javascript
  () => {
    const links = document.querySelectorAll('a');
    for (const link of links) {
      if (link.textContent.trim() === '发表') { link.click(); return 'clicked'; }
    }
    return 'not found';
  }
  ```
- 点击后用 `list_pages` 检查新打开的页面，用 `select_page` 切换到编辑器标签页
- 如果多次点击打开了多个编辑器标签，关闭多余标签，只保留一个

### 3-7. 批量设置（原创 + 合集 + 来源 + 摘要 + 留言）

以下 5 项均为纯机械设置，使用一次 `evaluate_script` 批量完成，替代逐项 snapshot-click 循环：

```javascript
(digestText) => {
  const results = [];

  // 1. 原创声明 — 点击"原创"打开对话框
  const origBtn = [...document.querySelectorAll('*')].find(el =>
    el.textContent.trim() === '原创' && el.offsetParent !== null
  );
  if (origBtn) { origBtn.click(); results.push('原创: clicked'); }

  // 2. 合集 — 点击合集 icon
  // 合集名称需要从快照 uid 获取，此处只做打开操作

  // 3. 创作来源 — 设为"无需声明"
  // 从快照中获取 uid 后单独处理

  // 4. 摘要 — React native setter 填入
  setTimeout(() => {
    const textareas = document.querySelectorAll('textarea');
    for (const ta of textareas) {
      if (ta.placeholder && ta.placeholder.includes('摘要')) {
        const nativeSetter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
        nativeSetter.call(ta, digestText);
        ta.dispatchEvent(new Event('input', { bubbles: true }));
        results.push('摘要: filled');
        break;
      }
    }
  }, 500);

  return results.join(', ');
}
```

**批量设置流程**：
1. 先 `take_snapshot` 获取编辑器右侧设置面板的所有元素 uid
2. 用上面的 JS 处理摘要填写
3. 原创声明、合集、创作来源这些需要交互式对话框的项，按快照 uid 依次点击处理（但不再每步单独 take_snapshot，连续操作）
4. 留言开启：从快照中找到"留言"checkbox，点击开启

**如果批量 JS 执行失败**，退回逐项操作模式（原步骤 3-7）。

- 点击"原创"区域打开声明设置
- 选择"文字原创"，确认作者名正确
- 已开启快捷转载
- 弹出的声明对话框中需勾选"我已阅读并同意"协议
- 协议勾选框是 React 控制的，普通 `checkbox.click()` 无效。必须点击 `.weui-desktop-icon-checkbox` 图标元素：
  ```javascript
  () => {
    const labels = document.querySelectorAll('.weui-desktop-form__check-label');
    for (const label of labels) {
      if (label.textContent.includes('我已阅读并同意')) {
        const input = label.querySelector('input[type="checkbox"]');
        if (input && !input.checked) {
          const icon = label.querySelector('.weui-desktop-icon-checkbox');
          if (icon) { icon.click(); return 'was unchecked, clicked icon'; }
        } else if (input && input.checked) { return 'already checked'; }
      }
    }
    return 'label not found';
  }
  ```
- 如对话框报"请选择赞赏账户"错误，说明公众号未绑定赞赏账户，点击"取消"关闭，文章仍可正常发布

**对话框异常处理**：
- 点击"原创"后未弹出对话框 → `take_snapshot` 确认状态，可能已在之前操作中打开（检查页面中是否有 `.weui-desktop-dialog` 元素）
- 协议复选框已勾选（`input.checked === true`）→ 跳过勾选步骤，直接点击"确定"
- 每次对话框交互后 `take_snapshot` 确认状态变化（对话框是否关闭、设置是否生效），避免在过期快照上操作

### 8. 截图确认

`take_screenshot` 截图展示给用户确认标题、封面、正文、原创声明、合集、创作来源、摘要、留言已开启

### 9. 发表（三步确认）

发表流程有三个连续的确认步骤：

**第一步 — 点击"发表"按钮**
- 编辑器底部右侧的"发表"按钮
- 弹出"发表"对话框，包含：群发通知（默认勾选）、分组通知、定时发表等选项

**第二步 — 确认群发通知**
- 对话框中显示"已开启群发通知"提示，点击"继续发表"按钮
- 如 MCP click 无反应，用 evaluate_script 降级点击

**第三步 — 微信扫码验证**
- 弹出"微信验证"对话框，显示二维码
- 需要公众号管理员/运营者用微信扫码确认
- `take_screenshot` 截图给用户看二维码（可单独截图二维码元素更清晰）
- `wait_for` 等待"已群发"或"发布成功"出现（timeout 建议 180-300 秒）
- 扫码成功后页面显示"正在发表..."，随后自动跳转到公众号首页
- 首页"近期发表"列表中可确认发布状态（"审核中"或"已发表"）

## 音频素材上传（通用）

把音频文件（如播客生成的 mp3）上传为公众号永久 voice 素材，拿到 media_id 供后续使用：

```bash
python skills/browser-publisher/scripts/wechat-mp-upload-voice.py --file "<mp3路径>"
```

- 用途：把音频文件上传为公众号永久素材（type=voice），返回 `media_id`
- **限制**（微信 voice 素材约束）：格式 mp3/wma/wav/amr；大小 ≤30MB；时长 ≤30 分钟
- 超过 30 分钟的音频（如长播客）不能用此接口，改用文章正文放外链（如喜马拉雅）的方式
- 成功输出：`{"success": true, "media_id": "xxx", "filename": "xxx.mp3"}`

## 表格手机端横向滑动（已内置）

多列表格（≥4 列）在公众号手机端会被挤压变形。`wechat-mp-draft.py` 已内置自动处理：创建草稿时，所有 `<table>` 会被 `<div style="overflow-x:scroll;-webkit-overflow-scrolling:touch;">` 包裹，让宽表格在手机端可**左右滑动查看**。

- **无需手动处理**——脚本自动完成（日志会打印 `[table] wrapped N table(s)`）
- **实测有效**（2026-07）：通过 draft/add → draft/get 回读确认，微信完整保留 `overflow-x:scroll` 和 `-webkit-overflow-scrolling:touch`，未过滤
- 这颠覆了网上"公众号会过滤 overflow"的过时说法——实测 `<div>` 上的 inline `overflow-x:scroll` 是保留的

## 已知限制：音频组件无法自动化插入

公众号编辑器的"插入音频"操作**无法通过浏览器自动化可靠完成**，原因：

1. 编辑器是跨域 iframe + React contenteditable，主页面 JS 无法访问 iframe 内部 DOM
2. 音频选择器是动态加载的弹窗组件，元素 uid 在 snapshot 中不稳定
3. 需要先在正文里精确定位光标到目标段落，再触发音频弹窗选择已上传素材——这个光标定位在 contenteditable 里极不可靠

**替代方案（按优先级）**：

- **方案 A（推荐）：正文里放音频外链**。把要嵌入的音频先发到喜马拉雅等平台，拿到公开链接，在文章 markdown 里用 `[🎧 点击试听：xxx](https://www.ximalaya.com/sound/xxx)` 替代音频占位。读者点链接跳转收听，简单可靠。
- **方案 B：引导用户手动插入**。草稿创建好后，告知用户去草稿编辑器里手动点"音频"按钮插入已上传的素材（voice media_id 已通过上传脚本拿到）。适合必须用原生音频组件的场景。

**不要再尝试**用 MCP 工具点击编辑器工具栏的"Audio"按钮——实测在跨域 iframe + React 架构下会失败或进入不稳定状态。
