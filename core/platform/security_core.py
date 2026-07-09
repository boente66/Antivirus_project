from typing import Optional

from system.system_inspector import SystemInspector

from services.scan_service import ScanService
from services.disk_usage_service import DiskUsageService
from services.ransomware_service import RansomwareService
from services.clamav_service import ClamAVService
from services.wifi_scan_service import WiFiScanService
from services.engine_watchdog_service import EngineWatchdogService


class SecurityCore:
    """
    Núcleo central do antivírus.

    Responsável por:

    - detectar sistema operacional
    - inicializar PlatformAdapter
    - fornecer acesso aos serviços
    - iniciar monitoramento do engine
    """

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------

    def __init__(self):

        # --------------------------------------
        # System inspector
        # --------------------------------------

        self.system = SystemInspector()

        self.adapter = self.system.get_platform_adapter()

        # --------------------------------------
        # Serviços principais
        # --------------------------------------

        self.clamav = ClamAVService()

        self.scan_service = ScanService()

        self.disk_service = DiskUsageService()

        self.wifi_service = WiFiScanService(self.adapter)

        self.ransomware_service: Optional[RansomwareService] = None

        # --------------------------------------
        # Watchdog
        # --------------------------------------

        self.watchdog = EngineWatchdogService(self.clamav)

    # --------------------------------------------------
    # WATCHDOG
    # --------------------------------------------------

    def start_watchdog(self):

        if not self.watchdog.is_running():
            self.watchdog.start()

    def stop_watchdog(self):

        if self.watchdog.is_running():
            self.watchdog.stop()

    # --------------------------------------------------
    # WIFI
    # --------------------------------------------------

    def scan_wifi(self):

        return self.wifi_service.scan_networks()

    def current_wifi(self):

        return self.wifi_service.current_network()

    # --------------------------------------------------
    # DISK
    # --------------------------------------------------

    def list_volumes(self):

        return self.disk_service.get_volumes()

    # --------------------------------------------------
    # SCAN
    # --------------------------------------------------

    def start_scan_engine(self):

        return self.clamav.ensure_engine_ready()

    # --------------------------------------------------
    # RANSOMWARE
    # --------------------------------------------------

    def enable_ransomware_protection(self, directory, notify_callback):

        if self.ransomware_service is None:

            self.ransomware_service = RansomwareService(
                notify_callback
            )

        self.ransomware_service.start(directory)

    def disable_ransomware_protection(self):

        if self.ransomware_service:

            self.ransomware_service.stop()

            self.ransomware_service = None

    # --------------------------------------------------
    # STATUS
    # --------------------------------------------------

    def engine_status(self):

        return self.clamav.get_status()

    def engine_installed(self):

        return self.clamav.is_installed()

    # --------------------------------------------------
    # PLATFORM
    # --------------------------------------------------

    def get_platform_name(self):

        return self.adapter.get_os_name()

    def get_adapter(self):

        return self.adapter