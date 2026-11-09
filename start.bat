@echo off
title Discord Booster Tool
cls
python main.py
if errorlevel 1 (
    echo.
    echo [!] An error occurred while running main.py.
    echo [!] Make sure dependencies are installed by running install.bat first.
    echo.
)
pause
