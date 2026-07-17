# 双音色分段合成 TTS

> `scripts/duo_tts.py` 的实现依据 + agent 理解"为什么双人必须分段、为什么 turn 级合成"。

## 核心结论：双音色无法一次合成，必须按角色标注分段

单人播客的"全文一次合成"（单音色一致）在双人场景**不适用**——MiMo TTS 单次请求只能用一个音色（voice 参数单一）。双人对话（A=苏打、B=冰糖）必须**按角色标注切段 → 每 turn 用对应内置音色合成 → ffmpeg 拼接**。这是双人播客的唯一可行路径。

## 为什么 turn 级合成（而非段级）

一个 **turn = 同一角色的连续台词**（同角色连续多段合成一次，音色最一致；角色切换即 turn 边界）。

- **turn 级**：同角色连续的几段（如 A 说 3 段）一次合成，音色/语气连贯；角色切换处是天然的对话停顿（插静音），拼接最自然。
- **段级**（每段单独合成）：同角色的相邻段拼接处易有音色微漂/节奏断裂，且合成请求数翻倍（turn 数 ≈ 段数的 1/2~1/3）。
- **句级**：更细，请求爆炸 + 拼接缝更多，无收益。

`duo_tts.parse_turns()` 把脚本按角色标注聚合成 turn：同一角色的连续台词（跨空行）属同一 turn，角色切换开新 turn。

## MiMo 内置音色清单（mimo-v2.5-tts 模型）

双人播客用 **内置音色**（`clone=False`，模型 `mimo-v2.5-tts`，非 voiceclone）。已配置：

| 角色 | 音色名 | 性别 | config 键 |
|------|--------|------|-----------|
| 主播A | 苏打 | 男 | `tts.voices.a` |
| 主播B | 冰糖 | 女 | `tts.voices.b` |

中文精品预置音色全表（官方文档）：苏打(男)、白桦(男)、冰糖(女)、茉莉(女)。选苏打+冰糖是为了**男女声对比鲜明**（听众秒辨双主持）。如需换音色，改 `config.tts.voices` 即可，脚本无需改。

> **voiceclone/voice_ref.wav 路径已退役**：单人播客用 clone + `tts-generation/scripts/voice_ref.wav`（单一 clone 参考音），双人改用内置音色后该路径不再被本 skill 引用（voice_ref.wav 仍在 tts-generation，供其它单音色场景用）。

## 合成流程（duo_tts.synth_and_concat）

```
解析 turn 列表 [{role, text}]
  → 逐 turn 合成 wav（A→苏打 builtin，B→冰糖 builtin，clone=False；失败串行重试 3 次）
  → 生成静音片段（turn_gap_ms，默认 250ms）
  → ffmpeg concat（turn 间插静音）：turn0 silence turn1 silence turn2 ...
  → 全局一次 loudnorm（I=-16:TP=-1.5:LRA=11）+ 转 320k mp3
```

### 为什么全局一次 loudnorm（而非 turn 级）
- 两内置音色响度可能不同。**全局一次 loudnorm** 让整条音频响度统一（-16 LUFS），且避免 turn 级归一化导致的拼接处响度跳变。
- turn 级 loudnorm 会让每个 turn 都拉到 -16，拼接后反而失去自然的强弱起伏，且苏打/冰糖的音色特性响度被强行抹平。

### 对话间隔静音（turn_gap_ms）
- 默认 250ms（`config.tts.turn_gap_ms`）。角色切换处的自然停顿，让"两人对话"的感觉真实，避免 A 刚说完 B 立刻接（机器感）。
- 太短（<150ms）像抢话/连读；太长（>400ms）像冷场。250ms 是对话节奏的甜区。

## 字幕对齐兼容（article-to-video）

duo_tts 落盘 `temp/script_clean.txt`（剥了 `[SECTION:N]` 标记 + `A：`/`B：` 角色标注的纯文本）+ `sections.json`（每节在 **clean 文本**的字符偏移）。下游 article-to-video 用 Whisper 转录音频 → word-level 时间戳 → 映射到 clean 文本，实现按插图分段切场景。

**关键**：clean 文本必须与合成音频内容完全一致（无角色标注/section 标记），否则 Whisper 转录文本与脚本不匹配致字幕错位。`duo_tts._recompute_section_offsets()` 重算偏移使其基于剥了角色标注的 clean 文本（extract_sections 原始偏移基于含标注文本，需修正）。

## 不要做

- ❌ 不要一次合成全部（MiMo 单请求单音色，无法合成双人对话）。
- ❌ 不要用 clone 模式（双人用内置音色苏打+冰糖，clone 是单人遗留）。
- ❌ 不要把中文输出路径直接喂 ffmpeg（用无中文 temp 目录 + shutil.copy）。
- ❌ 不要在 turn 内留半句话（一句话被拆到两个 turn → 拼接处断句怪）——craft §7 要求每个 turn 语义完整。
