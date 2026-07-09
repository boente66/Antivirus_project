from typing import List, Dict, Optional


class WiFiScanService:
    """
    Serviço responsável por operações de redes WiFi.

    Utiliza o PlatformAdapter ativo para executar
    operações específicas do sistema operacional.
    """

    # -------------------------------------------------
    # INIT
    # -------------------------------------------------

    def __init__(self, adapter):

        if adapter is None:
            raise ValueError("PlatformAdapter não informado")

        self.adapter = adapter

        self._last_scan: List[Dict] = []

    # -------------------------------------------------
    # VERIFICAR SUPORTE
    # -------------------------------------------------

    def is_supported(self) -> bool:

        return hasattr(self.adapter, "scan_wifi_networks")

    # -------------------------------------------------
    # SCAN WIFI
    # -------------------------------------------------

    def scan_networks(self) -> List[Dict]:

        if not self.is_supported():
            return []

        try:

            networks = self.adapter.scan_wifi_networks()

            normalized = self._normalize(networks)

            self._last_scan = normalized

            return normalized

        except Exception:
            return []

    # -------------------------------------------------
    # ULTIMO SCAN
    # -------------------------------------------------

    def last_scan(self) -> List[Dict]:

        return self._last_scan

    # -------------------------------------------------
    # WIFI DISPONÍVEL
    # -------------------------------------------------

    def wifi_available(self) -> bool:

        try:

            networks = self.scan_networks()

            return len(networks) > 0

        except Exception:
            return False

    # -------------------------------------------------
    # REDE ATUAL
    # -------------------------------------------------

    def current_network(self) -> Optional[str]:

        try:

            if hasattr(self.adapter, "current_wifi_network"):
                return self.adapter.current_wifi_network()

        except Exception:
            pass

        return None

    # -------------------------------------------------
    # REDES ABERTAS
    # -------------------------------------------------

    def open_networks(self) -> List[Dict]:

        networks = self.scan_networks()

        open_list = []

        for net in networks:

            security = str(net.get("security", "")).lower()

            if security in ("", "open", "none"):
                open_list.append(net)

        return open_list

    # -------------------------------------------------
    # REDES SEGURAS
    # -------------------------------------------------

    def secure_networks(self) -> List[Dict]:

        networks = self.scan_networks()

        secure = []

        for net in networks:

            security = str(net.get("security", "")).lower()

            if "wpa" in security:
                secure.append(net)

        return secure

    # -------------------------------------------------
    # PROCURAR REDE
    # -------------------------------------------------

    def find_network(self, ssid: str) -> Optional[Dict]:

        if not ssid:
            return None

        for net in self.scan_networks():

            if net.get("ssid") == ssid:
                return net

        return None

    # -------------------------------------------------
    # NORMALIZAÇÃO
    # -------------------------------------------------

    def _normalize(self, networks: List[Dict]) -> List[Dict]:

        normalized = []

        seen = set()

        for net in networks:

            ssid = net.get("ssid")

            if not ssid or ssid in seen:
                continue

            seen.add(ssid)

            normalized.append({
                "ssid": ssid,
                "signal": net.get("signal"),
                "security": net.get("security")
            })

        return normalized