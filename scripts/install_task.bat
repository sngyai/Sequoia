@echo off
REM ============================================================
REM  Register Sequoia-X daily scheduled task
REM  Double-click this on your own PC (outside the WorkBuddy sandbox)
REM  to register. Runs under the current user when logged in.
REM  Schedule: daily 19:00 (post-close; waits for Sina/Tencent hfq daily K to be published)
REM  PURE-ASCII content to avoid GBK vs UTF-8 cmd parsing issues.
REM ============================================================
set "BAT=C:\Users\Administrator\WorkBuddy\2026-09-02-21-10-59\Sequoia-X-new\scripts\daily.bat"

schtasks /create /tn "SequoiaX-Daily" /tr "%BAT%" /sc daily /st 19:00 /f
REM schtasks /create sometimes returns nonzero on /f overwrite; verify with /query instead of checking errorlevel.
schtasks /query /tn "SequoiaX-Daily" >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Registered: SequoiaX-Daily (daily 19:00)
) else (
    echo [FAIL] Registration failed. Run as administrator, or edit the BAT path.
)
pause