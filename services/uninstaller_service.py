import subprocess
from typing import Callable, Tuple, List
from pathlib import Path
from core.platform.platform_factory import PlatformFactory



class UninstallerService:

    def __init__(self):

        self.platform = PlatformFactory.get_adapter()
        self.os_type = self.platform.get_os_name()

    # --------------------------------------------------
    # LISTAGEM
    # --------------------------------------------------

    def list_installed(self) -> List[str]:

        try:

            programs = self.platform.get_installed_programs()

            # adapter pode retornar dict ou string
            normalized = []

            for p in programs:

                if isinstance(p, dict):
                    normalized.append(p.get("name", ""))

                else:
                    normalized.append(str(p))

            return sorted(normalized)

        except Exception:
            return []

    # --------------------------------------------------
    # DESINSTALAÇÃO
    # --------------------------------------------------

    def uninstall(
        self,
        program_name: str,
        password: str | None = None,
        progress_cb: Callable[[int, str], None] | None = None
    ) -> Tuple[bool, str]:

        if not program_name:
            return False, "Nome do programa inválido."

        if self.os_type == "Linux":
            return self._uninstall_linux(program_name, password, progress_cb)

        if self.os_type == "Windows":
            return self._uninstall_windows(program_name, progress_cb)

        if self.os_type == "macOS":
            return self._uninstall_mac(program_name, password, progress_cb)

        return False, "Sistema operacional não suportado."

    # --------------------------------------------------
    # LINUX
    # --------------------------------------------------

    def _uninstall_linux(self, program, password, progress_cb):

        if not password:
            return False, "Senha de administrador não fornecida."

        managers = [

            ["apt-get", "remove", "--purge", "-y", program],
            ["dnf", "remove", "-y", program],
            ["pacman", "-Rns", program]

        ]

        for manager in managers:

            cmd = ["sudo", "-S"] + manager

            success, msg = self._run_sudo(cmd, password, progress_cb)

            if success:
                return True, msg

        return False, "Gerenciador de pacotes não suportado."

    # --------------------------------------------------
    # WINDOWS
    # --------------------------------------------------

    def _uninstall_windows(self, program, progress_cb):

        try:

            if progress_cb:
                progress_cb(20, "Iniciando desinstalação...")

            cmd = [
                "powershell",
                "-Command",
                f"Get-WmiObject -Class Win32_Product "
                f"| Where-Object {{$_.Name -eq '{program}'}} "
                "| ForEach-Object {{$_.Uninstall()}}"
            ]

            subprocess.check_call(cmd)

            if progress_cb:
                progress_cb(100, "Desinstalação concluída.")

            return True, f"{program} removido com sucesso."

        except Exception as e:
            return False, str(e)

    # --------------------------------------------------
    # MAC
    # --------------------------------------------------

    def _uninstall_mac(self, program, password, progress_cb):

        if not password:
            return False, "Senha de administrador não fornecida."

        app_path = Path("/Applications") / f"{program}.app"

        if not app_path.exists():
            return False, "Aplicativo não encontrado."

        cmd = ["sudo", "-S", "rm", "-rf", str(app_path)]

        return self._run_sudo(cmd, password, progress_cb)

    # --------------------------------------------------
    # EXECUÇÃO SUDO
    # --------------------------------------------------

    def _run_sudo(self, command, password, progress_cb):

        try:

            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if progress_cb:
                progress_cb(30, "Executando comando...")

            stdout, stderr = process.communicate(password + "\n")

            if process.returncode == 0:

                if progress_cb:
                    progress_cb(100, "Desinstalação concluída.")

                return True, "Operação concluída com sucesso."

            return False, stderr.strip()

        except Exception as e:
            return False, str(e)