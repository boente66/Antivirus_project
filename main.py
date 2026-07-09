import sys
import traceback

from PyQt5.QtWidgets import QApplication
from views.main_view import MainView


if __name__ == "__main__":

    try:

        app = QApplication(sys.argv)

        view = MainView()
        view.show()

        sys.exit(app.exec())

    except Exception as e:

        print("Erro ao iniciar a aplicação:")
        traceback.print_exc()
