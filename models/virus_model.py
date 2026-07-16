class Virus:
    def __init__(self, name, path=None, detection_date=None, virus_type=None, recommended_action=None):
        self.name = name
        self.path = path
        self.detection_date = detection_date
        self.virus_type = virus_type
        self.recommended_action = recommended_action

    def get_name(self):
        return self.name

    def get_path(self):
        return self.path

    def get_detection_date(self):
        return self.detection_date

    def get_virus_type(self):
        return self.virus_type

    def get_recommended_action(self):
        return self.recommended_action

    def set_detection_date(self, detection_date):
        self.detection_date = detection_date

    def set_virus_type(self, virus_type):
        self.virus_type = virus_type

    def set_recommended_action(self, recommended_action):
        self.recommended_action = recommended_action

    def __str__(self):
        return (f"Vírus: {self.name}, Caminho: {self.path}, "
                f"Data de Detecção: {self.detection_date}, Tipo: {self.virus_type}, "
                f"Ação Recomendada: {self.recommended_action}")
