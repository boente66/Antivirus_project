import os
import logging
import subprocess
from pathlib import Path

import psutil

from .platform_adapter import PlatformAdapter


class LinuxAdapter(PlatformAdapter):

    _logger = logging.getLogger(__name__)

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
            for process in psutil.process_iter(attrs=["pid", "name"]):
                try:
                    info = process.info
                    name = str(info.get("name") or "").strip()
                    pid = int(info.get("pid"))
                    if not name:
                        continue
                    processes.append({
                        "pid": pid,
                        "name": name,
                    })
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess) as exc:
                    self._logger.debug("Processo indisponível durante enumeração: %s", exc)
                except (AttributeError, TypeError, ValueError) as exc:
                    self._logger.debug("Dados de processo inválidos: %s", exc)
        except (psutil.AccessDenied, psutil.NoSuchProcess) as exc:
            self._logger.warning("Enumeração de processos indisponível: %s", exc)
        except Exception as exc:
            self._logger.warning("Falha inesperada ao enumerar processos: %s", exc)
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
            "/lib64",
            "/dev",
            "/root",
            "/run",
            "/sbin",
            "/sys",
            "/proc",
            "/var"
        ]

    # --------------------------------------------------
    # Verificar privilégios admin
    # --------------------------------------------------

    def has_admin_privileges(self):

        try:
            return os.geteuid() == 0
        except Exception:
            return False

    def get_cleaner_capabilities(self):
        return {
            "supported": True,
            "message": "Limpeza segura disponível no Linux.",
        }
