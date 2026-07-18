import os
import subprocess
from pathlib import Path

from .platform_adapter import PlatformAdapter


class MacAdapter(PlatformAdapter):

    # --------------------------------------------------
    # Sistema operacional
    # --------------------------------------------------

    def get_os_name(self):
        return "macOS"

    # --------------------------------------------------
    # Diretório do usuário
    # --------------------------------------------------

    def get_home_directory(self):
        return os.path.expanduser("~")

    # --------------------------------------------------
    # Volumes do sistema
    # --------------------------------------------------

    def get_volumes(self):

        volumes = []

        try:

            result = subprocess.run(
                ["df", "-P"],
                capture_output=True,
                text=True,
                timeout=10
            )

            lines = result.stdout.splitlines()[1:]

            for line in lines:

                parts = line.split()

                if len(parts) >= 6:

                    volumes.append({
                        "device": parts[0],
                        "mountpoint": parts[5],
                        "filesystem": parts[1]
                    })

        except Exception:
            pass

        return volumes

    # --------------------------------------------------
    # Programas instalados
    # --------------------------------------------------

    def get_installed_programs(self):

        programs = []
        seen = set()

        paths = [
            Path("/Applications"),
            Path.home() / "Applications"
        ]

        try:

            for applications_path in paths:

                if not applications_path.exists():
                    continue

                for app in os.listdir(applications_path):

                    if not app.endswith(".app"):
                        continue

                    name = app.replace(".app", "")

                    if name in seen:
                        continue

                    seen.add(name)

                    programs.append({
                        "name": name,
                        "path": str(applications_path / app)
                    })

        except Exception:
            pass

        return programs

    # --------------------------------------------------
    # Diretórios inteligentes para scan
    # --------------------------------------------------

    def get_smart_scan_targets(self):

        home = Path.home()

        targets = [

            home / "Downloads",
            home / "Desktop",
            home / "Documents",
            home / "Pictures",
            home / "Movies",

            home / "Library" / "LaunchAgents",
            home / "Library" / "Application Support",

            Path("/tmp"),
            Path("/var/tmp"),

            Path("/Applications"),
            home / "Applications"
        ]

        return [p for p in targets if p.exists()]

    # --------------------------------------------------
    # Redes WiFi
    # --------------------------------------------------

    def scan_wifi_networks(self):

        networks = []

        try:

            result = subprocess.run(
                [
                    "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport",
                    "-s"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            lines = result.stdout.splitlines()[1:]

            seen = set()

            for line in lines:

                parts = line.split()

                if not parts:
                    continue

                ssid = parts[0]

                if ssid in seen:
                    continue

                seen.add(ssid)

                networks.append({
                    "ssid": ssid
                })

        except Exception:
            pass

        return networks

    # --------------------------------------------------
    # Processos em execução
    # --------------------------------------------------

    def get_running_processes(self):

        processes = []

        try:

            result = subprocess.run(
                ["ps", "-eo", "pid,comm"],
                capture_output=True,
                text=True,
                timeout=10
            )

            lines = result.stdout.splitlines()[1:]

            for line in lines:
                parts = line.strip().split(None, 1)
                if not parts:
                    continue

                pid = parts[0]
                command = parts[1] if len(parts) > 1 else ""

                processes.append({
                    "pid": pid,
                    "command": command
                })

        except Exception:
            pass

        return processes

    def get_firewall_status(self):
        return "unknown"

    def get_system_users(self):
        return []

    def get_temp_directories(self):
        return ["/tmp", "/var/tmp"]

    def get_system_directories(self):
        return [
            "/", "/System", "/usr", "/bin", "/sbin", "/etc",
            "/var", "/dev", "/private", "/Library"
        ]

    def has_admin_privileges(self):
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False

    def get_cleaner_capabilities(self):
        return {
            "supported": False,
            "message": (
                "Cleaner no macOS está desabilitado até a validação completa "
                "de lixeira e autorização administrativa."
            ),
        }
