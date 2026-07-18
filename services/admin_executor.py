# services/admin_executor.py

import sys
import json
import os
from pathlib import Path

from core.platform.platform_factory import PlatformFactory
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

        JSON de tasks é recebido pela entrada padrão.
    """

    # --------------------------------------------------
    # Segurança
    # --------------------------------------------------

    if not _is_root():

        print(
            "Erro: Este módulo deve ser executado como administrador/root.",
            file=sys.stderr
        )

        sys.exit(1)

    # --------------------------------------------------
    # Validar argumentos
    # --------------------------------------------------

    try:
        payload = sys.stdin.read()

        if not payload.strip():
            print("Erro: Nenhuma task recebida.", file=sys.stderr)
            sys.exit(1)

        tasks = json.loads(payload)

    except Exception as e:

        print(f"Erro ao decodificar JSON: {e}", file=sys.stderr)

        sys.exit(1)

    if not isinstance(tasks, list):

        print("Erro: Formato inválido de tasks.", file=sys.stderr)

        sys.exit(1)

    # --------------------------------------------------
    # Inicializar adapter
    # --------------------------------------------------

    try:

        adapter = PlatformFactory.create()

    except Exception as e:

        print(f"Erro ao inicializar PlatformAdapter: {e}", file=sys.stderr)

        sys.exit(1)

    # --------------------------------------------------
    # Criar CleanerService
    # --------------------------------------------------

    service = CleanerService(adapter)

    # --------------------------------------------------
    # Executar limpeza
    # --------------------------------------------------

    try:

        result = service.clean(

            tasks=tasks,

            target_path=str(Path.home()),

            require_admin=True,

            log_cb=None,

            progress_cb=None,

            should_stop=None

        )

        print(json.dumps(result))
        sys.exit(0 if result.get("status") != "failed" else 1)

    except Exception as e:

        print(f"Erro durante execução administrativa: {e}", file=sys.stderr)

        sys.exit(1)


if __name__ == "__main__":
    main()
