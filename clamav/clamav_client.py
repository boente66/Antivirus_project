from array import array
import socket

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
        ler o arquivo. Em socket Unix, FILDES compartilha um descritor já aberto
        pela aplicação. Em conexões de rede, o conteúdo é enviado por INSTREAM.
        """

        if not self.client:
            raise RuntimeError("ClamAV não conectado")

        with open(file_path, "rb") as file_stream:
            if isinstance(self.client, pyclamd.ClamdUnixSocket):
                return self._scan_file_descriptor(file_stream)

            try:
                return self.client.scan_stream(file_stream)
            except BrokenPipeError as exc:
                raise RuntimeError(
                    "O servidor ClamAV encerrou o envio do arquivo. "
                    "Verifique o limite StreamMaxLength do servidor."
                ) from exc

    def _scan_file_descriptor(self, file_stream):
        """Escaneia um descritor local pelo protocolo FILDES do clamd."""

        client = self.client
        client._init_socket()

        try:
            client._send_command("FILDES")
            descriptors = array("i", [file_stream.fileno()])
            client.clamd_socket.sendmsg(
                [b"\0"],
                [(socket.SOL_SOCKET, socket.SCM_RIGHTS, descriptors)],
            )
            response = client._recv_response()
            filename, reason, status = client._parse_response(response)
        finally:
            client._close_socket()

        if status == "OK":
            return None

        return {filename: (status, reason)}

    def uses_local_socket(self):
        return isinstance(self.client, pyclamd.ClamdUnixSocket)

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
