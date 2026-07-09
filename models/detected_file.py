import os


class DetectedFile:

    def __init__(self, path):
        self.path = path
        self.filename = os.path.basename(path)

    def get_path(self):
        return self.path

    def get_filename(self):
        return self.filename
