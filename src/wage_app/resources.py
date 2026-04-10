from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resource_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
    return base / relative_path


def get_font_path(filename: str) -> Path:
    return resource_path(f"assets/fonts/{filename}")
