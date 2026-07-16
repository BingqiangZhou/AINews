# Audio to Social V5 - Orchestrator Agent Contracts

> 本 skill 是**纯编排器**。内容生产全部委派下游 skill，自身只剩一个子 agent（audio-engineer，Phase 1 转录编排）。
>
> 平台标识符约定：`gongzhonghao` = 微信公众号，`boker` = 喜马拉雅播客（内部名）。config.json 中集号字段为 `platforms.boker_next_episode`。

> 所有代理先读 `agents/_shared.md`，再读各自的合同。共享约定（返回格式、反虚构、AI 腔 blocklist、错误码等）在那里定义。

## 调用方式

阅读 `skills/audio-to-social/agents/{agent-name}.md`，严格按其中定义的输入、输出和校验规则执行。

## 代理一览

| Agent | 文件 | 主要输入 | 主要输出 | 备注 |
|-------|------|---------|---------|------|
| audio-engineer | agents/audio-engineer.md | audio_file_path, source_assets, config, cache_key | temp/转录文本.txt, 原始录音.m4a, cache files | Whisper 转录 + 非音频资产归一化（Phase 1，唯一内联子 agent） |

> 旧的内容生产子 agent（transcript-optimizer / boker-optimizer / quality-gate / cover-prompt-agent / illustration-prompt-agent / image-batch-generator）已迁出至下游 skill 或归档至 `_backup/skills/audio-to-social-4.4.0/agents/`。

## 数据流（纯编排）

```
input_audio / URL / YouTube / Markdown
         |          |        |
         |      baoyu-url-to-markdown / baoyu-youtube-transcript
         |          |        |
         +-----> temp/source_assets + audio-engineer → temp/转录文本.txt
                                     |
                  [Phase 2] 委派 article-studio（transcript 模式）
                  → 公众号_文章.md + 公众号_摘要.txt + <article_dir>
                                     |
            ┌────────────┬───────────┴───┐  （并行）
            ▼            ▼               ▼
   [3a] cover-generator  [3b] illustrator  [4] article-to-solo-podcast
   → 公众号_封面.png      → imgs/*.png       → _podcast/{脚本,标题描述,TTS.mp3}
   (全量模式)             (全量模式,回写         │
                          ![]()到文章)          │
            └────────────┴───────────┬───────┘
                                   ▼
                      [Phase 5] 委派 article-to-video（5 CLI）
                      → _video/公众号_视频.mp4
                                   │
                      [Phase 6] reconcile ‖ compress（内联）
                                   │
                      [Phase 7] browser-publisher + bump_episode（用户触发）
```

> 上图与 [SKILL.md](SKILL.md) 流程概览对应。委派契约详见 [delegation-contracts](references/delegation-contracts.md)。

## 单一协议

所有流程基于 `articles/{YYYY-MM-DD}_{标题}/` 目录结构（项目根由 Phase 2 的 article-studio 建立）。编排器 `state.json` 在项目根，schema `audio-to-social-v4`。

## 输入源和素材

输入归一化（音频/URL/YouTube/Markdown → `temp/source_assets/`）详见 `references/phase0-initialization.md`。
转录产出的 `temp/转录文本.txt` 是 Phase 2 文章的唯一事实源。

## 缓存协议

`cache_key` 由输入源路径/大小/修改时间/hash 生成（`scripts/cache_key.py`）；缓存完整且未 `--refresh` 时 audio-engineer 复用并置 `stages.transcribe.reuse_cache = true`。

## 内容风格和视觉预设

`content_style` / `visual_preset` 取值与 auto 选择详见 `references/visual-presets.md`。传给 article-cover-image-generator / article-illustrator。

## 发布前后验证

详见 `references/phase8-publishing.md`。
