"""Punto de entrada: python -m viddoblaje o VidDoblaje.exe"""
from __future__ import annotations

import sys


def _is_headless_mode() -> bool:
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        return True
    if sys.platform.startswith("linux"):
        import os
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            if os.environ.get("QT_QPA_PLATFORM") not in ("offscreen", "minimal"):
                return True
    return False


def main() -> int:
    if not _is_headless_mode():
        try:
            from viddoblaje.ui.app import run_gui
            return run_gui()
        except Exception as exc:
            print(f"[VidDoblaje] No se pudo iniciar la GUI: {exc}", file=sys.stderr)
            print("[VidDoblaje] Iniciando modo CLI...", file=sys.stderr)
    from viddoblaje.cli import run_cli
    return run_cli(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
