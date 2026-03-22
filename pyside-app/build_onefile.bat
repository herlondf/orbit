@echo off
echo Building OctoChat (single file, slower startup)...
pip install pyinstaller --quiet
pyinstaller main.py ^
  --name OctoChat ^
  --onefile ^
  --windowed ^
  --icon resources\icon.ico ^
  --add-data "resources;resources" ^
  --hidden-import PySide6.QtWebEngineCore ^
  --hidden-import PySide6.QtWebEngineWidgets ^
  --hidden-import win32crypt ^
  --hidden-import websocket ^
  --hidden-import cryptography ^
  --exclude-module tkinter ^
  --clean --noconfirm
echo.
echo Build complete! Output: dist\OctoChat.exe
pause
