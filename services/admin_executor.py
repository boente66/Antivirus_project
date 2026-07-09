# services/admin_executor.py

import sys
import json
import os
from pathlib import Path

from system.system_inspector import SystemInspector
from services.cleaner_service import CleanerService


def _is_root():
    """
    Verifica se está rodando como administrador/root.
    """

    try:
        return os.geteuid() == 0
    except AttributeError:
        # Windows fallback
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False


def main():
    """
    Executor administrativo.

    Chamado via:

        pkexec python -m services.admin_executor '<json_tasks>'
    """

    # --------------------------------------------------
    # Segurança
    # --------------------------------------------------

    if not _is_root():

        print("Erro: Este módulo deve ser executado como administrador/root.")

        sys.exit(1)

    # --------------------------------------------------
    # Validar argumentos
    # --------------------------------------------------

    if len(sys.argv) < 2:

        print("Erro: Nenhuma task recebida.")

        sys.exit(1)

    try:

        tasks = json.loads(sys.argv[1])

    except Exception as e:

        print(f"Erro ao decodificar JSON: {e}")

        sys.exit(1)

    if not isinstance(tasks, list):

        print("Erro: Formato inválido de tasks.")

        sys.exit(1)

    # --------------------------------------------------
    # Inicializar adapter
    # --------------------------------------------------

    try:

        inspector = SystemInspector()

        adapter = inspector.get_platform_adapter()

    except Exception as e:

        print(f"Erro ao inicializar PlatformAdapter: {e}")

        sys.exit(1)

    # --------------------------------------------------
    # Criar CleanerService
    # --------------------------------------------------

    service = CleanerService(adapter)

    # --------------------------------------------------
    # Executar limpeza
    # --------------------------------------------------

    try:

        removed, freed = service.clean(

            tasks=tasks,

            target_path=str(Path.home()),

            require_admin=True,

            log_cb=None,

            progress_cb=None,

            should_stop=None

        )

        freed_mb = freed / 1024 / 1024 if freed else 0.0

        result = {
            "removed_items": removed,
            "freed_bytes": freed,
            "freed_mb": round(freed_mb, 2)
        }

        print(json.dumps(result))

        sys.exit(0)

    except Exception as e:

        print(f"Erro durante execução administrativa: {e}")

        sys.exit(1)


if __name__ == "__main__":
    main()