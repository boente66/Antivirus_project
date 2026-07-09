import os
from PyQt5.QtGui import QIcon

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ICON_DIR = os.path.join(BASE_DIR, "resources", "icons")


def get_icon(name: str) -> QIcon:

    path = os.path.join(ICON_DIR, f"{name}.svg")

    if os.path.exists(path):
        return QIcon(path)

    print(f"[IconLoader] Ícone não encontrado: {path}")

    return QIcon()