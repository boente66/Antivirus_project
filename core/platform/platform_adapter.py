import abc


class PlatformAdapter(abc.ABC):
    """
    Interface base para adaptação multiplataforma.

    Cada sistema operacional deve implementar
    os métodos necessários para integração
    com os serviços do antivírus.
    """

    platform = "unknown"
    backend = "unknown"

    # --------------------------------------------------
    # SISTEMA
    # --------------------------------------------------

    @abc.abstractmethod
    def get_os_name(self):
        pass

    @abc.abstractmethod
    def get_home_directory(self):
        pass

    # --------------------------------------------------
    # DISCO
    # --------------------------------------------------

    @abc.abstractmethod
    def get_volumes(self):
        pass

    # --------------------------------------------------
    # PROGRAMAS
    # --------------------------------------------------

    @abc.abstractmethod
    def get_installed_programs(self):
        pass

    # --------------------------------------------------
    # PROCESSOS
    # --------------------------------------------------

    @abc.abstractmethod
    def get_running_processes(self):
        pass

    # --------------------------------------------------
    # WIFI
    # --------------------------------------------------

    @abc.abstractmethod
    def scan_wifi_networks(self):
        pass

    # --------------------------------------------------
    # FIREWALL
    # --------------------------------------------------

    @abc.abstractmethod
    def get_firewall_status(self):
        pass

    def create_firewall_adapter(self, executor=None):
        """O próprio adapter de plataforma expõe o contrato de Firewall."""
        return self

    def read_status(self, operation_id="status"):
        """Converte a leitura legada em resultado operacional estruturado."""
        from models.firewall_contracts import FirewallOperationResult, OperationStatus

        backend = self.backend
        try:
            status = self.get_firewall_status()
        except Exception as exc:
            return FirewallOperationResult(
                operation_id=operation_id,
                status=OperationStatus.EXECUTION_FAILED.value,
                backend=backend,
                verified=False,
                error_code="status_read_failed",
                message=str(exc),
            )
        normalized = str(status or "unknown").lower()
        active = True if normalized == "active" else False if normalized == "inactive" else None
        if active is None:
            return FirewallOperationResult(
                operation_id=operation_id,
                status=OperationStatus.UNSUPPORTED.value,
                backend=backend,
                confirmed_state={"active": None},
                verified=False,
                error_code="status_unsupported",
                message="Leitura do estado não é suportada neste sistema.",
            )
        return FirewallOperationResult(
            operation_id=operation_id,
            status=OperationStatus.SUCCESS.value,
            backend=backend,
            confirmed_state={"active": active},
            verified=True,
            message="Estado do Firewall confirmado em modo somente leitura.",
        )

    def list_rules(self, operation_id="list_rules"):
        from models.firewall_contracts import FirewallOperationResult, OperationStatus

        return FirewallOperationResult(
            operation_id=operation_id,
            status=OperationStatus.UNSUPPORTED.value,
            backend=self.backend,
            verified=False,
            error_code="rule_listing_unsupported",
            message="Listagem de regras não suportada neste sistema.",
        ), []

    def detect_firewall_capability(self, **_dependencies):
        """Contrato seguro padrão para plataformas sem implementação."""
        from models.firewall_contracts import FirewallCapability, SupportStatus

        return FirewallCapability(
            platform=self.platform,
            backend=self.backend,
            installed=False,
            active=None,
            readable=False,
            writable=False,
            requires_privilege=True,
            support_status=SupportStatus.UNSUPPORTED.value,
            reason=f"Firewall sem implementação validada para {self.platform}.",
        )

    # --------------------------------------------------
    # USUÁRIOS
    # --------------------------------------------------

    @abc.abstractmethod
    def get_system_users(self):
        pass

    # --------------------------------------------------
    # SCAN INTELIGENTE
    # --------------------------------------------------

    @abc.abstractmethod
    def get_smart_scan_targets(self):
        pass

    # --------------------------------------------------
    # DIRETÓRIOS TEMPORÁRIOS
    # --------------------------------------------------

    @abc.abstractmethod
    def get_temp_directories(self):
        pass

    # --------------------------------------------------
    # DIRETÓRIOS CRÍTICOS
    # --------------------------------------------------

    @abc.abstractmethod
    def get_system_directories(self):
        pass

    # --------------------------------------------------
    # PRIVILÉGIOS
    # --------------------------------------------------

    @abc.abstractmethod
    def has_admin_privileges(self):
        pass

    def get_cleaner_capabilities(self):
        return {
            "supported": False,
            "message": "Limpeza segura ainda não está disponível neste sistema.",
        }
