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

    def __init__(self, service=None):

        super().__init__()

        self.service = service or QuarantineService()

        self._items = []

        # escutar eventos do serviço
        self.service.item_added.connect(self._on_service_added)
        self.service.item_removed.connect(self._on_service_removed)

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
            self.error.emit(f"Listar quarentena falhou: {e}")

            self._items = []

    # =====================================================
    # ADICIONAR (vindo do scan)
    # =====================================================

    def add_from_scan(self, original_path, virus_name):

        if not original_path:
            self.error.emit(
                "Adicionar à quarentena: caminho de origem não informado."
            )
            return None

        try:

            entity = self.service.quarantine_from_scan(
                original_path,
                virus_name
            )

            # serviço já dispara sinal
            return entity

        except Exception as e:
            self.error.emit(
                f"Adicionar à quarentena falhou para '{original_path}': {e}"
            )
            return None

    # =====================================================
    # RESTAURAR
    # =====================================================

    def restore_item(self, entity):

        if entity is None:
            self.error.emit("Restaurar quarentena: nenhum item selecionado.")
            return None

        try:

            restored_path = self.service.restore(entity)
            self.refresh_items()
            return restored_path

        except Exception as e:

            self.error.emit(f"Restaurar quarentena falhou: {e}")
            return None

    # =====================================================
    # EXCLUIR DEFINITIVAMENTE
    # =====================================================

    def delete_item(self, entity, confirmed=False):

        if entity is None:
            self.error.emit("Excluir quarentena: nenhum item selecionado.")
            return False

        if not confirmed:
            self.error.emit(
                "Excluir quarentena: confirmação explícita obrigatória."
            )
            return False

        try:

            self.service.delete(entity)
            self.refresh_items()
            return True

        except Exception as e:

            self.error.emit(f"Excluir quarentena falhou: {e}")
            return False

    # =====================================================
    # CALLBACK DO SERVICE
    # =====================================================

    def _on_service_added(self, entity):

        if entity not in self._items:

            self._items.insert(0, entity)

        self.item_added.emit(entity)

    def _on_service_removed(self, entity):

        self._safe_remove(entity)
        self.item_removed.emit(entity)

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
