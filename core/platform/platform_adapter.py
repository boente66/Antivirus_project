import abc


class PlatformAdapter(abc.ABC):
    """
    Interface base para adaptação multiplataforma.

    Cada sistema operacional deve implementar
    os métodos necessários para integração
    com os serviços do antivírus.
    """

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
