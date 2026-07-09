class WiFi:
    def __init__(self, ssid, allow_traffic):
        """Modela redes Wi-Fi temporárias"""
        self.ssid = ssid
        self.allow_traffic = allow_traffic  # True para permitir, False para bloquear

    def __str__(self):
        return f"Rede: {self.ssid} | {'Permitido' if self.allow_traffic else 'Bloqueado'}"
