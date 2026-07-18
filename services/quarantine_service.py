# services/quarantine_service.py

from datetime import datetime
import logging
from typing import Optional
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal

from services.filesystem_service import (
    QUARANTINE_DIR,
    move_to_quarantine_single,
    safe_move_from_quarantine,
    remove_quarantined_file
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

    def __init__(
        self,
        repo: Optional[QuarantineRepository] = None,
        quarantine_dir=QUARANTINE_DIR
    ):

        super().__init__()

        self.repo = repo if repo is not None else QuarantineRepository()
        self.quarantine_dir = Path(quarantine_dir).expanduser().resolve()
        self.logger = logging.getLogger(__name__)

    # =====================================================
    # USADO PELO SCAN
    # =====================================================

    def quarantine_from_scan(self, original_path: str, virus_name: str):
        if not original_path:
            raise ValueError(
                "Adicionar à quarentena: caminho de origem não informado."
            )

        original = Path(original_path).expanduser()

        if not original.is_absolute():
            raise ValueError(
                f"Adicionar à quarentena: caminho relativo não permitido: "
                f"{original_path}"
            )

        original = original.resolve(strict=False)
        quarantine_path = move_to_quarantine_single(
            str(original),
            self.quarantine_dir
        )

        entity = QuarantineEntity(
            original_path=str(original),
            quarantine_path=quarantine_path,
            virus_name=virus_name,
            date=datetime.now().isoformat(),
            status="QUARANTINED"
        )

        try:
            self.repo.insert(entity)
        except Exception as database_error:
            try:
                safe_move_from_quarantine(
                    source=quarantine_path,
                    destination=str(original),
                    quarantine_dir=self.quarantine_dir,
                    rename_on_conflict=False
                )
            except Exception as rollback_error:
                self.logger.critical(
                    "Estado inconsistente ao adicionar arquivo à quarentena: "
                    "origem=%s quarentena=%s erro_banco=%s erro_rollback=%s",
                    original,
                    quarantine_path,
                    database_error,
                    rollback_error
                )
                raise RuntimeError(
                    "Adicionar à quarentena: registro no banco falhou e o "
                    f"rollback também falhou para '{original}'. Arquivo mantido "
                    f"em '{quarantine_path}'. Erro do banco: {database_error}. "
                    f"Erro do rollback: {rollback_error}"
                ) from database_error

            raise RuntimeError(
                "Adicionar à quarentena: registro no banco falhou; o arquivo "
                f"foi devolvido para '{original}'. Causa: {database_error}"
            ) from database_error

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
        stored = self._get_stored_entity(entity, "Restaurar quarentena")

        restored_path = safe_move_from_quarantine(
            source=stored.quarantine_path,
            destination=stored.original_path,
            quarantine_dir=self.quarantine_dir,
            rename_on_conflict=True
        )

        try:
            deleted = self.repo.delete_by_path(stored.quarantine_path)
        except Exception as database_error:
            self.logger.error(
                "Estado inconsistente após restauração: origem=%s "
                "quarentena=%s erro_banco=%s",
                restored_path,
                stored.quarantine_path,
                database_error
            )
            raise RuntimeError(
                "Restaurar quarentena: arquivo restaurado para "
                f"'{restored_path}', mas não foi possível remover o registro "
                f"do banco. Causa: {database_error}"
            ) from database_error

        if not deleted:
            raise RuntimeError(
                "Restaurar quarentena: arquivo restaurado para "
                f"'{restored_path}', mas o registro já não existia no banco."
            )

        stored.original_path = restored_path
        stored.status = "RESTORED"
        self.item_removed.emit(stored)

        return restored_path

    # =====================================================
    # EXCLUSÃO DEFINITIVA
    # =====================================================

    def delete(self, entity: QuarantineEntity):
        stored = self._get_stored_entity(entity, "Excluir quarentena")

        removed_path = remove_quarantined_file(
            stored.quarantine_path,
            self.quarantine_dir
        )

        try:
            deleted = self.repo.delete_by_path(stored.quarantine_path)
        except Exception as database_error:
            self.logger.error(
                "Estado inconsistente após exclusão definitiva: "
                "quarentena=%s erro_banco=%s",
                stored.quarantine_path,
                database_error
            )
            raise RuntimeError(
                "Excluir quarentena: arquivo removido de "
                f"'{removed_path}', mas o registro não pôde ser excluído do "
                f"banco. Causa: {database_error}"
            ) from database_error

        if not deleted:
            raise RuntimeError(
                "Excluir quarentena: arquivo removido, mas o registro já não "
                f"existia no banco: {stored.quarantine_path}"
            )

        # emitir evento
        self.item_removed.emit(stored)

        return removed_path

    def _get_stored_entity(self, entity, operation: str) -> QuarantineEntity:
        quarantine_path = getattr(entity, "quarantine_path", None)

        if not quarantine_path:
            raise ValueError(f"{operation}: item inválido ou sem caminho.")

        stored = self.repo.find_by_path(quarantine_path)

        if stored is None:
            raise FileNotFoundError(
                f"{operation}: registro não encontrado: {quarantine_path}"
            )

        return stored
