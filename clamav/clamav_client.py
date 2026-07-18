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

        """Envia o conteúdo do arquivo ao ClamAV sem expor o caminho ao daemon.

        O daemon costuma executar com um usuário restrito e, por isso, pode não
        conseguir atravessar diretórios pessoais mesmo quando a aplicação pode
        ler o arquivo. O comando INSTREAM mantém a leitura sob as permissões do
        processo da aplicação e transmite o conteúdo em blocos ao engine.
        """

        if not self.client:
            raise RuntimeError("ClamAV não conectado")

        with open(file_path, "rb") as file_stream:
            return self.client.scan_stream(file_stream)

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
