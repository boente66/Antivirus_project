import platform
import psutil
import time


class SystemInspector:
    """
    Responsável por coletar informações gerais do sistema.

    Não contém lógica de segurança nem controle de processos.
    """

    CACHE_TTL = 5

    def __init__(self):

        self._cache = {}
        self._cache_time = {}

    # --------------------------------------------------
    # Cache interno
    # --------------------------------------------------

    def _get_cached(self, key, func):

        now = time.time()

        if key in self._cache:

            if now - self._cache_time[key] < self.CACHE_TTL:
                return self._cache[key]

        value = func()

        self._cache[key] = value
        self._cache_time[key] = now

        return value

    # --------------------------------------------------
    # Sistema operacional
    # --------------------------------------------------

    def get_os_info(self):

        return {
            "name": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine()
        }

    # --------------------------------------------------
    # CPU
    # --------------------------------------------------

    def get_cpu_info(self):

        def collect():

            return {
                "physical_cores": psutil.cpu_count(logical=False),
                "total_cores": psutil.cpu_count(),
                "usage_percent": psutil.cpu_percent(interval=1),
                "frequency": (
                    psutil.cpu_freq().current
                    if psutil.cpu_freq()
                    else None
                )
            }

        return self._get_cached("cpu", collect)

    # --------------------------------------------------
    # Memória
    # --------------------------------------------------

    def get_memory_info(self):

        def collect():

            mem = psutil.virtual_memory()

            return {
                "total": mem.total,
                "available": mem.available,
                "used": mem.used,
                "percent": mem.percent
            }

        return self._get_cached("memory", collect)

    # --------------------------------------------------
    # Disco
    # --------------------------------------------------

    def get_disk_summary(self, path="/"):

        usage = psutil.disk_usage(path)

        return {
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent": usage.percent
        }

    # --------------------------------------------------
    # Snapshot completo
    # --------------------------------------------------

    def get_system_snapshot(self):

        return {
            "os": self.get_os_info(),
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info()
        }