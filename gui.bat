@echo off
REM VTW GUI Launcher
REM Start GUI version of VTW

set GUI_SCRIPT=src\gui.py

REM Check if GUI script exists
if not exist "%GUI_SCRIPT%" (
    echo Error: GUI script not found: %GUI_SCRIPT%
    pause
    exit /b 1
)

REM Launch GUI
echo Starting VTW GUI...
echo Script: %GUI_SCRIPT%
echo.

python "%GUI_SCRIPT%"
if errorlevel 1 (
    echo.
    echo Launch failed, please check error message above
    pause
)
