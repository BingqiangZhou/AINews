# Phase 7: 发布

> 本文件是 `SKILL.md` Phase 7（发布）的详细参考，由主流程按需加载。
>
> 注：旧版编号为 Phase 8；纯编排版把发布重编为 Phase 7（归档为 Phase 6）。

## Phase 7 — 发布（可选，用户主动触发）

此步骤需要用户明确要求才会执行。如果用户未提及发布，跳过。

### 发布前 Pre-flight

调用 `browser-publisher` skill 前先做发布前验证：

- 环境：浏览器/登录态/API 凭证可用，目标平台账号别名已解析
- 文件：各平台需要的正文、封面、音频存在且非空
- 字段：标题、摘要、话题、标签、描述、封面/首屏文案完整
- **公众号 HTML**：如果包含 `gongzhonghao`，需先有 `公众号_文章.html`。若缺失或较旧（修改时间早于 `公众号_文章.md`），重新运行：
  ```bash
  <py> {skill_dir}/scripts/markdown_to_wechat_html.py --input "{article_dir}/公众号_文章.md" --output "{article_dir}/公众号_文章.html" --theme "{config.publishing.html_theme}"
  ```
  验证标题保留、正文长度与 Markdown 差异 < 20%。
- 公众号内嵌图片：`wechat-mp-draft.js` 创建草稿时自动扫描 HTML 中的 `<img src="imgs/...">` 引用，通过微信 `uploadimg` API 上传并替换为微信 URL；webp 自动回退同名 PNG。
- 映射：本地文件到发布字段的映射生成 `{article_dir}/发布清单.md`
- 多账号：发布清单写明公众号、喜马拉雅目标账号；账号未解析时 pre-flight 失败
- 安全：发布/提交按钮需用户在当前会话明确确认（规则见 `SKILL.md` 确认规则）

### 图片 reconciliation 前置条件

当包含 `gongzhonghao` 时：

1. 检查 `state.json.stages.archive.reconciliation.status == "completed"`。
2. 否则重新执行 reconciliation（命令同 Phase 6 Operation A，见 `phase7-verify-archive.md`，加 `--require-cover --require-illustrations`）。
3. 失败或 `passed != true` → pre-flight 失败，不进入发布。

Pre-flight 通过后，调用 `browser-publisher` skill，传入 `{article_dir}`、`target_platforms`、`发布清单.md`。

### 发布后验证

发布完成后，对每个已发布平台执行内容完整性验证：

1. 通过浏览器 snapshot 读取实际发布页面内容。
2. 按平台检查：
   - **公众号**：标题与 `公众号_文章.md` 第一行一致、正文长度差异 < 20%、封面图已上传、内嵌图片数量匹配
   - **喜马拉雅**：音频已上传、标题与 `_podcast/播客_标题与描述.txt` 一致、描述已填入
3. 验证结果：全部通过 → 标记发布成功；有差异 → 列出差异项提示用户确认；严重缺失 → 报错建议重试。

更新 `state.json.publish.tracks.{platform}` + `publish_verification.tracks.{platform}`。

### 喜马拉雅集号递增

喜马拉雅（boker）发布成功后，运行 `bump_episode.py` 自动递增集号并清除 `episode_number_claimed` 标记。集号在 Phase 4 播客生成时已加入标题前缀，此处仅在发布确认成功后才递增——如果生成后未发布，集号不变，下次运行仍用相同集号。

```bash
<py> {skill_dir}/scripts/bump_episode.py --config "{config_path}" --state "{state_path}" --bump
```
