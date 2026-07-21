# 环境依赖与迁移

本 skill 是 Markdown 编排器 + `build_segments.py` 脚本，实际生图委托 `image-generator` skill。

## 运行依赖

| 依赖 | 用途 | 说明 |
|------|------|------|
| **image-generator skill** | 实际生图（Gaoding/Jimeng/Agnes/Pollinations） | 必须已安装在本仓库 `skills/image-generator/` |
| **Python 3.10+** | image-generator 的 agnes_image.py + 本 skill 的 build_segments.py | 路径见 config.json `environment.conda_python` |
| **Pillow (PIL)** | 后处理裁剪/resize | image-generator 内使用 |
| **Chrome** | Gaoding/Jimeng 浏览器自动化 | 由 chrome-devtools MCP 自动启动；需已登录稿定/即梦 session |
| **AGNES_API_KEY** | Agnes 后端（仅 `backend.provider: agnes` 或回退时） | 见仓库根 AGENTS.md 环境变量表 |

## 迁移清单（换机器时必改）

本 skill 在 AINews 仓库中遵循**单一来源**约定：跨 skill 共享字段（cover 后端、environment）优先读 `../ai-news-digest/config.json`，本 skill 的 `config.json` 仅作独立运行时的 fallback 与本地偏好。

- `conda_python`：默认 `"python"`（依赖 PATH 解析，由 plugin 的 `SessionStart` hook 注入 `AINews_PYTHON`）；如需指向本机 miniconda3 绝对路径，改 `ai-news-digest/config.json#environment.conda_python`
- `chrome_download_dir`：本机 Chrome 下载目录（Gaoding 导出文件落地点）；留空则由 image-generator 自行解析

> AINews 约定（见根 AGENTS.md「Command & runtime conventions」）：`<py>` 解析顺序为 env var `AINews_PYTHON` → 各 skill 的 `config.environment.conda_python` → PATH 上的 `python`。不要硬编码机器绝对路径。
