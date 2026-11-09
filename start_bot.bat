@echo off
title Discord Booster Bot
cls
echo ==============================================
echo Starting Discord Booster Bot...
echo ==============================================
python bot.py
if errorlevel 1 (
    echo.
    echo [!] Bot stopped. Check above for error messages.
    echo.
)
pause

