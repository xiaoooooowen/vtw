@echo off
REM Build standalone VTW.exe
REM Prerequisites: pip install -r requirements.txt

echo ========================================
echo   VTW Standalone EXE Builder
echo ========================================
echo.

echo [1/2] Installing PyInstaller...
pip install pyinstaller -q

echo [2/2] Building VTW.exe...
python -m PyInstaller --onefile --windowed --name VTW ^
    --add-data "config.example.json;." ^
    --paths src ^
    --hidden-import faster_whisper ^
    --hidden-import ctranslate2 ^
    --hidden-import tokenizers ^
    --hidden-import huggingface_hub ^
    --hidden-import opencc ^
    --collect-all faster_whisper ^
    src/gui.py

echo.
echo ========================================
echo   Done! VTW.exe is in the dist\ folder.
echo ========================================
pause
