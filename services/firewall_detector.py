import platform
import shutil
import subprocess

from core.platform.platform_factory import PlatformFactory
from models.firewall_contracts import FirewallCapability, SupportStatus
from services.firewall_admin_executor import FirewallAdminExecutor


class FirewallDetector:
    """Delega a detecção à implementação da plataforma selecionada."""

    def __init__(
        self,
        system_name=None,
        which=None,
        runner=None,
        executor=None,
        platform_adapter=None,
    ):
        self.which = which or shutil.which
        self.runner = runner or subprocess.run
        self.executor = executor or FirewallAdminExecutor(
            runner=self.runner,
            which=self.which,
        )
        self._platform_error = None
        requested_system = str((system_name or platform.system)())
        try:
            self.platform_adapter = (
                platform_adapter
                or (
                    PlatformFactory.create_for(requested_system)
                    if system_name is not None
                    else PlatformFactory.create()
                )
            )
        except RuntimeError as exc:
            self.platform_adapter = None
            self._platform_error = str(exc)
        self.system_name = requested_system

    def detect(self):
        """Compatibilidade: retorna o backend identificado pela capacidade."""
        return self.detect_capability().backend

    def detect_capability(self):
        if self.platform_adapter is None:
            return FirewallCapability(
                platform=self.system_name or "unknown",
                backend="unknown",
                installed=False,
                active=None,
                readable=False,
                writable=False,
                requires_privilege=True,
                support_status=SupportStatus.UNSUPPORTED.value,
                reason=self._platform_error or "Sistema operacional não suportado.",
            )
        return self.platform_adapter.detect_firewall_capability(
            which=self.which,
            runner=self.runner,
            executor=self.executor,
        )
