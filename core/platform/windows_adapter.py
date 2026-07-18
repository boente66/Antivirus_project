import os
import string
import subprocess

import ctypes
import shutil
from pathlib import Path

# winreg is only available on Windows; import safely so the module can be imported on other platforms
try:
    import winreg
except Exception:
    winreg = None

from .platform_adapter import PlatformAdapter


class WindowsAdapter(PlatformAdapter):
    def get_os_name(self):
        import platform
        system = platform.system()
        # if on Windows, ensure winreg is available; otherwise just return the platform name
        if system == "Windows" and winreg is not None:
            return "Windows"
        return system

    # --------------------------------------------------

    def get_home_directory(self):
        return os.path.expanduser("~")

    # --------------------------------------------------
    # Volumes (C:, D:, etc)
    # --------------------------------------------------

    def get_volumes(self):
        volumes = []

        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"

            if os.path.exists(drive):
                try:
                    total, used, free = shutil.disk_usage(drive)
                    percent = int((used / total) * 100) if total else 0
                    volumes.append({
                        "device": drive,
                        "mountpoint": drive,
                        "filesystem": "NTFS",
                        "total": total,
                        "used": used,
                        "free": free,
                        "percent": percent
                    })
                except Exception:
                    # If we can't read usage, provide defaults
                    volumes.append({
                        "device": drive,
                        "mountpoint": drive,
                        "filesystem": "NTFS",
                        "total": 0,
                        "used": 0,
                        "free": 0,
                        "percent": 0
                    })

        # --------------------------------------------------
        # Programas instalados
        # --------------------------------------------------

    def get_installed_programs(self):
        # If winreg is not available (non-Windows), return empty list
        if winreg is None:
            return []

        programs = []
        seen = set()

        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for hive, path in registry_paths:
            try:
                key = winreg.OpenKey(hive, path)
            except Exception:
                continue

            try:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    subkey_name = winreg.EnumKey(key, i)
                    try:
                        subkey = winreg.OpenKey(key, subkey_name)
                        try:
                            name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        except Exception:
                            continue

                        if name in seen:
                            continue

                        seen.add(name)

                        try:
                            version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                        except Exception:
                            version = "unknown"

                        programs.append({
                            "name": name,
                            "version": version
                        })
                    except Exception:
                        # ignore inaccessible subkeys or missing values
                        pass
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
            Path(os.getenv("APPDATA", "")),
            Path(os.getenv("LOCALAPPDATA", "")),
            Path(os.getenv("PROGRAMDATA", "")),
            home / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup",
            Path(os.getenv("TEMP", "")),
            Path(os.getenv("TMP", "")),
            Path("C:/Program Files"),
            Path("C:/Program Files (x86)")
        ]

        return [p for p in targets if p and p.exists()]

    # --------------------------------------------------
    # WiFi Networks
    # --------------------------------------------------

    def scan_wifi_networks(self):
        networks = []
        seen = set()

        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks"],
                capture_output=True,
                text=True,
                timeout=10
            )

            for line in result.stdout.splitlines():
                if "SSID" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        ssid = parts[1].strip()
                        if ssid and ssid not in seen:
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
                ["tasklist"],
                capture_output=True,
                text=True,
                timeout=10
            )

            lines = result.stdout.splitlines()[3:]

            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        processes.append({
                            "name": parts[0],
                            "pid": int(parts[1])
                        })
                    except Exception:
                        continue
        except Exception:
            pass

        return processes

    # --------------------------------------------------
    # Firewall status
    # --------------------------------------------------

    def get_firewall_status(self):
        try:
            result = subprocess.run(
                ["netsh", "advfirewall", "show", "allprofiles"],
                capture_output=True,
                text=True,
                timeout=10
            )

            text = result.stdout.upper()

            if "STATE ON" in text:
                return "active"

            if "STATE OFF" in text:
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
            result = subprocess.run(
                ["net", "user"],
                capture_output=True,
                text=True,
                timeout=10
            )

            lines = result.stdout.splitlines()[4:-2]

            for line in lines:
                for user in line.split():
                    users.append(user)
        except Exception:
            pass

        return users

    # --------------------------------------------------
    # Diretórios temporários
    # --------------------------------------------------

    def get_temp_directories(self):
        return [
            os.getenv("TEMP"),
            os.getenv("TMP"),
            "C:\\Windows\\Temp"
        ]

    # --------------------------------------------------
    # Diretórios críticos do sistema
    # --------------------------------------------------

    def get_system_directories(self):
        return [
            "C:\\Windows",
            "C:\\Windows\\System32",
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            "C:\\ProgramData"
        ]

    # --------------------------------------------------
    # Verificar privilégios admin
    # --------------------------------------------------

    def has_admin_privileges(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def get_cleaner_capabilities(self):
        return {
            "supported": False,
            "message": (
                "Cleaner no Windows está desabilitado até a validação completa "
                "de lixeira, UAC e caminhos administrativos."
            ),
        }
