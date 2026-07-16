: << 'CMDBLOCK'
@echo off
REM Cross-platform launcher for the setup-env SessionStart hook.
REM
REM Reads plugin userConfig (injected by Claude Code as CLAUDE_PLUGIN_OPTION_*
REM env vars) and writes exports into %CLAUDE_ENV_FILE% via the bash script
REM setup-env (no extension). Skills' Python then reads AINews_PYTHON /
REM AINews_FFMPEG / AINews_FFPROBE / AINews_FONT with config.json fallbacks.
REM
REM On Windows: cmd.exe runs this batch portion, which finds and calls bash.
REM On Unix/Git-Bash: the shell treats ":" as no-op and the heredoc swallows
REM the batch block, then the bash body at the bottom runs setup-env directly.

if "%CLAUDE_ENV_FILE%"=="" exit /b 0

REM Try Git for Windows bash in standard locations, then bash on PATH.
if exist "C:\Program Files\Git\bin\bash.exe" (
    "C:\Program Files\Git\bin\bash.exe" "%~dp0setup-env" %*
    exit /b %ERRORLEVEL%
)
if exist "C:\Program Files (x86)\Git\bin\bash.exe" (
    "C:\Program Files (x86)\Git\bin\bash.exe" "%~dp0setup-env" %*
    exit /b %ERRORLEVEL%
)
where bash >nul 2>nul
if %ERRORLEVEL% equ 0 (
    bash "%~dp0setup-env" %*
    exit /b %ERRORLEVEL%
)
REM No bash found - exit silently (plugin still works, just without env injection)
exit /b 0
CMDBLOCK

# ---- bash branch (Unix, or Windows Git Bash reached directly) ----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec bash "${SCRIPT_DIR}/setup-env" "$@"
