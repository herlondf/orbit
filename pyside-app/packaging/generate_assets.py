"""Generate MSIX required PNG assets from resources/icon.ico."""
import os
import sys

try:
    from PIL import Image
except ImportError:
    print("Install Pillow: pip install Pillow")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICO = os.path.join(ROOT, 'resources', 'icon.ico')
ASSETS = os.path.join(ROOT, 'packaging', 'Assets')

os.makedirs(ASSETS, exist_ok=True)

SIZES = {
    'StoreLogo.png': (50, 50),
    'Square44x44Logo.png': (44, 44),
    'Square150x150Logo.png': (150, 150),
    'Wide310x150Logo.png': (310, 150),
    'SplashScreen.png': (620, 300),
}


def make_asset(name: str, size: tuple):
    w, h = size
    if os.path.exists(ICO):
        img = Image.open(ICO).convert('RGBA')
    else:
        img = Image.new('RGBA', (256, 256), (124, 106, 247, 255))

    # Center icon on dark background
    out = Image.new('RGBA', (w, h), (22, 22, 26, 255))
    icon_size = min(w, h) - 8
    resized = img.resize((icon_size, icon_size), Image.LANCZOS)
    x = (w - icon_size) // 2
    y = (h - icon_size) // 2
    out.paste(resized, (x, y), resized)

    path = os.path.join(ASSETS, name)
    out.save(path, 'PNG')
    print(f'Created: {name} ({w}x{h})')


for name, size in SIZES.items():
    make_asset(name, size)

print(f'\nAssets created in: {ASSETS}')
