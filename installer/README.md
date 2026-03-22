# Orbit Installer

## Requisitos para gerar o instalador
1. Instale o [NSIS 3.x](https://nsis.sourceforge.io/Download)
2. Gere o executável com PyInstaller: `cd pyside-app && build.bat`
3. Compile o instalador: clique direito em `Orbit.nsi` → "Compile NSIS Script"
4. O arquivo `dist/Orbit-Setup.exe` será gerado

## Estrutura esperada
```
Orbit/
├── pyside-app/
│   ├── dist/Orbit/       ← gerado por build.bat
│   └── resources/icon.ico
└── installer/
    └── Orbit.nsi
```
