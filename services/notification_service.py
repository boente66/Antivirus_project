from PyQt5.QtCore import QObject, pyqtSignal


class NotificationService(QObject):
    """
    Serviço global de notificações.

    Camadas de baixo nível (controllers) podem emitir notificações
    sem depender da interface gráfica.
    A UI (MainView) conecta-se aos sinais para exibir ao usuário.
    """

    info = pyqtSignal(str, str)     # title, message
    warning = pyqtSignal(str, str)  # title, message
    error = pyqtSignal(str, str)    # title, message

    def __init__(self):
        super().__init__()

    # -----------------------------------------
    # NOTIFICAÇÕES
    # -----------------------------------------

    def notify_info(self, title: str, message: str):
        self.info.emit(title, message)

    def notify_warning(self, title: str, message: str):
        self.warning.emit(title, message)

    def notify_error(self, title: str, message: str):
        self.error.emit(title, message)


# Instância global (singleton simples)
notification_service = NotificationService()