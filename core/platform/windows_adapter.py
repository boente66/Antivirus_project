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
from models.firewall_contracts import (
    FirewallCapability,
    FirewallOperationResult,
    OperationStatus,
    SupportStatus,
)


class WindowsAdapter(PlatformAdapter):
    platform = "Windows"
    backend = "windows_firewall"

    def __init__(self):
        self._firewall_runner = subprocess.run
        self._firewall_which = shutil.which

    def get_os_name(self):
        return self.platform

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
        result = self.read_status("platform-status")
        if not result.succeeded:
            return "unknown"
        return "active" if result.confirmed_state.get("active") else "inactive"

    def detect_firewall_capability(self, *, which=None, runner=None, **_dependencies):
        self._firewall_which = which or shutil.which
        self._firewall_runner = runner or subprocess.run
        result = self.read_status("capability-probe")
        return FirewallCapability(
            platform=self.platform,
            backend=self.backend,
            installed=True,
            active=(
                result.confirmed_state.get("active")
                if result.succeeded else None
            ),
            readable=result.succeeded,
            writable=False,
            requires_privilege=True,
            support_status=(
                SupportStatus.READ_ONLY.value
                if result.succeeded else SupportStatus.UNAVAILABLE.value
            ),
            reason=(
                "Windows Defender Firewall validado em modo somente leitura."
                if result.succeeded
                else result.message
                or "Estado do Windows Defender Firewall indisponível."
            ),
        )

    def read_status(self, operation_id="status"):
        powershell = (
            self._firewall_which("powershell.exe")
            or self._firewall_which("powershell")
        )
        if not powershell:
            return FirewallOperationResult(
                operation_id=operation_id,
                status=OperationStatus.UNAVAILABLE.value,
                backend=self.backend,
                verified=False,
                error_code="powershell_unavailable",
                message="PowerShell não está disponível para consultar o Firewall.",
            )
        command = [
            str(powershell),
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Get-NetFirewallProfile | Select-Object -ExpandProperty Enabled",
        ]
        try:
            completed = self._firewall_runner(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return FirewallOperationResult(
                operation_id=operation_id,
                status=OperationStatus.EXECUTION_FAILED.value,
                backend=self.backend,
                verified=False,
                error_code="windows_status_failed",
                message=f"Falha ao consultar o Firewall do Windows: {exc}",
            )
        if completed.returncode != 0:
            return FirewallOperationResult(
                operation_id=operation_id,
                status=OperationStatus.EXECUTION_FAILED.value,
                backend=self.backend,
                verified=False,
                exit_code=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
                error_code="windows_status_exit_nonzero",
                message="O Windows não confirmou o estado do Firewall.",
            )
        values = [
            line.strip().lower()
            for line in (completed.stdout or "").splitlines()
            if line.strip()
        ]
        if not values or any(value not in {"true", "false"} for value in values):
            return FirewallOperationResult(
                operation_id=operation_id,
                status=OperationStatus.VERIFICATION_FAILED.value,
                backend=self.backend,
                verified=False,
                stdout=completed.stdout or "",
                error_code="windows_status_unrecognized",
                message="Resposta do Firewall do Windows não reconhecida.",
            )
        active = all(value == "true" for value in values)
        return FirewallOperationResult(
            operation_id=operation_id,
            status=OperationStatus.SUCCESS.value,
            backend=self.backend,
            confirmed_state={"active": active, "profiles": len(values)},
            verified=True,
            exit_code=completed.returncode,
            stdout=completed.stdout or "",
            message="Estado dos perfis do Windows Defender Firewall confirmado.",
        )

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
