import subprocess


class FirewallEngine:
    """
    Executa comandos reais no firewall do sistema.
    """

    def __init__(self, engine_type):
        self.engine_type = engine_type

    # ----------------------------------------
    # STATUS
    # ----------------------------------------
    def status(self):

        if self.engine_type == "ufw":

            result = subprocess.run(
                ["ufw", "status"],
                capture_output=True,
                text=True
            )

            return result.stdout

        return "Firewall não suportado"

    # ----------------------------------------
    # ATIVAR
    # ----------------------------------------
    def enable(self):

        if self.engine_type == "ufw":

            subprocess.run(
                ["pkexec", "ufw", "enable"],
                check=False
            )

            return "Firewall ativado"

        return "Engine não suportada"

    # ----------------------------------------
    # DESATIVAR
    # ----------------------------------------
    def disable(self):

        if self.engine_type == "ufw":

            subprocess.run(
                ["pkexec", "ufw", "disable"],
                check=False
            )

            return "Firewall desativado"

        return "Engine não suportada"

    # ----------------------------------------
    # PERMITIR PORTA
    # ----------------------------------------
    def allow_port(self, port):

        if self.engine_type == "ufw":

            subprocess.run(
                ["pkexec", "ufw", "allow", str(port)],
                check=False
            )

            return f"Porta {port} liberada"

        return "Engine não suportada"

    # ----------------------------------------
    # BLOQUEAR PORTA
    # ----------------------------------------
    def block_port(self, port):

        if self.engine_type == "ufw":

            subprocess.run(
                ["pkexec", "ufw", "deny", str(port)],
                check=False
            )

            return f"Porta {port} bloqueada"

        return "Engine não suportada"