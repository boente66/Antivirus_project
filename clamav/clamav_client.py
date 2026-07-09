import pyclamd
import platform


class ClamAVClient:

    def __init__(self, server=None, port=None):
        self.server = server
        self.port = port
        self.client = None

    # ------------------------------------------
    # Conexão local
    # ------------------------------------------

    def connect_local(self):

        system = platform.system()

        if system == "Linux":
            socket = "/var/run/clamav/clamd.ctl"

        elif system == "Darwin":
            socket = "/usr/local/var/run/clamav/clamd.sock"

        else:
            raise RuntimeError(
                "Conexão local não suportada neste sistema."
            )

        self.client = pyclamd.ClamdUnixSocket(socket)

        if not self.client.ping():
            raise RuntimeError("Falha ao conectar ao ClamAV")

    # ------------------------------------------
    # Conexão servidor
    # ------------------------------------------

    def connect_server(self, host, port):

        self.client = pyclamd.ClamdNetworkSocket(host, port)

        if not self.client.ping():
            raise RuntimeError("Falha ao conectar ao servidor ClamAV")

    # ------------------------------------------
    # Scan
    # ------------------------------------------

    def scan_file(self, file_path):

        if not self.client:
            raise RuntimeError("ClamAV não conectado")

        return self.client.scan_file(file_path)

    # ------------------------------------------
    # Status
    # ------------------------------------------

    def is_alive(self):

        if not self.client:
            return False

        try:
            response = self.client.ping()
            return bool(response)
        except Exception:
            return False
     
    def disconnect(self):
        self.client = None