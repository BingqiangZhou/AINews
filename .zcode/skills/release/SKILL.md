---
name: release
version: "1.0"
description: 项目发布工具。分析 git 历史、检测 Skill 变更、通过 git-cliff 生成 CHANGELOG.md、同步 plugin.json 版本号、创建 git tag 并推送。推送后 GitHub Action 自动创建 Release。基于语义化版本号（如 v1.0.0，详见 Step 1 规则）。**触发场景**：用户提到"发布""release""发版""打 tag""生成 changelog""更新版本""发布新版本""创建 release"，或需要将当前项目状态发布为新版本时使用。
---

# Release — 项目发布

一键发布流程：分析变更 → 生成 CHANGELOG → 同步 plugin.json 版本号 → 创建 tag → 推送 → GitHub Action 自动创建 Release。

## 前置工具

| 工具 | 用途 | 安装 |
|------|------|------|
| `git-cliff` | 生成 CHANGELOG | `winget install git-cliff` |

GitHub Release 由 `.github/workflows/release.yml` 自动创建，无需本地安装 `gh` CLI。

## 工作流

按顺序执行以下步骤。**Step 1 和 Step 2 完成后展示摘要，等待用户确认再继续。**

### Step 0: 前置检查

逐项验证，失败则中止并提示用户处理：

1. **git-cliff**: 运行 `git cliff --version`，未安装则提示 `winget install git-cliff`，中止
2. **工作树干净**: 运行 `git status --porcelain`，有输出则提示用户先 commit 或 stash，中止

### Step 1: 确定版本号

采用语义化版本 `v<MAJOR>.<MINOR>.<PATCH>`（如 `v1.0.1`）。

1. **获取上一个版本号**：从最新 tag 读取
   ```bash
   git tag --sort=-v:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -1
   ```
2. **按变更规模递增**（参考本次待发布内容的 Step 2 分析）：
   - **PATCH（vX.Y.Z → vX.Y.Z+1）**：仅修 bug、文档、chore、配置同步等维护性变更
   - **MINOR（vX.Y.* → vX.Y+1.0）**：新增 skill、新增功能脚本、能力扩展
   - **MAJOR（vX.*.* → vX+1.0.0）**：架构级重构、不兼容的工作流变更（本项目极少触发）
3. 检查 tag 是否已存在：
   ```bash
   git tag -l "v<新版本号>"
   ```
   若已存在（极少见），在 PATCH 末位继续 +1 直到不冲突
4. 展示版本号及递增依据（说明为何是 PATCH/MINOR/MAJOR）

> **首次发版**：如果仓库当前没有任何 tag（`git tag -l` 为空），首版本号对齐 `.claude-plugin/plugin.json` 现有 `version` 字段——即首个 release 用 `v<plugin.json 里的 version>`（例如 plugin.json 是 `1.0.0`，首版本号即 `v1.0.0`）。

### Step 2: 预览变更

1. **找到上一个 tag**：
   ```bash
   git tag --sort=-creatordate | head -1
   ```
   如果没有任何 tag，使用初始 commit：
   ```bash
   git rev-list --max-parents=0 HEAD
   ```

2. **生成 changelog 预览**（输出到终端，不写入文件）：
   ```bash
   git cliff --tag <VERSION> --unreleased
   ```

3. **统计 commits 数量**：
   ```bash
   git rev-list <PREV_TAG>..HEAD --count
   ```

4. **分析 Skill 变更**（AINews 的正式 skill 在 `skills/`，发布工具自身在 `.zcode/skills/release/`，两者都纳入分析）：
   - 列出 prev tag 时的 skills：
     ```bash
     git ls-tree -d --name-only <PREV_TAG> skills/ 2>/dev/null || echo "no-skills"
     ```
   - 列出当前的 skills：
     ```bash
     ls skills/
     ```
   - 新增的 skills（在当前存在但 prev tag 不存在）：读取其 `skills/<name>/SKILL.md` frontmatter 的 `name` 和 `description`
   - 删除的 skills（在 prev tag 存在但当前不存在）：确认已迁出/合并
   - 更新的 skills（两边都存在的）：检查变更
     ```bash
     git diff <PREV_TAG>..HEAD --stat -- 'skills/<name>/'
     ```

5. **展示发布摘要**，格式如下：
   ```
   📦 Release <VERSION> Summary
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Previous: <PREV_TAG 或 "(首次发版，基准为初始 commit)">
   Commits:  <N>

   Skills:
     🆕 <name> — <description>
     🔄 <name> — <changed files summary>
     🗑️ <name> → removed/merged

   Output:
     [x] CHANGELOG.md
     [x] .claude-plugin/plugin.json version → <VERSION>
     [x] Git tag <VERSION>
     [x] Push to origin → GitHub Action auto-creates Release

   确认发布？(y/n)
   ```

6. **等待用户确认**。用户可以：
   - 确认继续
   - 修改版本号
   - 取消

### Step 3: 生成 CHANGELOG.md

1. 检查 CHANGELOG.md 是否已存在：
   ```bash
   test -f CHANGELOG.md && echo "exists" || echo "not-exists"
   ```

2. 如果**不存在**（首次），全量生成：
   ```bash
   git cliff --tag <VERSION> -o CHANGELOG.md
   ```

3. 如果**已存在**，前置插入新版本：
   ```bash
   git cliff --tag <VERSION> --prepend CHANGELOG.md
   ```

4. **生成 AI 摘要**：git-cliff 模板中 `<!-- AI_SUMMARY -->` 是占位符，需要用 AI 生成的摘要替换。

   基于以下信息生成一段 2-3 句的自然语言摘要：
   - commits 总数和分组统计（从 Step 2 的 git-cliff 预览中提取）
   - Skill 变更（新增/更新/删除，从 Step 2 分析结果中提取）
   - 主要技术变更（如工作流精简、管线 bug 修复、新 agent 等）

   摘要格式：
   ```markdown
   > <自然语言总结，2-3 句，概括本次发布最核心的变化>
   >
   > 共 <N> commits，其中 🚀 Features <N> | 🐛 Fixes <N> | 📝 Docs <N> | ...
   >
   > **[Full diff](https://github.com/BingqiangZhou/AINews/compare/<PREV_TAG>...<VERSION>)**
   ```

   将生成的摘要文本替换 CHANGELOG.md 中对应版本段的 `<!-- AI_SUMMARY -->` 占位符。

### Step 3.5: 同步 plugin.json 版本号

把 `.claude-plugin/plugin.json` 里的 `version` 字段改成新版本（**去掉 `v` 前缀**）。

例如新 tag 是 `v1.0.1`，则把：
```json
"version": "1.0.0",
```
改为：
```json
"version": "1.0.1",
```

用 Edit 工具精确替换该行。`marketplace.json` 没有 `version` 字段，**不要动它**。

### Step 3.6: 提交变更

```bash
git add CHANGELOG.md .claude-plugin/plugin.json
git commit -m "docs: update CHANGELOG and bump version to <VERSION>"
```

### Step 4: 创建 Tag 并推送

```bash
git tag -a <VERSION> -m "Release <VERSION>"
git push origin HEAD --tags
```

如果 push 失败，tag 和 CHANGELOG 已在本地，提示用户稍后手动推送：
```
⚠️ Push failed. 本地 tag 和 CHANGELOG 已就绪，稍后手动推送：
  git push origin HEAD --tags
```

### 完成

输出最终状态：
```
✅ Release <VERSION> 发布完成
   CHANGELOG.md: 已更新
   plugin.json: version → <VERSION 去掉 v>
   Git tag: <VERSION>
   GitHub Release: 等待 GitHub Action 自动创建
   查看: https://github.com/BingqiangZhou/AINews/actions
```

## 错误处理

| 场景 | 处理 |
|------|------|
| git-cliff 未安装 | 中止，提示安装命令 |
| 工作树有未提交变更 | 中止，提示 commit 或 stash |
| tag 已存在 | 自动追加序号（PATCH 末位继续 +1）直到不冲突 |
| push 失败 | 提示手动推送 `git push origin HEAD --tags` |
| 没有上一个 tag | 使用初始 commit 作为基准，全量生成 |
| 0 commits since last tag | 中止："No new commits since <PREV_TAG>. Nothing to release." |
