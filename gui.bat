@echo off
REM VTW GUI Launcher
REM Start GUI version of VTW

set PYTHON_PATH=C:\Users\27970\AppData\Local\Programs\Python\Python313\python.exe
set GUI_SCRIPT=src\gui.py

REM Check if Python exists
if not exist "%PYTHON_PATH%" (
    echo Error: Python not found: %PYTHON_PATH%
    pause
    exit /b 1
)

REM Check if GUI script exists
if not exist "%GUI_SCRIPT%" (
    echo Error: GUI script not found: %GUI_SCRIPT%
    pause
    exit /b 1
)

REM Launch GUI
echo Starting VTW GUI...
echo Python: %PYTHON_PATH%
echo Script: %GUI_SCRIPT%
echo.

"%PYTHON_PATH%" "%GUI_SCRIPT%"

REM If error occurred, pause to see error message
if errorlevel neq 0 (
    echo.
    echo Launch failed, please check error message above
    pause
)
