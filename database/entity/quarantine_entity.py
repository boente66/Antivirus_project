# database/entities/quarantine_entity.py
class QuarantineEntity:
    def __init__(self, original_path, quarantine_path, virus_name, date, status):
        self.original_path = original_path
        self.quarantine_path = quarantine_path
        self.virus_name = virus_name
        self.date = date
        self.status = status

    def to_tuple(self):
        return (
            self.original_path,
            self.quarantine_path,
            self.virus_name,
            self.date,
            self.status
        )
