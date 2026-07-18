import subprocess


class FirewallEngine:
    """
    Executa comandos reais no firewall do sistema.
    """

    def __init__(self, engine_type):
        self.engine_type = engine_type

    def _ensure_supported(self):
        if self.engine_type != "ufw":
            raise RuntimeError("Engine de firewall não suportada")

    def _validate_port(self, port):
        try:
            port = int(port)
        except (TypeError, ValueError):
            raise ValueError("Porta inválida")

        if port < 1 or port > 65535:
            raise ValueError("Porta fora do intervalo permitido")

        return port

    def _run(self, command, timeout=30):
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(message or "Comando de firewall falhou")

        return result.stdout.strip()

    # ----------------------------------------
    # STATUS
    # ----------------------------------------
    def status(self):
        self._ensure_supported()

        return self._run(["ufw", "status"], timeout=10)

    # ----------------------------------------
    # ATIVAR
    # ----------------------------------------
    def enable(self):
        self._ensure_supported()
        self._run(["pkexec", "ufw", "--force", "enable"])

        return "Firewall ativado"

    # ----------------------------------------
    # DESATIVAR
    # ----------------------------------------
    def disable(self):
        self._ensure_supported()
        self._run(["pkexec", "ufw", "disable"])

        return "Firewall desativado"

    # ----------------------------------------
    # PERMITIR PORTA
    # ----------------------------------------
    def allow_port(self, port):
        self._ensure_supported()
        port = self._validate_port(port)
        self._run(["pkexec", "ufw", "allow", str(port)])

        return f"Porta {port} liberada"

    # ----------------------------------------
    # BLOQUEAR PORTA
    # ----------------------------------------
    def block_port(self, port):
        self._ensure_supported()
        port = self._validate_port(port)
        self._run(["pkexec", "ufw", "deny", str(port)])

        return f"Porta {port} bloqueada"
