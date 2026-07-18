import subprocess
import shutil
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
                    name = p.get("name", "")

                else:
                    name = str(p)

                name = name.strip()

                if name:
                    normalized.append(name)

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

        program_name = program_name.strip()

        if not self._is_safe_program_name(program_name):
            return False, "Nome do programa contém caracteres inválidos."

        installed_name = self._find_installed_name(program_name)

        if not installed_name:
            return False, "Programa não encontrado na lista de instalados."

        if self.os_type == "Linux":
            return self._uninstall_linux(installed_name, password, progress_cb)

        if self.os_type == "Windows":
            return self._uninstall_windows(installed_name, progress_cb)

        if self.os_type == "macOS":
            return self._uninstall_mac(installed_name, password, progress_cb)

        return False, "Sistema operacional não suportado."

    def _is_safe_program_name(self, program_name: str) -> bool:
        if not program_name:
            return False

        if any(ch in program_name for ch in ("/", "\\", "\x00")):
            return False

        return not any(ord(ch) < 32 for ch in program_name)

    def _find_installed_name(self, program_name: str) -> str | None:
        installed = self.list_installed()
        requested = program_name.casefold()

        for name in installed:
            if name.casefold() == requested:
                return name

        return None

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
            if shutil.which(manager[0]) is None:
                continue

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
                "-NoProfile",
                "-Command",
                "$name = $args[0]; "
                "Get-CimInstance -ClassName Win32_Product "
                "| Where-Object { $_.Name -eq $name } "
                "| ForEach-Object { $_.Uninstall() }",
                program
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                return False, result.stderr.strip() or result.stdout.strip()

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

        try:
            app_path.resolve().relative_to(Path("/Applications").resolve())
        except ValueError:
            return False, "Caminho do aplicativo inválido."

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
