@echo off
REM VTW Launcher
REM Run VTW command line version

set SCRIPT_PATH=src\vtw.py

REM Check if script exists
if not exist "%SCRIPT_PATH%" (
    echo Error: Script not found: %SCRIPT_PATH%
    pause
    exit /b 1
)

REM Show usage if no arguments
if "%~1"=="" (
    echo.
    echo Usage:
    echo   run.bat ^<Bilibili Video URL^>
    echo.
    echo Examples:
    echo   run.bat https://www.bilibili.com/video/BV1xx411c7mD
    echo   run.bat https://space.bilibili.com/123456 -l 10
    echo   run.bat https://www.bilibili.com/video/BV1xx411c7mD --asr
    echo.
    pause
    exit /b 0
)

REM Run VTW
echo Running VTW...
echo Script: %SCRIPT_PATH%
echo URL: %~1
echo.

python "%SCRIPT_PATH%" %*
if errorlevel 1 (
    pause
)
