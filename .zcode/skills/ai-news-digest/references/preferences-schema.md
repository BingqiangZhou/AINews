# Preferences Schema（config.json 字段说明）

> 本文件说明 `config.json` 各字段的含义、默认值、被谁读。**config.json 是单一配置源**，脚本和 SKILL.md 都从这里读，不在代码里硬编码。

## 字段级回退优先级

用户本次输入 > `config.json` > SKILL.md 默认值。

## 顶层分组

| 分组 | 用途 |
|------|------|
| `schema_version` | 固定 `ai-news-digest-v1`，用于 schema 迁移 |
| `description` | skill 描述（供人读） |
| `brand` | 品牌名 + 输出根目录 |
| `sources` | RSS 信源表 / 采集窗口 / 并发 |
| `scoring` | 预筛/打分截取数 / 推广词 / 文章字数 |
| `article` | 文章类型 / 人设 / 系列前缀 |
| `media` | 各产物开关（封面/插图/播客/视频） |
| `platforms` | 三平台开关与参数 |
| `environment` | 工具路径 / API key 环境变量名 |
| `reused_from_audio_to_social` | 只读复用 audio-to-social 的资产清单 |

---

## brand

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 品牌名（"AINews"） |
| `storage_root` | string | 输出根目录（`articles/` 的父目录）。与 audio-to-social 共享同一值 |

## sources

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `sources_json` | string | `configs/bestblogs-sources/sources.json` | 信源表路径（相对仓库根） |
| `state_json` | string | `configs/ai-news-digest/state.json` | RSS 增量游标 state 路径（相对仓库根） |
| `types` | string[] | `["ARTICLE"]` | 源类型过滤（poll_feeds `--types`） |
| `categories` | string[] | `["Artificial_Intelligence"]` | 源分类过滤（poll_feeds `--categories`）；空数组=不过滤 |
| `hours_window` | number | 24 | 时间窗口（小时），只取近 N 小时新条目 |
| `poll_concurrency` | number | 20 | 并发抓取数 |
| `poll_timeout_seconds` | number | 15 | 单源超时（秒） |

## scoring

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `prefilter_top` | number | 80 | 预筛截取 top-N（prefilter.py） |
| `ai_scored_top` | number | 50 | AI 打分的候选数（build_digest prompt `--top`） |
| `digest_final_top` | number | 20 | 最终榜单条数（merge_scores `--top`） |
| `penalty_keywords` | string[] | 见 config | 推广词表（标题命中则剔除）；从 prefilter.py 的 DEFAULT 移出，便于按主题调 |
| `max_per_source` | number | 5 | 同源封顶（防头部源刷屏） |
| `article_min_words` | number | 900 | 文章最小字数（传给 article-studio + 质检脚本） |
| `article_max_words` | number | 2000 | 文章最大字数 |

## article

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `article_type` | string | `news` | article-studio 的文章类型（news=资讯/盘点，适配 AI 日报） |
| `persona` | string | `AI小周` | 人设名（写入事实素材文件，article-studio writer 据此调整口吻） |
| `series_prefix` | string | `AI日报` | 系列前缀（项目目录名 + 文章标题前缀） |

## media

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `cover_enabled` | bool | true | 是否生成封面（Phase 7a） |
| `illustrations_enabled` | bool | true | 是否生成插图（Phase 7b） |
| `tts_podcast_enabled` | bool | true | 是否生成播客（Phase 7c） |
| `video_enabled` | bool | true | 是否生成视频（Phase 7d，最耗时） |

> 关闭的产物在 state.json 里记 `status: "skipped"`，归档校验跳过。

## platforms

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `gongzhonghao.enabled` | bool | true | 是否发布公众号 |
| `gongzhonghao.mode` | string | `draft_only` | 发布模式（仅草稿；发表需扫码） |
| `boker.enabled` | bool | true | 是否发布喜马拉雅 |
| `douyin.enabled` | bool | true | 是否发布抖音 |

## environment

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `conda_python` | string | `D:\Development\miniconda3\python.exe` | Python 解释器（`<py>`） |
| `ffmpeg` | string | `ffmpeg` | FFmpeg 可执行文件 |
| `font` | string | `C:\Windows\Fonts\msyh.ttc` | 字体文件（视频字幕用） |
| `wechat_mp_appid_env` | string | `WECHAT_MP_APPID` | 公众号 AppID 的**环境变量名**（不是值） |
| `wechat_mp_appsecret_env` | string | `WECHAT_MP_APPSECRET` | 公众号 AppSecret 的环境变量名 |
| `mimo_api_key_env` | string | `MIMO_API_KEY` | MiMo TTS API key 的环境变量名（播客用） |
| `agnes_api_key_env` | string | `AGNES_API_KEY` | Agnes 图像 API key 的环境变量名（封面/插图 Agnes 后端，默认关） |

> **关键**：API key 存的是环境变量**名**而非值——安全且不与 shell profile 耦合。运行时由脚本 `os.environ[name]` 读取。

## reused_from_audio_to_social

只读引用 audio-to-social 的资产（避免漂移）。每项是相对路径（相对本 skill 目录）：

| 字段 | 引用目标 | 用途 |
|------|---------|------|
| `cover` | `../audio-to-social/config.json#cover` | 封面后端配置（Gaoding 等） |
| `image` | `../audio-to-social/config.json#image` | 图片尺寸（cover_size 900x383 等） |
| `tts` | `../audio-to-social/config.json#tts` | TTS 配置（MiMo 等） |
| `boker_next_episode` | `../audio-to-social/config.json#platforms.boker_next_episode` | **集号单一来源**（与 audio-to-social 共享） |
| `validate_quality_script` | `../audio-to-social/scripts/validate_content_quality.py` | 内容质检脚本（article-studio 复用） |
| `backup_file_script` | `../audio-to-social/scripts/backup_file.py` | 覆盖前备份 |
| `bump_episode_script` | `../audio-to-social/scripts/bump_episode.py` | 集号递增（发布后） |
| `compress_images_script` | `../audio-to-social/scripts/compress_images.py` | 图片压缩（归档时） |
| `reconcile_media_script` | `../audio-to-social/scripts/reconcile_media.py` | 一致性检查（归档时） |
| `voice_ref_wav` | `../audio-to-social/scripts/voice_ref.wav` | TTS 克隆参考音频（播客用） |
| `brand_config` | `../audio-to-social/references/brand-config.md` | 品牌声音定义（AI 小周人设来源） |

## 首次运行引导

首次运行（config.json 不存在或字段缺失）时，引导式生成：
1. `brand.storage_root`：问用户输出根目录（默认与 audio-to-social 同）。
2. `sources.categories`：问聚焦哪些分类（默认 Artificial_Intelligence）。
3. `media.*_enabled`：问要产出哪些形态（默认全开）。
4. `environment.*`：检测 conda_python / ffmpeg 是否在 PATH。
5. 检测 `configs/bestblogs-sources/sources.json` 是否存在；不存在则提示用户放置。

## config 备份

config.json 同目录维护 `config-backup-{timestamp}.json`（最多 3 份），由 audio-to-social 的 `backup_file.py` 轮转。
