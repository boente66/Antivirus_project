from PyQt5.QtCore import QObject, pyqtSignal

from services.quarantine_service import QuarantineService


class QuarantineController(QObject):

    # --------------------------------------------------
    # SINAIS
    # --------------------------------------------------

    item_added = pyqtSignal(object)
    item_removed = pyqtSignal(object)
    items_refreshed = pyqtSignal(list)
    error = pyqtSignal(str)

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------

    def __init__(self):

        super().__init__()

        self.service = QuarantineService()

        self._items = []

        # escutar eventos do serviço
        self.service.item_added.connect(self._on_service_added)

        self.refresh_items()

    # =====================================================
    # ACESSO CONTROLADO
    # =====================================================

    def get_items(self):

        return list(self._items)

    # =====================================================
    # SINCRONIZAR COM BANCO
    # =====================================================

    def refresh_items(self):

        try:

            self._items = self.service.list_items()

            self.items_refreshed.emit(self._items)

        except Exception as e:

            self.error.emit(str(e))

            self._items = []

    # =====================================================
    # ADICIONAR (vindo do scan)
    # =====================================================

    def add_from_scan(self, original_path, virus_name):

        try:

            entity = self.service.quarantine_from_scan(
                original_path,
                virus_name
            )

            # serviço já dispara sinal
            return entity

        except Exception as e:

            self.error.emit(str(e))

    # =====================================================
    # RESTAURAR
    # =====================================================

    def restore_item(self, entity):

        try:

            self.service.restore(entity)

            self._safe_remove(entity)

            self.item_removed.emit(entity)

        except Exception as e:

            self.error.emit(str(e))

    # =====================================================
    # EXCLUIR DEFINITIVAMENTE
    # =====================================================

    def delete_item(self, entity):

        try:

            self.service.delete(entity)

            self._safe_remove(entity)

            self.item_removed.emit(entity)

        except Exception as e:

            self.error.emit(str(e))

    # =====================================================
    # CALLBACK DO SERVICE
    # =====================================================

    def _on_service_added(self, entity):

        if entity not in self._items:

            self._items.insert(0, entity)

        self.item_added.emit(entity)

    # =====================================================
    # UTIL
    # =====================================================

    def _safe_remove(self, entity):
        target_id = getattr(entity, "id", None)
        target_path = getattr(entity, "quarantine_path", None)

        def is_same_item(item):
            if target_id is not None:
                return getattr(item, "id", None) == target_id

            return (
                getattr(item, "quarantine_path", None) == target_path
            )

        self._items = [

            item for item in self._items

            if not is_same_item(item)

        ]
