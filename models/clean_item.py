
from dataclasses import dataclass
from typing import Optional

@dataclass
class CleanItem:
    path: str
    size: int = 0
    category: str = ""
    safe: bool = True
    reason: Optional[str] = None
    selected: bool = True  # se o usuário marcou para limpeza