# MSIX Assets

Required image assets for MSIX package. Generate these from resources/icon.ico:

| File | Size | Usage |
|------|------|-------|
| StoreLogo.png | 50×50 | Store listing |
| Square44x44Logo.png | 44×44 | Taskbar icon |
| Square150x150Logo.png | 150×150 | Start menu tile |
| Wide310x150Logo.png | 310×150 | Wide start menu tile |
| SplashScreen.png | 620×300 | Splash screen |

Generate with:
```
python packaging/generate_assets.py
```
