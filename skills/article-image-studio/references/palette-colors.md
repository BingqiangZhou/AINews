# Palette Color Definitions

11 个权威色板 + 3 个别名（向后兼容 illustration 流程的历史命名）。每个色板附 hex 定义、适用场景、色彩占比。适用哪些 preset/style 见 style-presets.md / styles.md。

> **别名映射**（illustration 流程的历史 4 色板 → 权威 11 色板）：
> - `macaron` → `macaron`（直接重合，无别名需要）
> - `warm` → `warm`（直接重合）
> - `mono-ink` → `mono`（黑墨白底 + 语义点缀，hex 完全一致）
> - `neon` → 独立保留（见下文「neon」段，与 `vivid` 语义不同：neon 是深底霓虹，vivid 是白底高饱和三原色）
>
> **单一来源声明**：本文件是所有色板 hex 与语义约束的唯一事实源。illustration 的 `--palette mono-ink`/`neon` 在解析时映射到本文对应色板。

---

## warm — Friendly, approachable, human-centered

| Role | Color | Hex |
|------|-------|-----|
| Primary 1 | Warm Orange | #ED8936 |
| Primary 2 | Golden Yellow | #F6AD55 |
| Primary 3 | Terracotta | #C05621 |
| Background | Cream | #FFFAF0 |
| Background Alt | Soft Peach | #FED7AA |
| Accent 1 | Deep Brown | #744210 |
| Accent 2 | Soft Red | #E53E3E |

Best for: personal growth, lifestyle, education, human stories
Color ratio: 主色 (Primary 1-3) ~60%, Background ~30%, Accent ~10%

## elegant — Sophisticated, refined

| Role | Color | Hex |
|------|-------|-----|
| Primary 1 | Soft Coral | #F8B4B4 |
| Primary 2 | Muted Teal | #7BC8C8 |
| Primary 3 | Dusty Rose | #D4A0A0 |
| Background | Warm White | #FAF5F0 |
| Accent 1 | Champagne | #D4C5A9 |
| Accent 2 | Deep Mauve | #8B6F6F |

Best for: business, professional, thought leadership, luxury
Color ratio: 主色与背景柔和各半，Accent 点缀 < 15%

## cool — Technical, professional, precise

| Role | Color | Hex |
|------|-------|-----|
| Primary 1 | Engineering Blue | #2563EB |
| Primary 2 | Navy Blue | #1E3A5F |
| Primary 3 | Cyan | #06B6D4 |
| Background | Light Gray | #F8F9FA |
| Background Alt | Blueprint Off-White | #FAF8F5 |
| Accent 1 | Amber | #F59E0B |
| Accent 2 | Light Blue | #BFDBFE |

Best for: architecture, system design, API, technical documentation
Color ratio: Engineering Blue 主导 ~50%, Background 浅灰 ~35%, Accent 点缀 ~15%

## dark — Premium, cinematic

| Role | Color | Hex |
|------|-------|-----|
| Primary 1 | Charcoal | #2D2D2D |
| Primary 2 | Deep Navy | #0F172A |
| Background | Near Black | #0A0A0A |
| Accent 1 | Electric Blue | #3B82F6 |
| Accent 2 | Gold | #F59E0B |
| Text | White | #FFFFFF |

Best for: entertainment, premium, cinematic, dark mode
Color ratio: Charcoal/Navy/Background 深色主导 ~75%, Accent 电光蓝/金 ~20%, Text 白 ~5%

## earth — Natural, organic

| Role | Color | Hex |
|------|-------|-----|
| Primary 1 | Forest Green | #2D6A4F |
| Primary 2 | Terracotta | #C05621 |
| Primary 3 | Warm Brown | #8B6F47 |
| Background | Warm Linen | #FAF3E8 |
| Accent 1 | Olive | #6B7B3A |
| Accent 2 | Sand | #D4B896 |

Best for: nature, wellness, eco, organic, travel
Color ratio: Forest Green 主导 ~45%, Background 暖麻 ~35%, Terracotta/Brown 辅 ~20%

## vivid — High energy, saturated

| Role | Color | Hex |
|------|-------|-----|
| Primary 1 | Electric Red | #EF4444 |
| Primary 2 | Bright Blue | #2563EB |
| Primary 3 | Vibrant Yellow | #EAB308 |
| Background | White | #FFFFFF |
| Accent 1 | Hot Pink | #EC4899 |
| Accent 2 | Lime | #84CC16 |

Best for: product launch, gaming, promotion, event
Color ratio: 高饱和三原色均衡分布 ~70%, Background 白 ~20%, Accent 粉/绿 ~10%

## pastel — Soft, gentle

| Role | Color | Hex |
|------|-------|-----|
| Primary 1 | Soft Pink | #F9A8D4 |
| Primary 2 | Light Blue | #BAE6FD |
| Primary 3 | Mint | #A7F3D0 |
| Background | Cream White | #FFF8F0 |
| Accent 1 | Lavender | #C4B5FD |
| Accent 2 | Peach | #FED7AA |

Best for: fantasy, children, gentle, creative, whimsical
Color ratio: 柔和粉/蓝/薄荷均衡 ~60%, Background 奶油白 ~30%, Accent 点缀 ~10%

## mono — Minimal, focused（别名：`mono-ink`）

| Role | Color | Hex |
|------|-------|-----|
| Primary 1 | Near Black | #1A1A1A |
| Primary 2 | Dark Gray | #333333 |
| Primary 3 | Medium Gray | #666666 |
| Background | Pure White | #FFFFFF |
| Accent 1 | Coral Red | #E8655A |
| Accent 2 | Muted Teal | #5FA8A8 |
| Accent 3 | Dusty Lavender | #9B8AB5 |

Color ratio: primary > 90%, semantic accents < 10%
Best for: zen, focus, essential, pure, simple

## retro — Vintage, nostalgic

| Role | Color | Hex |
|------|-------|-----|
| Primary 1 | Burnt Orange | #C2410C |
| Primary 2 | Mustard | #A16207 |
| Primary 3 | Teal | #0D9488 |
| Background | Aged Paper | #F5E6D0 |
| Accent 1 | Rust | #9A3412 |
| Accent 2 | Sage | #6B8F6B |

Best for: history, vintage, retro, classic, exploration
Color ratio: Burnt Orange/Mustard 主导 ~55%, Background 旧纸 ~30%, Teal/Rust 辅 ~15%

## duotone — Dramatic, poster-like

| Role | Color | Hex |
|------|-------|-----|
| Primary 1 | Deep Blue | #1E3A5F |
| Primary 2 | Bright Orange | #F97316 |
| Background | Dark | #0F172A |
| Accent | White highlight | #FFFFFF |

Best for: movie poster, album cover, concert, cinematic, dramatic
Color ratio: Deep Blue + Bright Orange 双色对峙各 ~40%, Background 深色 ~15%, Accent 白高光 ~5%

## macaron — Playful, educational

| Role | Color | Hex |
|------|-------|-----|
| Background | Warm Cream | #F5F0E8 |
| Lines/Text | Near Black | #1A1A1A |
| Fill 1 | Macaron Blue | #A8D8EA |
| Fill 2 | Mint Green | #B5E5CF |
| Fill 3 | Lavender | #D5C6E0 |
| Fill 4 | Peach | #FFD5C2 |
| Accent | Coral Red | #E8655A |

Best for: education, tutorial, knowledge, onboarding, concept explainer
Color ratio: Background 暖奶油 ~50%, 4 个马卡龙填充色均衡各 ~10%, Lines 近黑 ~5%, Accent 红 ~5%

---

## neon — Cyberpunk, futuristic（illustration 独有色板，独立保留）

> 与 `vivid` 的区别：`neon` 是**深底霓虹**（Dark Navy 底 + 高饱和发光色），适合赛博/未来主题；`vivid` 是**白底高饱和三原色**，适合产品发布/活动。两者不可互换。

| Role | Color | Hex |
|------|------|-----|
| 背景 | Dark Navy | #0A0E27 |
| 主色 | Electric Blue | #00D4FF |
| 辅色 1 | Neon Green | #39FF14 |
| 辅色 2 | Hot Pink | #FF006E |
| 辅色 3 | Vivid Purple | #8B5CF6 |
| 文字 | White | #FFFFFF |

---

## 颜色渲染硬约束（所有 prompt 共用）

**禁止在 prompt 视觉描述正文中包含 hex 色值**。AI 图像模型无法区分"颜色指令"和"需要显示的文字"，hex 值（如 `#ED8936`）会被误渲染为图内文字。

- prompt 正文**只用描述性颜色名**：`warm orange` / `cream background` / `暖米白` / `橄榄绿`
- hex 色值仅写入 prompt 文件的 YAML frontmatter 作为元数据
- 每个 prompt 末尾加：`不要在图片中显示任何颜色代码、十六进制数值或色号。`

Do NOT render color names, hex codes, or role labels as visible text in generated images.
