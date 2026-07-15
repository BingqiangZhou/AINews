# 小红书 (xiaohongshu)

小红书以**视频笔记**形式发布，与抖音共用同一个视频（`抖音_短视频.mp4`）。

## 发布步骤

1. **导航到发布页**：`navigate_page` → `https://creator.xiaohongshu.com/publish/publish`

2. **检测登录**：`take_snapshot` 检查。平台可能显示登录页面，提示用户手动登录（手机号 + 验证码）

3. **选择发布视频**：在发布页面上选择"发布视频"入口。`take_snapshot` 找到"视频"tab 或入口按钮并 `click`

4. **上传视频**：找到视频上传区域（`input[type="file"][accept*="video"]`），`upload_file` 上传 `抖音_短视频.mp4`
   - 如 file input 不在快照中，用 [js-patterns.md](js-patterns.md) 中的「隐藏 file input」模式将其显示出来

5. **等待视频上传**：使用 `wait_for` 等待上传完成标志出现（如"上传完成"、"发布"按钮可用），避免固定间隔轮询。如果 `wait_for` 不支持目标文字，退回 `take_snapshot` 轮询（间隔 10 秒）

6. **选择封面**：视频第一帧即为封面帧（大标题居中设计）。在封面选择器中直接选取视频第一帧

7. **填标题**：从 `小红书_文案.md` 第一个 `# ` 行提取标题（去掉 `# ` 前缀）。**标题限 20 字**，超长必须截断。`fill` 填入标题输入框

8. **填正文描述**：
   - 正文内容**不能以 `#` 开头**，否则小红书会把首行当作话题标签
   - 用 [js-patterns.md](js-patterns.md) 中的「contenteditable 富文本注入」模式设置内容
   - 内容格式：`<p>第一段正文</p><p>第二段正文</p>`

9. **添加话题标签**：在正文末尾追加话题，使用 `#话题名` 格式，空格分隔。小红书自动识别为可点击标签

10. **原创声明**：勾选原创声明复选框。如 MCP `click` 无法直接点击，用 evaluate_script 查找包含"原创声明"文字的元素并点击关联 checkbox

11. **取消"允许正文复制"**：用 evaluate_script 找到并取消勾选包含"允许正文复制"文字的 checkbox

12. **截图确认并发布**：`take_screenshot` 截图展示给用户确认 → 用户确认后 `click` 发布按钮
