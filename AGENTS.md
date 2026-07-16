# AGENTS.md — AINews workspace

ZCode **skills workspace** (not a traditional code project). An end-to-end content automation pipeline: RSS AI-news sources → rule prefilter → model scoring → factual material → article → podcast → video → draft-publish to 3 platforms (WeChat 公众号 / 喜马拉雅 boker / 抖音 douyin). There is **no build / lint / test step** — each skill ships its own Python scripts invoked directly via the conda Python.

## Layout

```
.zcode/skills/        ← the actual "code": the skill library (read SKILL.md first in each)
configs/              ← runtime config & data (tracked, except state.json)
  bestblogs-sources/  ← sources.json + sources.md (1686 RSS feeds, AI category ~170+)
  ai-news-digest/     ← state.json (RSS incremental cursor; gitignored)
articles/             ← per-run output: articles/{YYYY-MM-DD}_AI日报/ (gitignored)
AGENTS.md             ← this file
```

Each skill folder follows the same shape: `SKILL.md` (frontmatter + flow) + `config.json` + `scripts/` + `references/` (loaded on demand) + `agents/` (sub-agent contracts) + sometimes `assets/`. Some skills also have a local `AGENTS.md` for agent entry notes.

## Skills & roles

| Skill | Role |
|-------|------|
| **ai-news-digest** | Pure orchestrator (`metadata.orchestrator: true`). RSS → score → factual material → delegates all content production + publish. Entry point: `/ai-news-digest`. |
| **audio-to-social** | Pure orchestrator + **asset/config reuse hub**. Many skills reuse its `config.json` (brand/cover/image/tts) and `references/brand-config.md`. Has the only inline sub-agent (audio-engineer, Whisper transcription). |
| **article-studio** | Central writing skill. Any 公众号 article type; `transcript` mode = skip web research, source file is sole authority. Used by all orchestrators. |
| article-cover-image-generator | Cover image (900x383). |
| article-illustrator | Article illustrations (prepare → render, rewrites `![]()` into article). |
| article-to-solo-podcast | Article → single-voice podcast + TTS. Claims episode number. |
| article-to-video | Article + illustrations + podcast → landscape video (5 sequential CLI scripts). |
| **browser-publisher** | Owns **ALL** publishing logic. Never rewrite publish code elsewhere; always delegate here. |
| image-generator / tts-generation / whisper-transcribe | Shared media utilities. |

## Hard architecture rules

- **Orchestrators produce no content.** `ai-news-digest` and `audio-to-social` only run scripts + delegate to downstream skills. Don't add content generation to them.
- **Publishing is single-sourced in `browser-publisher`.** No other skill writes publish code.
- **`article-studio` transcript mode** is the glue for orchestrators: pass `source_mode: "transcript"` + `source_file` (factual-material markdown); it then skips web research and treats that file as the sole authority (zero external facts).
- **Config reuse points at `audio-to-social/config.json`** (read-only from other skills): cover/image/tts settings and — critically — `platforms.boker_next_episode`, the **single source of the boker episode number**.
- **Episode number is shared.** `ai-news-digest` and `audio-to-social` read the same `boker_next_episode`. Don't run both the same day (episode race). Only `bump_episode.py` (after successful publish) writes it.

## Command & runtime conventions

- **`<py>` = `D:\Development\miniconda3\python.exe`** — always use this; never assume `python` on PATH is correct. Read from each skill's `config.environment.conda_python`.
- Scripts are run as `<py> .zcode/skills/<skill>/scripts/<x>.py ...` with absolute or repo-relative paths.
- ffmpeg = `ffmpeg`; font = `C:\Windows\Fonts\msyh.ttc` (Chinese). Paths are Windows; the repo runs on win32.
- **Secrets are env vars only** (`WECHAT_MP_APPID`, `WECHAT_MP_APPSECRET`, `MIMO_API_KEY`, `AGNES_API_KEY`); never committed. Browser login state lives under `browser-publisher/configs/browser-auth/` (gitignored).
- **Dates = today, Beijing time (UTC+8)**, `YYYY-MM-DD`. Event dates come from RSS `published`; if missing, mark "（具体日期未公布）" — never fabricate.
- Invoke a skill via its slash command, e.g. `/ai-news-digest`.

## Platform identifiers (internal names, used in code/config/state)

- `gongzhonghao` = 微信公众号 (WeChat MP). Draft via API (`wechat-mp-draft.py`); publishing (non-draft) needs user scan.
- `boker` = 喜马拉雅播客 (Ximalaya podcast). Browser upload.
- `douyin` = 抖音 (Douyin). Browser video upload, optional scheduled.
- (browser-publisher also supports `xiaohongshu`, `wechat_channels` — not on the digest pipeline.)

## Output naming (in each `articles/{date}_AI日报/`)

`公众号_文章.md` + `公众号_摘要.txt` + `公众号_封面.png`; `_research/事实素材与来源.md` (article-studio authority source); `imgs/` (illustrations); `_podcast/播客_*` ; `_video/公众号_视频.mp4`; `temp/` (intermediate); `prompts/` (scoring); `state.json` (orchestrator state machine).

## Two cross-cutting invariants (do not violate)

1. **State machine = `state.json`, checkpoint-resumable.** Each phase writes `stages.{stage}.status="completed"` + artifact path on completion; re-entry skips completed stages. When editing state: **read the full file → modify target fields → write the whole file back** (never partial overwrites).
2. **反虚构硬约束 (anti-fabrication).** Digest content may only come from the day's real RSS items (`temp/digest_ranked.json`), each cited with its source URL preserved verbatim. Never use LLM built-in knowledge as collected facts, never rewrite/truncate source URLs, never invent event dates.

## What to read before changing sensitive areas

- Editing orchestrator flow / state → `ai-news-digest/references/state-schema.md`, `delegation-contracts.md`, and `agents/_shared.md` (paths, return format, error codes, anti-fabrication).
- Editing a skill → its `SKILL.md` first, then its `references/` (loaded on demand, listed under each skill's "按需加载").
- Publishing → `browser-publisher/references/{platform}.md` + `ai-news-digest/references/publishing.md` (filename adapters, e.g. `_video/公众号_视频.mp4` → `抖音_短视频.mp4`, and the 抖音 文案 format).
