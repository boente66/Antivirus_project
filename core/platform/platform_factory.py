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

    @classmethod
    def create(cls):

        if cls._adapter_instance is not None:
            return cls._adapter_instance

        system = platform.system()

        if system == "Linux":

            cls._adapter_instance = LinuxAdapter()

        elif system == "Windows":

            cls._adapter_instance = WindowsAdapter()

        elif system == "Darwin":

            cls._adapter_instance = MacAdapter()

        else:

            raise RuntimeError(
                f"Sistema operacional não suportado: {system}"
            )

        return cls._adapter_instance

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

        return platform.system()

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