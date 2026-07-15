# 内容主编评分细则 — 5 维度 × 1-10 分（按 `article_type` 差异化）

> **内容主编**（`agents/content-editor.md`）评分真源。每维打分必须有 evidence（引用具体段落/句子）。

> **本文件是双主编之一——内容主编——的评分细则**。读者代表（`agents/reader.md`）的 3 维度（reading_experience/takeaway/engagement）评分细则直接写在 reader.md 内，不在本文件。

> **5 维度框架跨所有类型通用**。各维度的**具体评判锚点按 `article_type` 从 [type-profiles.md](type-profiles.md) 的 `rubric_focus` 字段加载**。本文件给出每维的通用评分锚点 + 类型差异化说明。

## 5 维度（通用框架）

| 维度 | 评什么 | 通用关键问题 |
|------|--------|---------|
| `structure` | 结构（按类型骨架） | 是否符合 `article_type` 对应 profile.structure？开头/中段/结尾各模块是否齐备？ |
| `accuracy` | 事实准确（对照 _research） | 编造？夸大？事实/观点混淆？引文是否照搬？ |
| `voice` | 声音（强度按 profile.voice） | 是否符合本类型的声音调性？信息密度够？有记忆点（按类型）？ |
| `format` | 公众号技术规范 | 标题字数/小节数/无 `>`/无渲染死角/AI 腔 |
| `honesty` | 可信度/分寸（承载红线） | 是否违反本类型启用的红线子集？立场类文章是否诚实？ |

> 每维的**类型差异化锚点**：见 [type-profiles.md](type-profiles.md) 各 profile 的 `rubric_focus` 字段。例：
> - structure 评 opinion：钩子 3 段亮观点 + 分论点递进 + 结尾回扣
> - structure 评 howto：SCQA 戳痛点 + 步骤可复现 + 核对清单齐全
> - structure 评 story：起承转合齐全 + 转折点 sharp + 升华不生硬
> - structure 评 review：痛点共鸣 + 卖点有证据 + **独立对比段（横向/前后对比，缺失=≤6 hard_block）** + 适合谁/不适合谁

## 评分等级（每维通用）

| 分数 | 含义 |
|------|------|
| **9-10** | 卓越。该维度无可挑剔，可作为范例 |
| **8** | 良好。符合标准，有微小改进空间 |
| **7** | 及格。达到本 skill 最低门槛（`pass_bar.min_per_dimension`） |
| **5-6** | 不足。有明显问题，需修订 |
| **3-4** | 严重不足。触及 hard_block（红线/事实编造）通常落此区间 |
| **1-2** | 灾难性。该维度完全失败 |

## 各维度详细评分标准

### structure（按类型骨架评）

通用锚点：
- **10**：完全符合本类型 profile.structure，各模块齐备且**递进/转折 sharp**（不平面）
- **8**：结构清晰符合类型，但某模块略弱（如开头钩子不够抓、结尾回扣略生硬）
- **7**：结构齐备但平庸
- **5-6**：缺其中一项关键模块（如 howto 无核对清单、story 无转折点、review 无对比段）
- **3-4**：结构混乱，不符合本类型骨架
- **evidence 必引**：开头第 1-3 段 + 各 `##` 小标题 + 结尾段，对照 profile.structure 逐项核

### accuracy（事实准确，对照 _research）

- **10**：每个数字/事件/版本/引文都能在 `_research` 找到对应，引文一字不改
- **8**：事实准确，偶有"据称"未标但无伤大雅
- **7**：基本准确，1-2 处模糊措辞缺失
- **5-6**：有夸大（"据报道"说成"官方承认"）或事实/观点边界模糊
- **3-4**：**FIDELITY_VIOLATION**——检出 `_research` 外事实且无法佐证 → hard_block
- **1-2**：大量编造
- **evidence 必引**：抽 3-5 个具体事实，逐个对照 `_research` 的 bullet + URL
- **类型加强**：news/profile/review 对引文保真与时效标注要求更高，缺日期/版本号即扣分

### voice（按 profile.voice 调强度）

- **10**：完全符合本类型声音调性 + 信息密度高 + 有记忆点（opinion/review 的金句、story 的画面、profile 的人物细节、howto 的避坑提示等）
- **8**：声音到位，但缺记忆点或偶有跑调
- **7**：声音基本符合，强度略弱
- **5-6**：声音错位（如 news 写得感情泛滥、opinion 写成纯客观转述、story 抽象抒情无细节）
- **3-4**：毫无声音特征，像 AI 通稿
- **evidence 必引**：体现本类型声音特征的句子 + 记忆点候选
- **类型差异**：opinion/review 要求第一人称强在场；news 要求客观简洁；story 要求代入感细节；profile 要求人物立体；howto 要求教练式。

### format（公众号技术规范）

- **10**：标题字数达标且符合本类型套路 + 小节数达标 + 无 `>` 引用块 + 无 AI 腔 + 无渲染死角
- **8**：规范达标，标题略平或某处可优化
- **7**：机器预检全过，但有小瑕疵（如标题不够抓）
- **5-6**：机器预检有 warning（插图占位等）
- **3-4**：机器预检 error（字数/小节/AI 腔） → 实际不会到 2b，此分留作记录
- **evidence 必引**：标题字数 + 小节数 + `grep '^>'` 结果 + AI 腔检测

### honesty（可信度/分寸 — 承载红线检查）

通用锚点（按本类型启用的红线子集评，子集见 [type-profiles.md](type-profiles.md) 各 profile 的 `redlines`）：
- **10**：符合本类型红线要求——立场类文章（opinion/review）立场鲜明但分寸到位（承认对方优点、限定词精准、不一边倒）；非立场类文章（howto/news/profile/story）事实/观点边界清晰、时效标注完整、AI 声明到位
- **8**：基本符合，偶有略重的话但未越线
- **7**：基本到位，1-2 处可改得更稳
- **5-6**：有轻微问题（如立场类文章略一边倒，或非立场类文章事实/观点边界模糊），但不构成红线违反
- **3-4**：**REDLINE_VIOLATION**——本类型启用的红线任一违反 → hard_block
- **1-2**：严重违反（人身攻击/造谣/明显拉踩/未声明 AI 而冒充真实经历等）
- **evidence 必引**：对争议对象的评价句 + 是否有承认对方优点的句子（仅立场类）+ 限定词使用情况 + AI 声明 + 时效标注
- **类型差异**：opinion/review 全量红线，honesty 维度最重；howto/news/profile/story 只查通用红线（1/2/6），honesty 主要评事实/观点边界与 AI 声明。

## 一票否决（hard_block）

以下情况无论总分多高都 hard_block（verdict = revise）：

| 触发条件 | 错误码 | 涉及维度 |
|---------|--------|---------|
| `_research` 外事实且无法佐证 | FIDELITY_VIOLATION | accuracy ≤3 |
| **本类型启用的红线子集**任一违反（见 profile.redlines） | REDLINE_VIOLATION | honesty ≤3 |
| 任一维度 < `pass_bar.min_per_dimension`（默认 7） | SCORE_BELOW_BAR | 对应维度 |

## overall 计算

`overall = (structure + accuracy + voice + format + honesty) / 5`（简单平均，保留 1 位小数）

overall 用于报告展示，**不作为 pass 判据**（pass 判据是"全维度≥门槛 + 无 hard_block"）。

## 评分纪律

- **证据优先**：每个分数必须有 evidence 引用，不许抽象打分（"感觉不错"不算 evidence）。
- **不放水**：熟人/朋友的文章也一样审。文章代表真人品牌，放水损害可信度。
- **不替作者写正文**：fix_directives 给方向，不写成品段落。
- **不因风格偏好打回**：**只看是否符合当前 `article_type` 的标准**，不审个人品味（不拿 opinion 的"立场鲜明"去要求 news 的"客观简洁"）。
- **不引入 `_research` 之外的外部知识**：只对照 `RESEARCH_FILE` 核查，不自己 fact-check 外部世界。
- **类型标准一致性**：同一篇文章从头到尾按同一个 `article_type` 评，不中途换标准。
