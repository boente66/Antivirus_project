from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QLineEdit,
    QMessageBox
)

from controllers.uninstaller_controller import UninstallerController
from views.progress_dialog import ProgressDialog


class UninstallerView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.controller = UninstallerController()
        self.progress_dialog = None

        # ------------------------------------------
        # Conectar sinais do controlador
        # ------------------------------------------

        self.controller.program_list_updated.connect(
            self.update_program_list
        )

        self.controller.progress_updated.connect(
            self.update_progress_dialog
        )

        self.controller.uninstall_completed.connect(
            self.finish_progress_dialog
        )

        # ------------------------------------------

        self.init_ui()

        # carregar lista inicial
        try:
            self.controller.get_installed_programs()
        except Exception:
            pass

    # =====================================================
    # UI
    # =====================================================

    def init_ui(self):

        self.setWindowTitle("Desinstalador de Programas")
        self.setMinimumSize(600, 420)

        layout = QVBoxLayout(self)

        # ------------------------------------------
        # Título
        # ------------------------------------------

        title_label = QLabel("Desinstalador de Programas")

        title_label.setStyleSheet(
            "font-size: 22px; font-weight: bold;"
        )

        layout.addWidget(title_label)

        # ------------------------------------------
        # Barra de busca
        # ------------------------------------------

        self.search_bar = QLineEdit()

        self.search_bar.setPlaceholderText(
            "Buscar aplicativos..."
        )

        self.search_bar.textChanged.connect(
            self.filter_program_list
        )

        layout.addWidget(self.search_bar)

        # ------------------------------------------
        # Botão atualizar
        # ------------------------------------------

        refresh_button = QPushButton("Atualizar Lista")

        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                font-size: 14px;
                padding: 6px;
                border-radius: 4px;
            }

            QPushButton:hover {
                background-color: #2ECC71;
            }
        """)

        refresh_button.clicked.connect(
            self.controller.get_installed_programs
        )

        layout.addWidget(refresh_button)

        # ------------------------------------------
        # Lista de programas
        # ------------------------------------------

        self.program_listbox = QListWidget()

        layout.addWidget(self.program_listbox)

        # ------------------------------------------
        # Botão desinstalar
        # ------------------------------------------

        uninstall_button = QPushButton("Desinstalar")

        uninstall_button.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                font-size: 14px;
                padding: 6px;
                border-radius: 4px;
            }

            QPushButton:hover {
                background-color: #C0392B;
            }
        """)

        uninstall_button.clicked.connect(
            self.uninstall_selected_program
        )

        layout.addWidget(uninstall_button)

    # =====================================================
    # Atualizar lista de programas
    # =====================================================

    def update_program_list(self, programs):

        self.program_listbox.clear()

        try:
            self.program_listbox.addItems(programs)
        except Exception:
            pass

    # =====================================================
    # Filtrar programas
    # =====================================================

    def filter_program_list(self, text):

        text = text.lower().strip()

        for i in range(self.program_listbox.count()):

            item = self.program_listbox.item(i)

            visible = text in item.text().lower()

            item.setHidden(not visible)

    # =====================================================
    # Desinstalar programa
    # =====================================================

    def uninstall_selected_program(self):

        selected_items = self.program_listbox.selectedItems()

        if not selected_items:

            QMessageBox.warning(
                self,
                "Seleção de Programa",
                "Por favor, selecione um programa para desinstalar."
            )

            return

        program_name = selected_items[0].text()

        confirm = QMessageBox.question(
            self,
            "Confirmação",
            f"Tem certeza de que deseja desinstalar {program_name}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        # ------------------------------------------
        # abrir diálogo de progresso
        # ------------------------------------------

        self.progress_dialog = ProgressDialog(self)

        self.progress_dialog.show()

        try:

            self.controller.uninstall_program(program_name)

        except Exception as e:

            QMessageBox.critical(
                self,
                "Erro",
                str(e)
            )

    # =====================================================
    # Atualizar progresso
    # =====================================================

    def update_progress_dialog(self, value, message):

        if not self.progress_dialog:
            return

        try:
            self.progress_dialog.update_progress(value, message)
        except Exception:
            pass

    # =====================================================
    # Finalizar progresso
    # =====================================================

    def finish_progress_dialog(self, message):

        if not self.progress_dialog:
            return

        try:

            self.progress_dialog.update_progress(100, message)

            self.progress_dialog.enable_close_button()

        except Exception:
            pass

        # atualizar lista de programas após remoção

        try:
            self.controller.get_installed_programs()
        except Exception:
            pass

    # =====================================================
    # Mensagem de status
    # =====================================================

    def show_status(self, message):

        QMessageBox.information(
            self,
            "Status",
            message
        )
