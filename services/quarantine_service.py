# services/quarantine_service.py

from datetime import datetime
from typing import Optional
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal

from services.filesystem_service import (
    safe_move_to_quarantine,
    safe_move_from_quarantine,
    safe_remove
)

from database.repositories.quarantine_repository import QuarantineRepository
from database.entity.quarantine_entity import QuarantineEntity


class QuarantineService(QObject):

    # sinais
    item_added = pyqtSignal(object)
    item_removed = pyqtSignal(object)

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, repo: Optional[QuarantineRepository] = None):

        super().__init__()

        self.repo = repo if repo is not None else QuarantineRepository()

    # =====================================================
    # USADO PELO SCAN
    # =====================================================

    def quarantine_from_scan(self, original_path: str, virus_name: str):

        moved = safe_move_to_quarantine([original_path])

        if not moved:
            raise RuntimeError(
                "Falha ao mover arquivo para quarentena."
            )

        quarantine_path = moved[0]

        entity = QuarantineEntity(
            original_path=original_path,
            quarantine_path=quarantine_path,
            virus_name=virus_name,
            date=datetime.now().isoformat(),
            status="QUARANTINED"
        )

        self.repo.insert(entity)

        # notificar UI
        self.item_added.emit(entity)

        return entity

    # =====================================================
    # LISTAGEM
    # =====================================================

    def list_items(self):

        return self.repo.list_all()

    # =====================================================
    # RESTAURAR
    # =====================================================

    def restore(self, entity: QuarantineEntity):

        quarantine_path = Path(entity.quarantine_path)
        original_path = Path(entity.original_path)

        if not quarantine_path.exists():

            raise FileNotFoundError(
                "Arquivo em quarentena não encontrado."
            )

        restored = safe_move_from_quarantine(
            source=str(quarantine_path),
            destination=str(original_path)
        )

        if not restored:

            raise RuntimeError(
                "Falha ao restaurar arquivo."
            )

        self.repo.update_status(
            entity.quarantine_path,
            "RESTORED"
        )

    # =====================================================
    # EXCLUSÃO DEFINITIVA
    # =====================================================

    def delete(self, entity: QuarantineEntity):

        quarantine_path = Path(entity.quarantine_path)

        if quarantine_path.exists():

            safe_remove([entity.quarantine_path])

        self.repo.delete(entity.quarantine_path)

        # emitir evento
        self.item_removed.emit(entity)