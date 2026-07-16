# services/cleaner_service.py

import os
import shutil
from pathlib import Path
from datetime import datetime

from database.entity.clean_entity import CleanEntity
from database.repositories.clean_history_repository import CleanHistoryRepository


class CleanerService:

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, adapter, repository=None):

        if adapter is None:
            raise ValueError("PlatformAdapter não informado")

        self.adapter = adapter

        self.repository = repository or CleanHistoryRepository()

    # =====================================================
    # 🔎 ANÁLISE (não remove nada)
    # =====================================================

    def analyze(
        self,
        *,
        tasks,
        target_path,
        log_cb=None,
        progress_cb=None,
        should_stop=None
    ):

        total_size = 0
        total_items = 0

        total = sum(len(t.get("paths", [])) for t in tasks) or 1
        processed = 0

        base_path = Path(target_path).resolve()

        for task in tasks:

            for p in task.get("paths", []):

                if should_stop and should_stop():
                    return total_items, total_size

                processed += 1

                if progress_cb:
                    progress_cb(int((processed / total) * 100))

                try:

                    path = Path(p).expanduser().resolve()

                    if not self._is_safe_path(path, base_path):
                        continue

                    if not path.exists():
                        continue

                    size = self._calculate_size(path)

                    total_size += size

                    if size > 0:
                        total_items += 1

                    if log_cb:
                        log_cb(f"Detectado: {path}")

                except Exception as e:

                    if log_cb:
                        log_cb(f"Erro em {p}: {e}")

        return total_items, total_size

    # =====================================================
    # 🧹 LIMPEZA REAL
    # =====================================================

    def clean(
        self,
        *,
        tasks,
        target_path,
        require_admin=False,
        log_cb=None,
        progress_cb=None,
        should_stop=None
    ):

        if require_admin and not self._has_admin():
            raise PermissionError("Permissão de administrador necessária")

        removed = 0
        freed = 0
        logs = []

        total = sum(len(t.get("paths", [])) for t in tasks) or 1
        processed = 0

        base_path = Path(target_path).resolve()

        for task in tasks:

            action = task.get("action")

            for p in task.get("paths", []):

                if should_stop and should_stop():
                    return removed, freed

                processed += 1

                if progress_cb:
                    progress_cb(int((processed / total) * 100))

                try:

                    path = Path(p).expanduser().resolve()

                    if not self._is_safe_path(path, base_path):

                        msg = f"Bloqueado por segurança: {path}"

                        logs.append(msg)

                        if log_cb:
                            log_cb(msg)

                        continue

                    if not path.exists():
                        continue

                    size = self._calculate_size(path)

                    if action == "delete":

                        if path.is_file():

                            path.unlink(missing_ok=True)

                        elif path.is_dir():

                            shutil.rmtree(path, ignore_errors=True)

                    removed += 1
                    freed += size

                    msg = f"Removido: {path}"

                    logs.append(msg)

                    if log_cb:
                        log_cb(msg)

                except Exception as e:

                    msg = f"Erro em {p}: {e}"

                    logs.append(msg)

                    if log_cb:
                        log_cb(msg)

        # -------------------------------------------------
        # Persistência
        # -------------------------------------------------

        entity = CleanEntity(

            user=os.getenv("USER", os.getenv("USERNAME", "unknown")),

            timestamp=datetime.now().isoformat(),

            total_items=removed,

            total_size=freed,

            permanent=require_admin,

            details="\n".join(logs),
        )

        self.repository.insert(entity)

        return removed, freed

    # =====================================================
    # 🔐 ADMIN CHECK
    # =====================================================

    def _has_admin(self):

        if hasattr(self.adapter, "has_admin_privileges"):
            return self.adapter.has_admin_privileges()

        return False

    # =====================================================
    # 🔐 PROTEÇÃO DE CAMINHO
    # =====================================================

    def _is_safe_path(self, path: Path, base_path: Path):

        try:

            if path == Path(path.anchor):
                return False

            if hasattr(self.adapter, "get_system_directories"):

                critical = self.adapter.get_system_directories()

                for c in critical:

                    critical_path = Path(c).expanduser().resolve()

                    if self._is_same_or_child(path, critical_path):
                        return False

        except Exception:
            pass

        if self._is_same_or_child(path, base_path):
            return True

        if hasattr(self.adapter, "get_temp_directories"):

            for temp in self.adapter.get_temp_directories():

                if not temp:
                    continue

                temp_path = Path(temp).expanduser().resolve()

                if self._is_same_or_child(path, temp_path):
                    return True

        return False

    def _is_same_or_child(self, path: Path, parent: Path):
        if path == parent:
            return True

        if parent == Path(parent.anchor):
            return False

        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    # =====================================================
    # 📦 CALCULAR TAMANHO
    # =====================================================

    def _calculate_size(self, path: Path):

        size = 0

        try:

            if path.is_file():

                return path.stat().st_size

            if path.is_dir():

                for p in path.rglob("*"):

                    try:

                        if p.is_file():

                            size += p.stat().st_size

                    except Exception:
                        continue

        except Exception:
            pass

        return size
