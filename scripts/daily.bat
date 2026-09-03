@echo off
REM ============================================================
REM  Sequoia-X daily runner
REM  Steps: 1) incremental backfill (sina)  2) run + push to Feishu
REM  Recommended: run after 15:00 market close
REM  PURE-ASCII content to avoid GBK vs UTF-8 cmd parsing issues.
REM ============================================================
setlocal
set "ROOT=C:\Users\Administrator\WorkBuddy\2026-09-02-21-10-59\Sequoia-X-new"
set "LOG=%ROOT%\daily_%date:~0,4%%date:~5,2%%date:~8,2%.log"

cd /d "%ROOT%"
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] venv missing, run environment setup first. > "%LOG%"
    exit /b 1
)
call .venv\Scripts\activate.bat

echo [%date% %time%] === 1/2 backfill === >> "%LOG%"
python scripts\backfill_sina.py >> "%LOG%" 2>&1

echo [%date% %time%] === 2/2 run + push === >> "%LOG%"
python scripts\run_daily.py --composite >> "%LOG%" 2>&1

echo [%date% %time%] === done === >> "%LOG%"
endlocal