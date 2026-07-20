import sys
import traceback

from PyQt5.QtWidgets import QApplication
from views.main_view import MainView
from views.theme import APP_STYLESHEET


if __name__ == "__main__":

    try:

        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        app.setStyleSheet(APP_STYLESHEET)

        view = MainView()
        view.show()

        sys.exit(app.exec())

    except Exception as e:

        print("Erro ao iniciar a aplicação:")
        traceback.print_exc()
