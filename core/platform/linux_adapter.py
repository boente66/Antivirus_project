import os
import subprocess
from pathlib import Path

from .platform_adapter import PlatformAdapter


class LinuxAdapter(PlatformAdapter):

    # --------------------------------------------------
    # Sistema operacional
    # --------------------------------------------------

    def get_os_name(self):
        return "Linux"

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

        try:

            result = subprocess.run(
                ["dpkg-query", "-W", "-f=${Package}\t${Version}\n"],
                capture_output=True,
                text=True,
                timeout=15
            )

            for line in result.stdout.splitlines():

                parts = line.split("\t")

                if len(parts) >= 2:

                    programs.append({
                        "name": parts[0],
                        "version": parts[1]
                    })

        except Exception:

            try:

                result = subprocess.run(
                    ["rpm", "-qa", "--qf", "%{NAME}\t%{VERSION}\n"],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                for line in result.stdout.splitlines():

                    parts = line.split("\t")

                    if len(parts) >= 2:

                        programs.append({
                            "name": parts[0],
                            "version": parts[1]
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
            home / "Videos",

            home / ".config" / "autostart",
            home / ".local" / "bin",
            home / ".local" / "share" / "applications",

            Path("/tmp"),
            Path("/var/tmp"),

            Path("/usr/bin"),
            Path("/usr/local/bin")
        ]

        return [p for p in targets if p.exists()]

    # --------------------------------------------------
    # Scan WiFi networks
    # --------------------------------------------------

    def scan_wifi_networks(self):

        networks = []

        try:

            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )

            seen = set()

            for line in result.stdout.splitlines():

                parts = line.split(":")

                if len(parts) < 3:
                    continue

                ssid = parts[0].strip()

                if not ssid or ssid in seen:
                    continue

                seen.add(ssid)

                networks.append({
                    "ssid": ssid,
                    "signal": parts[1],
                    "security": parts[2]
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

                parts = line.split(None, 1)

                if len(parts) == 2:

                    processes.append({
                        "pid": int(parts[0]),
                        "name": parts[1]
                    })

        except Exception:
            pass

        return processes

    # --------------------------------------------------
    # Firewall status
    # --------------------------------------------------

    def get_firewall_status(self):

        try:

            result = subprocess.run(
                ["ufw", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if "Status: active" in result.stdout:
                return "active"

            if "Status: inactive" in result.stdout:
                return "inactive"

        except Exception:
            pass

        return "unknown"

    # --------------------------------------------------
    # Usuários do sistema
    # --------------------------------------------------

    def get_system_users(self):

        users = []

        try:

            with open("/etc/passwd") as f:

                for line in f:

                    parts = line.split(":")

                    if len(parts) >= 3:

                        uid = int(parts[2])

                        if uid >= 1000:
                            users.append(parts[0])

        except Exception:
            pass

        return users

    # --------------------------------------------------
    # Diretórios temporários
    # --------------------------------------------------

    def get_temp_directories(self):

        return [
            "/tmp",
            "/var/tmp"
        ]

    # --------------------------------------------------
    # Diretórios críticos do sistema
    # --------------------------------------------------

    def get_system_directories(self):

        return [
            "/",
            "/usr",
            "/bin",
            "/boot",
            "/etc",
            "/lib",
            "/sbin",
            "/sys",
            "/proc"
        ]

    # --------------------------------------------------
    # Verificar privilégios admin
    # --------------------------------------------------

    def has_admin_privileges(self):

        try:
            return os.geteuid() == 0
        except Exception:
            return False