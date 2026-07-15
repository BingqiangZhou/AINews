# Reference Images（参考图深度处理框架）

当 `references` 参数非空（调用方传入了参考图片路径列表）时，本 skill 必须按本框架对参考图做**深度分析**，并把可复现的视觉指令**注入 prompt 正文**。

> **核心论断**：只把参考图路径透传给后端（`--ref`）**远远不够**——图像模型常忽略参考图，或在风格迁移时丢失关键细节。必须把参考元素转译成 prompt 文本里 `MUST`/`REQUIRED` 前缀的可复现指令，才能可靠复现。

本框架适配本 skill 的"委托 image-generator"架构：本 skill 做分析与转译，生成带参考指令的 prompt 文件，再由 image-generator 透传给后端。

---

## 1. 输入检测与保存

### 1.1 校验存在性
对 `references` 列表中的每个路径，调用前必须 `test -f <path>` 验证文件存在。任一缺失则报告失败，不静默跳过。

### 1.2 保存到 refs/
将参考图复制到 `{output_dir}/refs/ref-NN-{slug}.{ext}`：
- `NN`：两位序号（01, 02, ...），按 references 顺序
- `{slug}`：从参考图主题派生的英文短 slug（如 `brand-logo`、`hero-portrait`）
- `{ext}`：保留原扩展名（png/jpg/jpeg/webp）

例：`references: ["D:/assets/brand.png"]` → `refs/ref-01-brand-logo.png`

### 1.3 写入 frontmatter
在 prompt 文件的 YAML frontmatter 写入 `references` 列表：
```yaml
references:
  - ref_id: "01"
    filename: refs/ref-01-brand-logo.png
    usage: direct   # direct | style | palette，见 §3
```

---

## 2. 深度分析维度表（核心）

对每张参考图，按以下 6 个维度提取**具体、可复现**的元素。每项给出 Good vs Bad 对照——Bad 描述无法复现，Good 描述能让另一个 agent/模型重现同一效果。

| 维度 | ❌ Bad（模糊） | ✅ Good（可复现） |
|------|---------------|------------------|
| **品牌元素** | "有个 logo" | "Logo 是字母 m，由 3 条粗竖线组成，主色 #2563EB，置于左上角占画面 8%" |
| **标志性图案** | "有装饰图案" | "右上角有一个由 6 个等大圆点组成的三角形阵列，间距均匀，填充琥珀色 #F59E0B" |
| **精确色值** | "蓝色调" | "Primary 深海军蓝 #1E3A5F（占 ~55%），Accent 电光蓝 #3B82F6（占 ~15%），Background 近黑 #0A0A0A（占 ~30%）" |
| **布局比例** | "上下结构" | "分割布局：顶部主图区占 ~65%，底部深色 banner 占 ~35%，banner 高度内文字垂直居中" |
| **字体处理** | "现代字体" | "标题用几何无衬线体，字重 Bold，字号约占画面高度的 1/6，字距收紧，左对齐" |
| **渲染特征** | "插画风格" | "扁平矢量，纯色填充无渐变，线条粗细均匀（~3px 视觉等效），边缘锐利无抗锯齿模糊" |

### 2.1 人像参考（特殊处理）
若参考图含人物：
- 提取**外观特征**（年龄/性别/发型/肤色/体型）
- 提取**姿势与表情**（坐姿/站姿/手势/朝向/情绪）
- 提取**服装**（颜色/款式/材质）
- **风格化转换规则**：参考图是写实照片时，生成图应转为与目标 rendering 一致的风格化人像（如 flat-vector → 几何化剪影、hand-drawn → 简笔线条人）。**绝不上传/复刻真实人脸**，做"风格相似替代"。

---

## 3. usage 三分类

每张参考图标注 `usage`，决定它在 prompt 中的处理方式：

| usage | 含义 | prompt 处理 | 后端处理 |
|-------|------|------------|---------|
| **direct** | 参考图本身（或其关键元素）要出现在生成图中 | MUST 复现元素逐条写入正文 | image-generator 透传 `--ref` 给后端 |
| **style** | 只取风格/渲染特征，不要具体内容 | 提取渲染/纹理/笔触特征写入 Style words 槽位 | 可不传 `--ref`（仅文本指导） |
| **palette** | 只取色板 | 提取 hex 写入 frontmatter，色名写入正文 | 可不传 `--ref` |

> **冲突优先级**：参考图 > 默认维度值。若参考图的 palette 与传入的 `palette` 维度冲突，以参考图为准（在 prompt 中注明"参考图覆盖 palette 维度"）。

---

## 4. MUST/REQUIRED 转译规则（注入 prompt 正文）

参考元素**不能只放在 frontmatter**，必须用 `MUST`/`REQUIRED` 前缀在 prompt 正文中逐条描述，并给出**整合方案**（确切的空间排布）。

### 4.1 注入模板
在 prompt 正文末尾追加专门的参考段落（标题用 `# Reference Style — MUST INCORPORATE` 或中文 `# 参考元素 — 必须复现`）：

```
# 参考元素 — 必须复现
基于参考图 refs/ref-01-brand-logo.png (usage: direct)：
- MUST 复现：字母 m logo，由 3 条粗竖线组成，主色为深工程蓝，置于左上角约占画面 8%。
- MUST 复现：右上角 6 圆点三角形阵列，琥珀色填充，间距均匀。
- 整合方案：分割布局——顶部主图区 ~65% 放置核心视觉，底部深色 banner ~35% 内含 logo（左）与圆点阵列（右），文字垂直居中。
```

### 4.2 转译要点
- **每个元素单独成行**，用 `MUST`/`REQUIRED` 前缀
- **描述要具体到能复现**（精确 hex、构造方法、布局比例、占比百分数）
- **给出整合方案**：不能只列元素，要说明它们在画面中如何排布
- **区分硬约束与软参考**：必须复现的用 MUST，风格倾向的用 SHOULD/INSPIRED BY

---

## 5. 后端差异提示

本 skill 委托 image-generator 出图，后端能力差异影响参考图策略：

| 后端 | 参考图能力 | 中文图内文字 | 推荐场景 |
|------|-----------|------------|---------|
| **Gaoding（万相2.7）** | 较弱（稿定 Web 平台参考图支持有限） | ✅ 印刷级 | 含中文标题/标签的封面，参考图以 style/palette 为主 |
| **Agnes** | 较强（API 支持 `--ref`） | ⚠️ 不稳定 | 强参考复现场景（direct usage），无中文或中文极少 |

**选择建议**：
- 参考图为 `direct` usage 且需精确复现 → 优先 Agnes（接受中文渲染风险，或用 `text: none`）
- 参考图仅取风格/色板（style/palette usage）+ 需中文文字 → 优先 Gaoding
- 冲突时由调用方通过 `cover_provider` 显式指定

---

## 6. 反模式（禁止）

- ❌ 只透传路径不做分析：`references: ["brand.png"]` 然后什么都不写进 prompt
- ❌ 模糊描述：`"参考品牌风格"` / `"像参考图那样"`
- ❌ 把 hex 当可见文字：参考色值只进 frontmatter，正文用色名
- ❌ 复刻真实人脸：人像参考必须做风格化转换
- ❌ 忽略 usage 分类：把 `style` 参考当 `direct` 强行复现具体内容
