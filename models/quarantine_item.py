from datetime import datetime

class QuarantineItem:
    def __init__(self, original_path, quarantine_path, virus_name):
        self.original_path = original_path
        self.quarantine_path = quarantine_path
        self.virus_name = virus_name
        self.date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __str__(self):
        return f"{self.virus_name} | {self.original_path}"