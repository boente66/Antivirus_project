import subprocess
import platform
import threading
import time


class FirewallMonitorService:
    """
    Monitora conexões de rede do sistema.

    Pode detectar:
    - processos usando rede
    - portas abertas
    - conexões ativas
    """

    def __init__(self, interval=3):

        self.os_type = platform.system()

        self.running = False
        self.thread = None

        self.interval = interval

        self.connections = []

        self._lock = threading.Lock()

    # -----------------------------------------
    # INICIAR MONITORAMENTO
    # -----------------------------------------
    def start(self):

        if self.running:
            return

        self.running = True

        self.thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )

        self.thread.start()

    # -----------------------------------------
    # PARAR MONITORAMENTO
    # -----------------------------------------
    def stop(self):

        self.running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    # -----------------------------------------
    # STATUS
    # -----------------------------------------
    def is_running(self):
        return self.running

    # -----------------------------------------
    # LOOP PRINCIPAL
    # -----------------------------------------
    def _monitor_loop(self):

        while self.running:

            try:

                new_connections = self._read_connections()

                with self._lock:
                    self.connections = new_connections

            except Exception:
                pass

            time.sleep(self.interval)

    # -----------------------------------------
    # LER CONEXÕES
    # -----------------------------------------
    def _read_connections(self):

        if self.os_type == "Linux":
            return self._linux_connections()

        if self.os_type == "Windows":
            return self._windows_connections()

        if self.os_type == "Darwin":
            return self._mac_connections()

        return []

    # -----------------------------------------
    # LINUX
    # -----------------------------------------
    def _linux_connections(self):

        try:

            result = subprocess.run(
                ["ss", "-tunap"],
                capture_output=True,
                text=True,
                timeout=5
            )

            lines = result.stdout.splitlines()

            return lines

        except Exception:

            return []

    # -----------------------------------------
    # WINDOWS
    # -----------------------------------------
    def _windows_connections(self):

        try:

            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5
            )

            return result.stdout.splitlines()

        except Exception:

            return []

    # -----------------------------------------
    # MACOS
    # -----------------------------------------
    def _mac_connections(self):

        try:

            result = subprocess.run(
                ["netstat", "-anv"],
                capture_output=True,
                text=True,
                timeout=5
            )

            return result.stdout.splitlines()

        except Exception:

            return []

    # -----------------------------------------
    # OBTER CONEXÕES
    # -----------------------------------------
    def get_connections(self):

        with self._lock:
            return list(self.connections)