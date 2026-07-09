class Permission:
    def __init__(self, app_name, allow_traffic):
        """Modela permissões de aplicativos"""
        self.app_name = app_name
        self.allow_traffic = allow_traffic  # True para permitir, False para bloquear

    def __str__(self):
        return f"Aplicativo: {self.app_name} | {'Permitido' if self.allow_traffic else 'Bloqueado'}"
