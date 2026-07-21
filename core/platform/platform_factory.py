import platform

from core.platform.linux_adapter import LinuxAdapter
from core.platform.windows_adapter import WindowsAdapter
from core.platform.mac_adapter import MacAdapter


class PlatformFactory:
    """
    Factory responsável por fornecer o adapter correto
    para o sistema operacional atual.
    """

    _adapter_instance = None

    # --------------------------------------------------
    # Criar adapter
    # --------------------------------------------------

    ADAPTERS = {
        "Linux": LinuxAdapter,
        "Windows": WindowsAdapter,
        "Darwin": MacAdapter,
    }
    ALIASES = {"macOS": "Darwin"}

    @classmethod
    def create(cls):
        """Retorna a instância única correspondente ao sistema real."""
        system = cls.normalize_system_name(platform.system())
        adapter_class = cls._adapter_class(system)
        if not isinstance(cls._adapter_instance, adapter_class):
            cls._adapter_instance = adapter_class()
        return cls._adapter_instance

    @classmethod
    def create_for(cls, system_name):
        """Cria adapter explícito sem contaminar o singleton de produção."""
        system = cls.normalize_system_name(system_name)
        return cls._adapter_class(system)()

    @classmethod
    def _adapter_class(cls, system):
        adapter_class = cls.ADAPTERS.get(system)
        if adapter_class is None:
            raise RuntimeError(f"Sistema operacional não suportado: {system}")
        return adapter_class

    @classmethod
    def normalize_system_name(cls, system_name):
        name = str(system_name or "").strip()
        return cls.ALIASES.get(name, name)

    # Backwards-compatible alias expected by other code.
    @classmethod
    def get_adapter(cls):
        """
        Alias for create() to preserve older API that calls
        PlatformFactory.get_adapter().
        """
        return cls.create()

    # --------------------------------------------------
    # Nome do sistema
    # --------------------------------------------------

    @staticmethod
    def get_os_name():
        return PlatformFactory.normalize_system_name(platform.system())

    # --------------------------------------------------
    # Verificar suporte
    # --------------------------------------------------

    @staticmethod
    def is_supported():

        return platform.system() in (
            "Linux",
            "Windows",
            "Darwin"
        )
