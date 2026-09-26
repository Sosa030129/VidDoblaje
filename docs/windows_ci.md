# Windows CI

GitHub Actions workflow en `.github/workflows/windows-ci.yml`.

## Pasos del workflow

1. Checkout code
2. Setup Python 3.11
3. Install dependencies
4. Install NSIS
5. Download FFmpeg (Windows LGPL)
6. Generate app icon
7. Run quick tests
8. Build VidDoblaje.exe (PyInstaller)
9. Verify PE32
10. Run smoke test
11. Build VidDoblajeSetup.exe (NSIS)
12. Install (silent /S)
13. Verify installation
14. Run installed VidDoblaje.exe
15. Uninstall (silent /S)
16. Verify no residue
17. Upload artifacts

## Activación

El workflow se ejecuta automáticamente al hacer push a `main`.
