# 归档目录约定

> 本 skill 产物目录结构（通用公众号文章系列，按 `article_type` 路由）。

## 目录结构

```
articles/{YYYY-MM-DD}_{标题}/
├── 公众号_文章.md              # 终稿源（通过主编审查）
├── 公众号_摘要.txt             # 一句话摘要（≤ digest_max_chars 字）
├── _research/
│   └── 事实素材与来源.md        # Phase 0 联网检索的事实底座（每条带信源 URL）
├── prompts/                    # 审查标准、写作 prompt 备份
├── imgs/                       # 预留给 article-illustrator（本 skill 不填）
│   └── prompts/                # 同上
├── scorecards/
│   ├── round-1.json            # 主编第 1 轮审查
│   └── round-N.json            # 后续修正轮次
├── temp/                       # 中间产物（validate 报告等，可清理）
└── state.json                  # 状态机断点续跑
```

## 文件命名契约（顶层产物）

对齐 `browser-publisher` 的公众号草稿脚本契约（脚本读这些固定文件名）：

| 文件 | 用途 | 必需 |
|------|------|------|
| `公众号_文章.md` | 正文（首行 `# 标题`） | ✓ |
| `公众号_摘要.txt` | 一句话摘要（草稿 digest） | ✓ |
| `公众号_封面.png` | 封面（**本 skill 不生成**，留给 article-cover-image-generator） | 可选 |
| `imgs/*.png` | 插图（**本 skill 不生成**，留给 article-illustrator） | 可选 |

## state.json schema

```json
{
  "schema_version": "article-studio-v1",
  "phase": "initialized | researched | gap_blocked | written | editor_passed",
  "source_mode": "stance_research | transcript",
  "topic": "...",
  "article_type": "opinion | howto | story | news | profile | review",
  "stance": "...",
  "source_file": "（transcript 模式）转录文本路径",
  "output_dir": "articles/{YYYY-MM-DD}_{标题}",
  "title": "...",
  "research_file": "articles/{YYYY-MM-DD}_{标题}/_research/事实素材与来源.md",
  "article_file": "articles/{YYYY-MM-DD}_{标题}/公众号_文章.md",
  "current_round": 0,
  "fix_rounds_used": 0,
  "scorecards": ["scorecards/round-1.json", ...],
  "created_at": "2026-07-05T...",
  "updated_at": "2026-07-05T..."
}
```

> `source_mode` 默认 `stance_research`；transcript 模式下 `stance` 可空、`source_file` 必填，`researched` 阶段在 researcher 落盘转录派生 `_research` 后即置（无联网）。详见 [transcript-mode.md](transcript-mode.md)。

## 标题 → 目录名转换

`topic` 转目录 slug：取标题中的核心实体，去标点，kebab-case。例：
- 标题"阿里禁了 Claude Code，我也早不在用了——迁移到 ZCode 3.0 的真实记录"
- 目录名 `articles/{YYYY-MM-DD}_告别claude-code-我的coding-agent迁移记/`（按 `articles/` 现有约定带日期前缀，创建日期；用户也可自定义）

主 agent 在 Phase 0 初始化时通过 `AskUserQuestion` 确认目录名。

## 后续步骤（Phase 4 完成后，主 agent 告知用户）

本 skill 到 `公众号_文章.md` 通过审查为止。后续手动调：

| 步骤 | skill | 输入 |
|------|-------|------|
| 配图 | `article-illustrator` | `公众号_文章.md` |
| 封面 | `article-cover-image-generator` | content_context（标题+核心论点） |
| 公众号草稿上传 | `browser-publisher` | `--project-dir articles/{YYYY-MM-DD}_{标题}` |
| 播客脚本+音频 | `article-to-duo-podcast` | `--input 公众号_文章.md` |
