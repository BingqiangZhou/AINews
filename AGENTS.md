# AGENTS.md — AINews workspace

A **Claude Code / ZCode plugin** (`ainews-pipeline`) packaged for distribution via GitHub. An end-to-end content automation pipeline: RSS AI-news sources → rule prefilter → model scoring → factual material → article → podcast → video → draft-publish to 3 platforms (WeChat 公众号 / 喜马拉雅 boker / 抖音 douyin). There is **no build / lint / test step** — each skill ships its own Python scripts invoked directly via the conda Python.

## Layout

```
.claude-plugin/       ← Claude Code plugin manifest (plugin.json + marketplace.json + hooks/)
skills/               ← the actual "code": the skill library (read SKILL.md first in each)
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

## Shared code & docs single-sourcing

`audio-to-social` is the de-facto **shared-scripts / shared-config / shared-docs hub** (not just a peer orchestrator). These single-source rules were consolidated to kill drift:

- **`scripts/lib/utils.py` canonical copy lives in `audio-to-social/scripts/lib/`.** `whisper-transcribe` and `article-to-video` MUST NOT keep their own copy:
  - `whisper-transcribe/scripts/transcribe-faster-whisper.py` `sys.path.insert`s audio-to-social's `scripts/` and `from lib.utils import ...` (its own `lib/` dir was removed).
  - `article-to-video/scripts/lib/utils.py` is a **thin re-export shim** (loads audio-to-social's utils via `importlib` by absolute path, re-exports the public surface) — needed because article-to-video keeps its own `lib/caption_align.py` (vendored), and two same-named `lib` packages can't both win `sys.path`. The shim's only job is forwarding; do not add logic there.
  - `image-generator/scripts/lib/utils.py` and `browser-publisher/scripts/lib/utils.py` are **unrelated** modules (AGNES helpers / WeChat HTTP helpers) — different content, same filename, leave as-is.
- **`voice_ref.wav` single copy** at `audio-to-social/scripts/voice_ref.wav`. `tts-generation/scripts/mimo_tts.py` resolves its default ref audio to `../../audio-to-social/scripts/voice_ref.wav`; no other copy exists.
- **AI-腔禁用词 (banned-phrase blocklist) single source** = `audio-to-social/references/brand-config.md` (`## 禁用 AI 腔短语`). Both `article-studio/.../validate_content_quality.py` and `article-to-solo-podcast/.../validate_solo_script.py` parse this same file at runtime. `article-to-solo-podcast/config.json#content.machine_word_blocklist_extra` is an optional *additive* list (default `[]`), NOT a parallel source. Never inline the phrase list in skill docs — link to brand-config.md.
- **`agents/_shared_base.md`** (in `audio-to-social/agents/`) is the cross-skill base contract: `<py>`/ffmpeg resolution, unified return format, 5 file-write rules, shared error codes, episode single-source, "默认不回退". Each skill's `agents/_shared.md` inherits it (inline-copies the load-bearing invariants, since sub-agents may not follow relative links) and adds skill-specific deltas (paths, persona, source-specific anti-fabrication, skill-specific error codes).
- **article-to-video 5-script invocation** canonical bash lives in `article-to-video/SKILL.md` ("### 脚本调用示例"). Both orchestrators' `delegation-contracts.md` and `audio-to-social/SKILL.md` reference it rather than duplicating the block.
- **`config.json` field naming**: prefer `environment.conda_python` / `environment.ffmpeg` / `environment.ffprobe` (nested). `audio-to-social/scripts/lib/utils.py`'s `get_ffmpeg_path()`/`get_ffprobe_path()` accept both the nested `environment.*` and legacy flat `ffmpeg_path`/`ffprobe_path` keys. Mirrored model names (`mimo-v2.5-tts-voiceclone`, `万相2.7`, …) live once in `audio-to-social/config.json`; downstream skills express the relationship via a `reused_from_audio_to_social` (or `_reused_from_audio_to_social`) block rather than re-declaring the values (fields actually read by a skill's own workflow are kept, with a `_note` flagging the sync relationship).

## Command & runtime conventions

- **`<py>` = the Python interpreter resolved by the plugin.** Resolution order: env var `AINews_PYTHON` → each skill's `config.environment.conda_python` (legacy flat `python_executable`/`conda_python` also accepted) → `python` on PATH. In Claude Code this is auto-populated from the plugin's `conda_python` userConfig via the `SessionStart` hook. Never assume a hardcoded absolute path.
- Scripts are run as `<py> skills/<skill>/scripts/<x>.py ...` with absolute or repo-relative paths (CWD = repo root).
- ffmpeg/ffprobe resolve via `AINews_FFMPEG`/`AINews_FFPROBE` → `config.environment.ffmpeg`/`ffprobe` (or legacy `config.ffmpeg_path`/`ffprobe_path`) → on PATH; CJK subtitle font via `AINews_FONT` → `config.font` → platform default. Paths are Windows; the repo runs on win32.
- **Secrets are env vars only** (`WECHAT_MP_APPID`, `WECHAT_MP_APPSECRET`, `MIMO_API_KEY`, `AGNES_API_KEY`); never committed. Browser login state lives under `skills/browser-publisher/configs/browser-auth/` (gitignored).
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

## Release flow (versioning + CHANGELOG + GitHub Release)

One-shot, locally-triggered: the `/release` skill (`.zcode/skills/release/SKILL.md`, a maintenance tool — **not** part of the published plugin's `skills/`) orchestrates everything; CI only auto-creates the GitHub Release from a pushed tag.

- **Trigger**: `/release` (or ask "发布 / release / 发版 / 打 tag / 生成 changelog / 更新版本").
- **Version source**: git tag `vX.Y.Z` is canonical, and `.claude-plugin/plugin.json`'s `version` field is **kept in sync** with it on each release (drop the `v` prefix). `marketplace.json` has no version field — leave it. Commit messages use **conventional commits** (`feat`/`fix`/`refactor`/`docs`/...); `git-cliff` parses them via `cliff.toml` (full commit_parsers + `<!-- AI_SUMMARY -->` placeholder that the skill replaces with a 2-3 sentence summary).
- **Flow**: skill → preview changes & wait for confirmation → `git cliff` regenerates/prepends `CHANGELOG.md` → bump `plugin.json` version → commit → `git tag -a <VERSION>` → `git push origin HEAD --tags`.
- **CI**: `.github/workflows/release.yml` triggers on `push: tags: ['v*']`, slices the matching `## <TAG>` section out of `CHANGELOG.md` with awk, and creates the GitHub Release via `softprops/action-gh-release@v2` (no build artifacts — source-only repo).
- **First release**: no tags exist yet. First cut defaults to `v<plugin.json version>` (currently `v1.0.0`), treating the already-migrated 11 skills as the initial release; CHANGELOG is then generated from the repo's initial commit.
