@echo off
REM Build standalone VTW.exe

echo Installing PyInstaller...
pip install pyinstaller -q

echo.
echo Building VTW.exe...
python -m PyInstaller --onefile --windowed --name VTW --add-data "config.example.json;." src/gui.py

echo.
echo Done! VTW.exe is in the dist\ folder.
pause
