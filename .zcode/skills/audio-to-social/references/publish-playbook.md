# 发布手册（Publish Playbook）

> 一条内容从"文章写完"到"公众号 + 喜马拉雅双平台发布"的完整编排手册。跨 5 个 skill 协作，本文是顶层流程索引。**每次执行完整发布前必读**，避免现场拼顺序、踩重复坑。

## 完整流程（6 步，含产物依赖）

```text
① 封面 ──┐
② 插图 ──┤（两步可并行，都委托 article-cover-image-generator 批量）
         ├──→ ③ 公众号草稿（API，含封面+插图）──→ ③b 音频处理
④ 播客生成 ──────────────────────────────────────→ ⑤ 喜马拉雅上传+定时
```

**关键依赖**：③ 公众号草稿依赖 ①② 的图片产物；⑤ 喜马拉雅依赖 ④ 的播客音频。①② 可并行，④ 可后台跑（TTS 耗时长），③ 等 ①② 完成后做。

## 各步详解

### 步骤 ① 封面 + ② 插图

- **skill**：`article-cover-image-generator`（批量并行模式）
- **产物**：`<文章目录>/公众号_封面.png`（900×383）+ `<文章目录>/imgs/*.png`（1920×1080）
- **插图嵌入**：生成后在文章 markdown 里用 `![alt](imgs/xxx.png)` 插入对应位置
- **注意**：封面文件名必须是 `公众号_封面.png`（草稿脚本按此名找）；多图必须批量并行，Gaoding 串行每张新 tab

### 步骤 ③ 公众号草稿（API）

- **skill**：`browser-publisher`（脚本 `wechat-mp-draft.py`）
- **产物**：草稿 media_id（公众号草稿箱可见）
- **关键参数**：
  - 文章文件名非 `公众号_文章.md` 时，用 `--md <路径>` 指定（不要手动 cp）
  - 封面、插图自动上传；摘要读 `公众号_摘要.txt`
- **环境变量**：`WECHAT_MP_APPID` / `WECHAT_MP_APPSECRET`
- **详见**：`browser-publisher/references/wechat-mp.md`

### 步骤 ③b 文章里的音频怎么处理

文章若含音频（如 AI 生成音乐演示），公众号里嵌入有两种方式：

- **方式 A（推荐）：正文放外链**。音频先发到喜马拉雅（步骤 ⑤），拿到链接，在文章 markdown 里用 `[🎧 点击试听](https://www.ximalaya.com/sound/xxx)` 替代音频占位
- **方式 B：上传为 voice 素材**。用 `wechat-mp-upload-voice.py --file <mp3>` 上传（限 ≤30MB、≤30min），拿到 media_id 后引导用户在草稿编辑器手动插入（**音频组件无法自动化**，详见 wechat-mp.md「已知限制」）

### 步骤 ④ 播客生成

- **skill**：`article-to-solo-podcast`
- **产物**：`<文章目录>/_podcast/播客_TTS.mp3`（8-12 分钟，320k, loudnorm）
- **耗时**：TTS 合成是最慢的一步（~2 分钟），建议后台并行跑
- **集号**：从 `audio-to-social/config.json` 的 `platforms.boker_next_episode` 读

### 步骤 ⑤ 喜马拉雅上传 + 定时

- **skill**：`browser-publisher`（浏览器自动化，需 Chrome 已登录喜马拉雅创作者后台）
- **产物**：喜马拉雅声音 ID（如 `https://www.ximalaya.com/sound/xxx`）
- **必填项**：专辑、标题（含集号前缀）、AI 合成标记（TTS 必选"是"）、简介、标签
- **定时**：开"定时发布"switch → 日历选日期 + 小时 + 分钟（最早 now+2h）。UI 点选稳定，详见 ximalaya.md「定时发布模式」
- **发布后**：跑 `bump_episode.py` 递增集号（**脚本在 `audio-to-social/scripts/`，不在 browser-publisher**）
- **详见**：`browser-publisher/references/ximalaya.md`

## 需要用户介入的点

| 介入点 | 何时 | 原因 |
|---|---|---|
| 公众号扫码登录 | 步骤 ③ 之后若要在编辑器操作（如手动插音频）| 公众号后台 session 会过期，浏览器操作需登录态 |
| 喜马拉雅登录态确认 | 步骤 ⑤ 开始前 | browser-publisher 靠已登录 session，需用户确认 Chrome 登录着创作者后台 |
| 公众号发表扫码 | 步骤 ③ 最终发表时 | 微信验证，需管理员扫码 |

## 已知限制汇总

| 限制 | 影响 | 应对 |
|---|---|---|
| 公众号音频组件无法自动化 | 不能用 MCP 在草稿编辑器插原生音频 | 用正文外链（喜马拉雅）或引导用户手动插，详见 wechat-mp.md |
| voice 素材 ≤30MB/30min | 长播客不能上传为公众号音频 | 改用喜马拉雅外链 |
| Gaoding 多图必须串行每张新 tab | 多图生成不能同 tab 复用 | 批量并行接口内部处理，调用方传图片列表即可 |
| 喜马拉雅 iframe 嵌套 | snapshot 的 uid 跨 iframe 不连续 | 注意 uid 前缀区分（如 `12_*` 是 iframe 内）|

## 不要做的

- **不要**手动 `cp` 文章到 `公众号_文章.md`——用 `wechat-mp-draft.py --md` 指定
- **不要**尝试用 MCP 点击公众号编辑器的"Audio"按钮——跨域 iframe + React 会失败
- **不要**忘了发布后 bump 集号——下次集号会重复
