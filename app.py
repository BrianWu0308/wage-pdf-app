from pathlib import Path
import sys
import tkinter as tk

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from wage_app.ui import WageApp


def main() -> None:
    root = tk.Tk()
    WageApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
