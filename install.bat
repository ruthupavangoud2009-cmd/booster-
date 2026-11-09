@echo off
title Installing Booster Dependencies...
echo ==============================================
echo Installing Booster Dependencies...
echo ==============================================
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r humanizer/requirements.txt
echo.
echo ==============================================
echo Installation Complete! You can now run start.bat
echo ==============================================
pause
