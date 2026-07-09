from PyQt5.QtCore import QObject
import os
import platform
import subprocess
import time

from clamav.clamav_client import ClamAVClient


class ClamAVService(QObject):

    # ======================================================
    # INIT
    # ======================================================

    def __init__(self):

        super().__init__()

        self.client = ClamAVClient()

        self.os_type = platform.system()

        # caminho padrão do banco
        self.db_path = "/var/lib/clamav"

    # ======================================================
    # INSTALAÇÃO
    # ======================================================

    def is_installed(self):

        if self.os_type == "Linux":
            cmd = ["which", "clamscan"]

        elif self.os_type == "Windows":
            cmd = ["where", "clamscan"]

        elif self.os_type == "Darwin":
            cmd = ["which", "clamscan"]

        else:
            return False

        try:

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=5
            )

            return result.returncode == 0

        except Exception:

            return False

    # ======================================================
    # STATUS DO DAEMON
    # ======================================================

    def get_status(self):

        if self.os_type != "Linux":
            return "unsupported"

        try:

            result = subprocess.run(
                ["systemctl", "is-active", "clamav-daemon"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.stdout.strip() == "active":
                return "running"

            return "stopped"

        except Exception:

            return "unknown"

    # ======================================================
    # CONEXÃO
    # ======================================================

    def connect_local(self):

        if self.is_connected():
            return True

        self.client.connect_local()

        return True

    def connect_network(self, host="127.0.0.1", port=3310):

        if self.is_connected():
            return True

        self.client.connect_server(host, port)

        return True

    def auto_connect(self):

        if self.is_connected():
            return True

        try:

            self.connect_local()

            return True

        except Exception:
            pass

        try:

            self.connect_network()

            return True

        except Exception:

            return False

    def disconnect(self):

        try:
            self.client.disconnect()
        except Exception:
            pass

    def is_connected(self):

        try:
            return self.client.is_alive()
        except Exception:
            return False

    # ======================================================
    # SCAN
    # ======================================================

    def scan_file(self, file_path):

        if not os.path.exists(file_path):

            raise FileNotFoundError(
                "Arquivo não encontrado"
            )

        if not os.path.isfile(file_path):

            raise RuntimeError(
                "Caminho informado não é um arquivo"
            )

        if not os.access(file_path, os.R_OK):

            raise PermissionError(
                "Sem permissão para ler o arquivo"
            )

        if not self.is_connected():

            raise RuntimeError(
                "ClamAV não conectado"
            )

        return self.client.scan_file(file_path)

    # ======================================================
    # DETECÇÃO
    # ======================================================

    def is_infected(self, file_path):

        result = self.scan_file(file_path)

        if not result:
            return False

        try:

            status = list(result.values())[0][0]

            return status == "FOUND"

        except Exception:

            return False

    # ======================================================
    # BANCO DE VÍRUS
    # ======================================================

    def database_files(self):

        files = [
            "main.cvd",
            "daily.cvd",
            "bytecode.cvd",
            "main.cld",
            "daily.cld",
            "bytecode.cld"
        ]

        existing = []

        for f in files:

            path = os.path.join(self.db_path, f)

            if os.path.exists(path):
                existing.append(path)

        return existing

    # ------------------------------------------------------

    def database_last_update(self):

        files = self.database_files()

        if not files:
            return None

        newest = max(os.path.getmtime(f) for f in files)

        return newest

    # ------------------------------------------------------

    def database_age_days(self):

        last = self.database_last_update()

        if last is None:
            return None

        now = time.time()

        age_seconds = now - last

        return age_seconds / 86400

    # ------------------------------------------------------

    def database_is_outdated(self, max_days=3):

        age = self.database_age_days()

        if age is None:
            return True

        return age > max_days

    # ======================================================
    # ATUALIZAÇÃO
    # ======================================================

    def update_database(self):

        if self.os_type != "Linux":

            raise RuntimeError(
                "Atualização automática suportada apenas em Linux"
            )

        try:

            result = subprocess.run(
                ["freshclam"],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:

                raise RuntimeError(
                    result.stderr.strip()
                )

            return True

        except Exception as e:

            raise RuntimeError(
                f"Falha ao atualizar banco de vírus: {e}"
            )

    # ======================================================
    # CHECK COMPLETO DO ENGINE
    # ======================================================

    def ensure_engine_ready(self):

        if not self.is_installed():

            raise RuntimeError(
                "ClamAV não está instalado no sistema"
            )

        status = self.get_status()

        if status != "running" and self.os_type == "Linux":

            try:

                subprocess.run(
                    ["systemctl", "start", "clamav-daemon"],
                    capture_output=True,
                    timeout=10
                )

            except Exception:

                raise RuntimeError(
                    "Falha ao iniciar daemon ClamAV"
                )

        if not self.is_connected():

            if not self.auto_connect():

                raise RuntimeError(
                    "Falha ao conectar ao engine ClamAV"
                )

        if self.database_is_outdated():

            try:
                self.update_database()
            except Exception:
                pass

        return True
