class CleanEntity:
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
        self.total_items = total_items
        self.total_size = total_size
        self.permanent = permanent
        self.details = details
    # ============================
    # ➕ TUPLE
    # ============================
    def to_tuple(self):
        return (
            self.user,
            self.timestamp,
            self.total_items,
            self.total_size,
            self.permanent,
            self.details
        )
