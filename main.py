import argparse
import importlib
import json
import platform
import shutil
import sys
import traceback
from pathlib import Path

from utils.app_metadata import APP_NAME, APP_VERSION


def _build_parser():
    parser = argparse.ArgumentParser(prog="antivirus-project")
    parser.add_argument(
        "--version",
        action="version",
        version=f"{APP_NAME} {APP_VERSION}",
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="verifica a integridade do pacote sem abrir a interface",
    )
    return parser


def _diagnose():
    base_dir = Path(__file__).resolve().parent
    required_modules = ("PyQt5", "psutil", "pyclamd", "watchdog")
    imports = {}
    for module_name in required_modules:
        try:
            importlib.import_module(module_name)
            imports[module_name] = True
        except Exception as exc:
            imports[module_name] = f"indisponível: {exc}"

    resource_dir = base_dir / "resources" / "icons"
    required_icons = ("shield.svg", "firewall.svg", "scan.svg")
    resources = {
        icon: (resource_dir / icon).is_file()
        for icon in required_icons
    }
    integrations = {
        executable: bool(shutil.which(executable))
        for executable in ("clamdscan", "clamd", "ufw", "pkexec")
    }
    critical_ok = all(value is True for value in imports.values()) and all(
        resources.values()
    )
    report = {
        "application": APP_NAME,
        "version": APP_VERSION,
        "platform": platform.platform(),
        "package_integrity": critical_ok,
        "python_modules": imports,
        "resources": resources,
        "optional_system_integrations": integrations,
        "note": (
            "Integrações ausentes geram aviso; o instalador não ativa "
            "serviços nem modifica o Firewall automaticamente."
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if critical_ok else 1


def main(argv=None):
    arguments = _build_parser().parse_args(argv)
    if arguments.diagnose:
        return _diagnose()

    try:
        from PyQt5.QtWidgets import QApplication
        from views.main_view import MainView
        from views.theme import APP_STYLESHEET

        app = QApplication(sys.argv if argv is None else [APP_NAME, *argv])
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName("AntivirusProject")
        app.setStyle("Fusion")
        app.setStyleSheet(APP_STYLESHEET)

        view = MainView()
        view.show()
        return app.exec()
    except Exception:
        print("Erro ao iniciar a aplicação:", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
