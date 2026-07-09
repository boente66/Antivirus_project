class FirewallRule:
    def __init__(self, name, port, protocol, action):
        """Modela uma regra de firewall"""
        self.name = name
        self.port = port
        self.protocol = protocol
        self.action = action  # "block" ou "allow"

    def __str__(self):
        return f"Regra: {self.name} | Porta: {self.port} | Protocolo: {self.protocol} | Ação: {self.action}"
