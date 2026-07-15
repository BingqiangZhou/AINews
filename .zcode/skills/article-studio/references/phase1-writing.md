# Phase 1 — 通用写作工艺

> writer agent（DRAFT/FIX）必读。本文件是**跨所有文章类型的通用工艺**：声音原则、事实保真、反 AI 腔、格式规范。

> **结构骨架、声音强度、CTA 强弱、标题套路、红线子集均按 `article_type` 从 [type-profiles.md](type-profiles.md) 加载对应 profile**。本文件提供的是叠加在 profile 之上的通用约束。

## 通用写作原则（所有类型共享）

### 段落与排版（手机阅读优先）

- **短句多段落**：公众号是手机阅读，段落宜短，单段 ≤ `max_para_chars`（默认 120 字）。
- **小标题分隔模块**：除 story 类型可降级外，正文应有 `##` 二级标题切分模块。
- **不一块砖糊脸**：长论证/长步骤拆成多个短段。
- **金句节奏**：每 200-300 字尽量有一个"启发点"或可记忆的金句，维持注意力。

### 声音（强度按 profile.voice 调）

通用底线：
- 口语化但有信息密度——像跟读者说话，但**每句都有信息增量**，不灌水。
- 有作者/叙述者的"在场感"（具体强度按 profile：opinion/review 强，news/profile 弱）。
- 不打官腔、不堆书面语（见反 AI 腔）。

各类型的调性差异已在 [type-profiles.md](type-profiles.md) 的 `voice` 字段写清，按类型执行。

### 标题（套路按 profile.title_formula 选）

通用底线：
- 字数 `title_min_chars`-`title_max_chars`（默认 15-30）。
- 有点击欲但不标题党——关键词前置，让读者 1 秒抓到主题。
- 各类型偏好的标题公式（数字型 / 痛点型 / 悬念型 / 反问型）见 profile 的 `title_formula`。

## 事实保真（反虚构硬约束，违反 hard_block）

- 文中每个具体数字/事件/版本号/日期/引文都必须能在 `_research/事实素材与来源.md` 找到对应 bullet。
- **不编造**：超出 `_research` 的细节必须用"据……""有报道称"或删去。
- **不夸大**：不把"有报道说"说成"官方承认"；不把"据称"说成确定事实。
- **区分事实与观点**：客观事实（事件、数字）与作者主观判断有清晰边界。说"我认为"就别包装成"事实上"。
- **引文照搬**：受访者原话、官方公告、参数表等一字不改，用引号包裹，不为顺口而改写失真。
  - **转述降级**：若 `_research` 某条只有转述，文章里不得用引号当原话，改用"据……所述"转述形式。
- **news 事件日期保真**：news 文章里每个事件的日期必须来自 `_research`（事件发生/源文发布日期），不可用检索日期冒充，更不可编造。详见 [type-profiles.md](type-profiles.md) news profile 的 research_focus。

### story 虚构豁免（仅 `article_type == "story"`）

纯虚构 story（`_research` 的 `## 写作立场/素材` 区标注"纯虚构/AI 生成"）的**情节、对话、人物动作、场景细节**不受"必须来自 _research"约束。但红线 1（不冒充真实经历）、红线 6（AI 声明）仍生效；引用的真实背景元素（事件/人物/地名/时间）仍须来自 `_research`。详见 [article-writer.md](../agents/article-writer.md) §4a。

## 红线自查（hard_block 源，按类型启用子集）

写完后**只对照当前 `article_type` 启用的红线子集**自查（子集见 [type-profiles.md](type-profiles.md) 各 profile 的 `redlines` 字段，红线全文见 [redlines.md](redlines.md)）：

- 通用红线（所有类型启用）：
  1. 区分事实与观点
  2. 限定词使用（"据报道/被扒出来"）
  6. AI 生成声明 + 时效标注
- 立场类红线（仅 opinion/review 全启用，其他类型按需）：
  3. 不一边倒（承认对方优点/自己工具不完善）
  4. 不阴谋论/不上纲上线
  5. 对同行工具公平

> 例：写 howto 教程时不必自查"不一边倒"（教程不涉立场）；写 opinion 时评必须全 6 条查。

违反启用的红线 → 就地改写，不要把问题留给主编。

## 反 AI 腔（machine check 会拦）

禁用短语来自 `audio-to-social/references/brand-config.md` 的 `## 禁用 AI 腔短语` 段。典型：

- `首先 / 其次 / 再次 / 综上所述 / 总而言之`
- `值得一提的是 / 不可否认 / 毋庸置疑 / 不难发现 / 众所周知`
- `在当今...的背景下 / 随着...的发展`

写作时如果发现自己在打这种官腔，**重写成口语**。

## 格式规范（不符 machine check 报 error）

- **首行**：`# 标题`（H1，标题 `title_min_chars`-`title_max_chars` 字，或 profile 的 `content_overrides`）
- **正文**：`body_min_chars`-`body_max_chars` 字（或 profile 覆盖）
- **小节**：`min_sections`-`max_sections` 个 `##`（story 类型可降级，见 profile）
- **摘要**：同步写 `公众号_摘要.txt`，一句话，≤ `digest_max_chars` 字
- 文末 AI 生成声明用 `>` 引用块样式（如 `> 本文由作者手写初稿，AI 辅助改写。`，详见 [redlines.md](redlines.md) 红线 6）
- 不依赖公众号不渲染的语法（嵌套引用、复杂 HTML 等）

## DRAFT 与 FIX 的区别

- **DRAFT**：从零写，按 profile.structure 骨架 + 以上全部通用约束。
- **FIX**：按**双主编合并后的** `fix_directives`（target+problem+fix 三元组，内容主编的红线/事实指令优先 + 读者代表的阅读体验指令）定向改。只改有问题的部分，保留两位主编认可的段落，不重构整体。红线/事实问题优先改干净。改完仍按**当前类型**的红线子集自查一遍。
