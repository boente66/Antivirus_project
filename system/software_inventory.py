import platform
import subprocess
import os


class SoftwareInventory:
    """
    Responsável por listar programas instalados no sistema.
    Funciona em Linux, Windows e macOS.
    """

    # --------------------------------------------------
    # método principal
    # --------------------------------------------------

    def get_installed_programs(self):

        system = platform.system()

        if system == "Linux":
            return self._get_linux_programs()

        if system == "Windows":
            return self._get_windows_programs()

        if system == "Darwin":
            return self._get_macos_programs()

        return []

    # --------------------------------------------------
    # LINUX
    # --------------------------------------------------

    def _get_linux_programs(self):

        programs = []

        try:

            result = subprocess.run(
                ["dpkg", "-l"],
                capture_output=True,
                text=True
            )

            lines = result.stdout.splitlines()[5:]

            for line in lines:

                parts = line.split()

                if len(parts) > 1:

                    programs.append({
                        "name": parts[1],
                        "version": parts[2] if len(parts) > 2 else ""
                    })

        except Exception:
            pass

        return programs

    # --------------------------------------------------
    # WINDOWS
    # --------------------------------------------------

    def _get_windows_programs(self):

        programs = []

        try:

            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
            )

            for i in range(winreg.QueryInfoKey(key)[0]):

                subkey_name = winreg.EnumKey(key, i)

                subkey = winreg.OpenKey(key, subkey_name)

                try:

                    name = winreg.QueryValueEx(
                        subkey,
                        "DisplayName"
                    )[0]

                    programs.append({
                        "name": name
                    })

                except Exception:
                    pass

        except Exception:
            pass

        return programs

    # --------------------------------------------------
    # macOS
    # --------------------------------------------------

    def _get_macos_programs(self):

        programs = []

        applications_path = "/Applications"

        try:

            for app in os.listdir(applications_path):

                if app.endswith(".app"):

                    programs.append({
                        "name": app.replace(".app", "")
                    })

        except Exception:
            pass

        return programs