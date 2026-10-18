"""
Main entrypoint for SubFynn - AI Thai Subtitle Generator.
Launches the Glassmorphism Desktop Application.
"""

import sys
import os

# Ensure stdout and stderr exist (in windowed/frozen mode they may be None)
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass

# Ensure console supports UTF-8 on Windows Thai codepage (cp874)
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    if "--web" in sys.argv or "--server" in sys.argv:
        from app import start_server
        port = 5000
        for i, a in enumerate(sys.argv):
            if a == "--port" and i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit():
                port = int(sys.argv[i + 1])
        start_server(port=port, open_browser=True)
        return

    from gui import ThaiSubtitleApp
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    initial_video = args[0] if args else None
    app = ThaiSubtitleApp(initial_video=initial_video)
    app.mainloop()


if __name__ == "__main__":
    main()
