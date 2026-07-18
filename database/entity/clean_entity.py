class CleanEntity:
    """Registro persistente compatível com a tabela ``clean_history``.

    Métricas adicionais da execução são serializadas em JSON no campo
    ``details`` para preservar o esquema existente.
    """

    def __init__(
        self,
        user,
        timestamp,
        total_items,
        total_size,
        permanent,
        details,
        id=None
    ):
        self.id = id
        self.user = user
        self.timestamp = timestamp
        self.total_items = int(total_items or 0)
        self.total_size = int(total_size or 0)
        self.permanent = bool(permanent)
        self.details = str(details or "")
    # ============================
    # ➕ TUPLE
    # ============================
    def to_tuple(self):
        return (
            self.user,
            self.timestamp,
            self.total_items,
            self.total_size,
            int(self.permanent),
            self.details
        )
