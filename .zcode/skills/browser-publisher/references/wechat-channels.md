# 微信视频号 (wechat_channels)

通过「视频号助手」网页端（`channels.weixin.qq.com`）发布短视频。微信扫码登录后，PC 端上传视频画质优于手机端。

> 与抖音/小红书的关键差异：
> - **封面**：PC 端视频号助手**不支持自定义上传封面图**，只能从视频帧中选取。本流水线视频第一帧已是 article-to-video 设计的大标题封面，直接选第一帧即可。
> - **短标题硬限制 16 字符**（不是 60 字）：视频号标题字段叫「短标题」，超 16 字符红字报错且无法发表。文案标题需重拟精简版。
> - **话题标签写在描述里**：用 ` #话题名` 文本格式追加到描述末尾，视频号自动解析为话题，不强制走下拉联想。
> - **登录**：复用 Chrome profile 登录态（同账号已登录公众号 mp.weixin.qq.com 不代表视频号已登录，视频号需单独扫码授权）。登录页 `https://channels.weixin.qq.com/login.html`，登录后跳 `/platform`。
> - **⚠️ 表单全在 `iframe[name="content"]` 内**（真实 URL `/micro/content/post/create`，同源可访问其 contentDocument）。MCP `evaluate_script` 默认在顶层 document 执行，**操作表单元素必须先进入该 iframe**：`document.querySelector('iframe[name="content"]').contentDocument.querySelector(...)`。MCP `fill(uid)` 对 iframe 内元素不可达（报「未变交互」），`click(uid)`/`type_text`/`press_key` 走 a11y 可用。

## 文案格式

`视频号_文案.txt` 用 `---` 分隔描述和发布信息（沿用抖音文案格式）：

```
描述正文（≤1000 字，不带 # 开头）
---
标题：视频标题（≤60 字）
话题：#话题1 #话题2 #话题3
```

发布时取 `---` 之后的标题与话题；描述取 `---` 之前的内容。

## 发布步骤

1. **导航到视频号助手**：`navigate_page` → `https://channels.weixin.qq.com`
   - 未登录会跳 `/login.html`；已登录跳 `/platform`（首页，显示账号数据概览）
   - 若从编辑页导航触发 `beforeunload`，需 `handle_dialog accept`

2. **检测登录**：`take_snapshot` 或 `evaluate_script` 查 `location.href` 是否含 `login.html`
   - 在登录页：页面中央 iframe 显示二维码，手机微信扫码 → 手机上点「确认登录」。监听 URL 跳到 `/platform` 即登录成功（`wait_for` 文字不可靠，建议轮询 `location.href`）
   - 复用 `configs/browser-auth/chrome-profile` 登录态，之前登过可能免登

3. **进入「发表动态」页**：在 `/platform` 首页，`take_snapshot` 找到右上角 **「发表视频」按钮**（button 文本精确为「发表视频」），`click` → 跳转到 `/platform/post/create`（页面标题「视频管理 / 发表动态」）

4. **上传视频**：`take_snapshot` 找到上传按钮区域（button，tooltip 文本「上传时长8小时内，大小不超过20GB...格式为MP4/H.264格式」），对它直接 `upload_file`（指向上传区 uid 即可，MCP 会拦截文件选择器；**不需要先显示隐藏的 file input**）
   - 视频文件查找顺序：`_video/公众号_视频.mp4` → `抖音_短视频.mp4`（与抖音/小红书共用）
   - **重传处理**：如上传后页面异常，重新 `navigate_page` 到 `/platform/post/create` 从干净页面重传，不在脏草稿上重试

5. **等待上传 + 处理**：`take_snapshot` 看是否出现视频预览（含播放 `slider` + 「封面预览」+「个人主页卡片 3:4」/「分享卡片 4:3」）。出现即上传成功并可发表（视频号后端转码与发表解耦，预览出现即可继续，不必等转码完成）

6. **选择封面帧**：在封面选择区/视频预览条中选取视频帧。
   - PC 端**不能上传自定义封面**，只能从视频画面里选一帧
   - 本流水线视频第一帧是大标题居中封面（article-to-video Phase 5 合成），直接选第一帧（或时间轴 0:00 处）
   - 若需拖动时间轴选帧：`click` 时间轴起点或拖动游标到 0:00，点「选为封面」/「完成」

7. **填短标题**：从文案 `标题：` 行提取（视频号字段名是「短标题」，placeholder「填写短标题有机会获得更多流量」）
   - **硬限制 16 字符**（汉字/字母/数字/空格各算 1，实测超 16 会红字报「标题超过16字限制」且无法发表）。文案标题通常超长，必须重拟一个 ≤16 字符的精简版
   - 标题框是 **weui 受控 input**（class `weui-desktop-form__input`），且位于 `iframe[name="content"]` 内：
     - MCP `fill(uid)` 会报「未变交互」（iframe 内 a11y 元素不可达）
     - 用 `click(uid)` 聚焦 + `press_key Delete`/`Backspace` 清空 + `type_text` 输入（**type_text 模拟真实键盘，weui 能正确响应**）
     - 直接 evaluate_script 设 native setter **只改 DOM value 不改 React state**，校验仍按旧值报错——**不可用**

8. **填描述**：取 `---` 之前的描述内容。描述编辑器是 `iframe[name="content"]` 内的 `div.text-area > div.content`（Vue 富文本组件，非标准 contenteditable）
   - 描述**不能以 `#` 开头**（首行会被当话题标签）
   - 操作方式：`click(uid)` 聚焦描述区 → `type_text` 逐字注入（模拟键盘，Vue 能正确响应）
   - **清空已有描述**：click 描述区 → `press_key Control+A` 全选 → `press_key Backspace` 删除（**不要用 Delete，Vue 不响应**；也不要直接改 innerHTML，会被 Vue 覆盖）
   - ≤1000 字

9. **添加话题标签**：话题**写在描述里**，不是独立字段
   - 语法：在描述末尾追加 ` #话题名`（**话题名前必须有 `#`，话题间用空格分隔**）。实测视频号会把 `#中文话题` 文本解析为话题标签，不强制走下拉联想
   - 操作：先确保光标在描述末尾（click 描述区 + `press_key Control+End`），再 `type_text` 输入 ` #话题1 #话题2 ...`
   - ⚠️ **「#话题」按钮陷阱**：页面有「#话题」快捷按钮，点击会在**当前光标位置**插入 `#`（不是末尾）。若光标在描述开头，会把描述首字变成话题，污染描述。**用 `type_text` 直接输 `#` 更可控，不要点这个按钮**
   - 取文案 `话题：` 行解析，逐个用 `#话题名` 格式，建议 5-8 个

10. **设置 5 个发布选项**（位置 / 合集 / 活动 / 声明原创 / 视频标注）— ⚠️ **默认值不可靠**（实测同一账号两次发表，默认值不同：有时合集/声明原创/标注预填，有时全空）。**必须每项 DOM 读取核对，未满足才改**。字段都在 `iframe[name="content"]` 内：

    - **位置 → `不显示位置`**：默认可能是定位城市（如「湘潭市」）。改法：`click` 位置字段 → 弹出搜索面板，顶部第一项即「不显示位置」，`click` 它
    - **添加到合集 → `AI手记`**（或指定合集）：默认可能是「选择合集」（未选）。改法：`click` 合集字段 → 弹出含账号所有合集（`AI手记`/`播客`/...）+「创建新合集」的列表，`click` 目标合集项（item class `.item`，文本在 `.name`）。DOM 校验：`添加到合集` 后跟合集名
    - **活动 → `不参与活动`**：默认即此值，一般无需改
    - **声明原创 → 勾选**：Ant Design checkbox（非 weui），容器 `.declare-original-checkbox`，结构 `.ant-checkbox-wrapper > .ant-checkbox > input.ant-checkbox-input`。
        - ⚠️ **直接 `click(uid)` 或点 input 不生效**（ant 受控，不触发 onChange）。**必须 evaluate_script 点击 `.ant-checkbox-wrapper`（label）**：`doc.querySelector('.declare-original-checkbox .ant-checkbox-wrapper').click()`
        - 勾选后会**自动展开「原创权益」说明面板**（展示分成/保护权益，非模态框，**无需点任何确认按钮**，面板内那个 rect=0 的"声明原创"button 是隐藏触发器，不要点）
        - DOM 校验：`.declare-original-checkbox input.checked === true`
    - **视频标注 → `Contains AI-generated content`**（AI 生成内容）：Vue 自定义下拉 `.mark-tag-select`，选项 class `.mark-tag-option`，选中项带 `.is-selected`。默认可能是「选择视频标注」（未选）。
        - 改法：`click` 标注字段 → 弹出选项列表（No label needed / **Contains AI-generated content** / Fictional storyline... / Personal opinion... / Content contains ads / Self-recorded content / 等），`click` 目标项
        - DOM 校验：`.mark-tag-option.is-selected` 文本是否为「Contains AI-generated content」

    **批量核对脚本**（一次读全 5 项状态，发表前必跑）：
    ```javascript
    () => {
      const doc = document.querySelector('iframe[name="content"]').contentDocument;
      const b = doc.body.innerText;
      const orig = doc.querySelector('.declare-original-checkbox input');
      const tagSel = doc.querySelector('.mark-tag-option.is-selected');
      return JSON.stringify({
        位置: (b.match(/位置[\s\S]{0,8}/)||[])[0].replace(/\n/g,'|'),
        合集: (b.match(/添加到合集[\s\S]{0,8}/)||[])[0].replace(/\n/g,'|'),
        活动: b.includes('不参与活动') ? '不参与活动' : '其他',
        声明原创: orig ? !!orig.checked : 'n/a',
        视频标注: tagSel ? tagSel.innerText.trim() : '未选'
      });
    }
    ```

10b. **链接（可选）→ 公众号文章 URL**：仅当用户显式要求挂载公众号文章链接时执行，默认跳过。字段在 `iframe[name="content"]` 内 `.post-link-wrap`。
    - **前置硬条件**（视频号规则，页面提示原文）：「**文章需近7天发表且阅读量超过10000**」。不满足则视频号不解析链接，填了也白填——执行前先和用户确认文章是否达标
    - 操作：
      1. `click`「链接」字段（`.link-display-wrap`，文本「选择链接」）→ 弹出类型选项「公众号文章」/「红包封面」（`.link-option-item`）
      2. `click`「公众号文章」项 → 展开 URL 输入框（`input[placeholder="粘贴公众号文章链接"]`，weui input）
      3. 填 URL：用 `click` 输入框聚焦 + `type_text` 输入（weui 受控，同短标题；native setter 只改 DOM 不触发解析）
      4. 触发解析：按 `Enter` 或点页面其他位置失焦。解析成功会显示文章标题卡片；不成功（文章不达标）输入框附近提示「文章需近7天发表且阅读量超过10000」
    - **取消/清空链接**：重新 `click` `.link-display-wrap` 打开类型下拉 → 再次 `click`「公众号文章」项，即取消选中、输入框消失、字段回到「选择链接」
    - DOM 校验：`.post-link-wrap` 文本为「选择链接」=未挂载；为「公众号文章」+ 有解析出的标题卡片=已挂载

11. **截图确认**：`take_screenshot` 截图展示给用户，**用户确认后才继续发表**（面向平台不可逆）

12. **发表**：`click`「发表」按钮（页面底部，与「保存草稿」「手机预览」并排）
    - **实测：MCP `click(uid)` 直接生效，点击后立即跳转，无二次确认弹窗**（页面预生成的「手机预览」「下载二维码」等弹层是隐藏的无关弹窗，不用管）
    - 若 click 报 "did not become interactive"，用 [js-patterns.md](js-patterns.md) 第 1 节降级：在 `iframe[name="content"]` 内找文本 ===「发表」的 button `.click()`

13. **成功标志**：页面跳转到 **`/platform/post/list`**（视频管理列表页），新作品出现在列表顶部。发表即成功，无失败态
    - 列表项含完整描述文本 + 发表时间 + 状态标签（声明了原创的显示「**原创审核中**」→ 审核通过后转正常）
    - 顶部 tab「视频 (N)」的 N 会 +1
    - 落袋复核（如有延迟）：`navigate_page` 重载 `/platform/post/list` 后 `take_snapshot` 查顶部作品描述是否含刚发的标题/描述

---

## 已实测确认要点（2026-07-12 端到端验证）

- 登录：`channels.weixin.qq.com` → `/login.html`（二维码在 iframe 内）→ 手机扫码+确认 → 跳 `/platform`
- 发表入口：`/platform` 首页右上角「发表视频」button → `/platform/post/create`
- 表单全部在 `iframe[name="content"]`（URL `/micro/content/post/create`，同源）
- 上传：`upload_file` 指向上传区 button uid 即可，自动出现预览（slider + 封面预览）
- 短标题：weui input，**16 字符硬限制**，用 click+type_text 填（fill/native-setter 不可用）
- 描述：Vue 富文本 `div.text-area`，click+type_text 填，清空用 Ctrl+A + Backspace
- 话题：描述末尾 ` #话题名` 文本，逐个空格分隔（不要点「#话题」按钮，会插到光标处）
- 4 个发布选项默认值已满足要求（合集=AI手记 / 活动=不参与活动 / 声明原创=已勾选 / 视频标注=Contains AI-generated content），发表前用批量核对脚本读 DOM 确认
- ⚠️ **默认值不可靠**：同一账号第二次发表时合集/声明原创/视频标注全空，必须逐项主动设置（见第 10 步）
- **声明原创二次交互**：勾选后展开「原创权益」说明面板（非模态框，无需点确认按钮）；勾选要点 `.ant-checkbox-wrapper`（点 input 无效）
- **链接（公众号文章）硬条件**：「文章需近7天发表且阅读量超过10000」，不达标不解析
- **发表**：click「发表」按钮直接跳转 `/platform/post/list`，无二次确认；新作品状态「原创审核中」（声明了原创时）

## 仍需后续验证

- 定时发表模式（页面有「不定时/定时」radio，未实现；如需可仿 douyin.md 的 timed 模式）
