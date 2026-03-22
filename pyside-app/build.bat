@echo off
echo Building OctoChat...
pip install pyinstaller --quiet
pyinstaller OctoChat.spec --clean --noconfirm
echo.
echo Build complete! Output in dist\OctoChat\
pause
