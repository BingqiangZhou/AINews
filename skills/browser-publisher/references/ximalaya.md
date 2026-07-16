# 喜马拉雅 (ximalaya)

**注意**：喜马拉雅上传页面在嵌套 iframe 中。快照中上传表单元素的 uid 前缀与主页面不同（如 `uid=73_*`），需注意区分。

## 发布步骤

1. **导航到上传页**：`navigate_page` → `https://studio.ximalaya.com/upload`

2. **检测登录**：`take_snapshot` 检查 — 页面标题应为"创作中心-喜马拉雅"，左上角显示用户名（如"小粥Joe"）

3. **上传音频**：在 iframe 中找到 `button "上传音频"`，`upload_file` 上传 `播客_TTS.mp3`。
   > **专辑自动选中**：上传成功后专辑会**自动选中**（显示"本专辑已发布 N 期"），无需手动点"选择专辑"。历史上文档写过"先选专辑再上传"，实测顺序相反——直接上传即可，专辑是默认绑定的。只有在多专辑账号需要切换时才点"选择专辑"。

4. **等待上传**：轮询 `take_snapshot` 检查，直到显示"上传成功"（同时会出现表单填写界面）

5. **填标题**：读取 `播客_标题与描述.txt` 解析标题（标题已含集号前缀，格式为四位零填充+中文全角冒号，如"0248："）。`fill` 标题输入框即可。**标题限 40 字**，超长需截断

6. **标记 AI 合成**：找到"是否AI合成"的 `radio "是"`，`fill`/`click` 选中（TTS 生成内容必选）

7. **填简介**：简介编辑器在**嵌套 iframe** 内（`reform-upload` iframe 里还有一层 iframe），**跨域**。
   - ❌ `evaluate_script` 从主 frame 注入文本会失败（`Blocked a frame ... from accessing a cross-origin frame`）
   - ✅ 正确做法：`click` 激活简介编辑器的 paragraph 元素 → `type_text` 输入（模拟键盘事件，能跨 iframe）

8. **添加标签**：`fill` 标签输入框 → 每个标签后按 `Enter`（`press_key`）确认。逐个输入，标签会变成 chip

9. **（可选）设置定时发布**：见下文「定时发布模式」

10. **确认发布**：确认"我已阅读并同意《知识产权承诺》"checkbox 已勾选（默认勾选）→ `click` 点 `button "确认发布"`
    > 发布成功后会**自动跳转到定时发布管理页**（`/timePublish`），列出所有排期中的作品。立即发布的作品也会短暂出现在这里（状态"审核成功"），定时发布的会显示倒计时。

11. **更新集号计数器**：发布成功后，运行 `bump_episode.py` 自动递增集号并清除 claimed 标记：
```bash
# 注意：bump_episode.py 在 audio-to-social skill 下，不在 browser-publisher
python skills/audio-to-social/scripts/bump_episode.py \
  --config skills/audio-to-social/config.json \
  --state "<播客 state.json 路径>" \
  --bump
```
如需强制修正集号，使用 `--set <N>` 参数（如 `--set 250`）。

## 定时发布模式

喜马拉雅支持定时发布——在上传表单底部有一个「定时发布」switch，开启后会展开日历时间选择器。发布后作品进入定时队列，到预设时间自动发布。

> **经验来源**：2026-07-08 实测（0248 期，定时 07-09 06:00）。此前文档未记录此功能，Explore agent 曾误报"喜马拉雅无定时发布自动化支持"——实际 UI 支持，只是文档没写。

### 设置步骤（在步骤 8 添加标签之后、步骤 10 确认发布之前）

1. **开启开关**：找到 `switch "定时发布"`（在"更多设置"附近），`click` 开启。开启后会显示一个 `textbox "选择发布时间"`（readonly）和一个日历图标

2. **打开日历**：`click` 日历图标（`generic "图标: calendar"`），展开日期+时间选择面板

3. **选日期**：日历默认显示当月，`click` 目标日期（如"9日"的 `button "9日"`）。选中后日期高亮

4. **选时间（小时+分钟）**：日历下方有时间选择区——
   - 上半区是小时（00-23 的 button），`click` 目标小时（如 `button "06"`）
   - 下半区是分钟（00-59 的 button），`click` 目标分钟（如 `button "00"`）

5. **确定**：`click` `button "确 定"` 确认时间选择

6. **验证**：`wait_for` 等待时间文本（如 `["2026-07-09 06:00"]`）出现在 `textbox "选择发布时间"` 的 value 中

### 注意事项

- **时间窗口**：提示文案写"您可以设置 2 小时后的时间点发布"——最早只能设到当前时间 +2 小时之后。例如现在 04:00，最早只能设 06:00。
- **readonly 输入框**：`textbox "选择发布时间"` 是 readonly，**不要用 `fill` 直接写值**（React 不会更新状态）。必须通过日历 UI 点选。
- **日历默认时间**：开启定时开关时，输入框默认填的是"当前时间 +2 小时"，点日历图标展开后从这个默认值开始改。
- **发布后状态**：定时发布的作品在管理页显示状态为"转码中"→"审核成功"→（到时间）自动发布。转码中是正常流程。
- **管理页**：`https://studio.ximalaya.com/timePublish` 可查看/编辑/删除所有排期作品，左侧导航也有"定时发布"入口。

### 与抖音定时发布的对比

| | 喜马拉雅 | 抖音 |
|---|---|---|
| 开关位置 | 上传表单底部 `switch` | 发布弹窗 `checkbox` |
| 时间选择 | 日历 UI（点日期+小时+分钟） | 日期 input（`fill` 值 `"YYYY-MM-DD HH:MM"`） |
| 时间格式 | 分散点选，无统一输入框 | 单个 input，可 `fill` |
| JS 降级 | 未需要（UI 点选稳定） | 需要（`evaluate_script` 文本点击链） |
| 发布后 | 跳转定时发布管理页 | 返回 `status: "scheduled"` |

抖音的定时发布已有 `publish_mode: "timed"` + `scheduled_at` 协议（见 SKILL.md）；喜马拉雅目前走 UI 点选，未抽象成参数协议。如需参数化，可在调用方约定一个 `scheduled_at: "YYYY-MM-DD HH:MM"` 字段，由 browser-publisher 在步骤 9 解析并操作日历。
