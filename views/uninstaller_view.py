from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QLineEdit,
    QMessageBox,
    QHBoxLayout,
    QSplitter,
    QFrame,
)
from PyQt5.QtCore import Qt

from controllers.uninstaller_controller import UninstallerController
from views.progress_dialog import ProgressDialog
from views.components import CardFrame, EmptyState, MetricCard
from utils.icon_loader import get_icon


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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(12)

        # ------------------------------------------
        # Título
        # ------------------------------------------

        metrics = QHBoxLayout()
        self.programs_metric = MetricCard("Aplicativos instalados", "0", "Lista do sistema", "apps", "green")
        self.selection_metric = MetricCard("Selecionado", "—", "Escolha um aplicativo", "apps", "purple")
        metrics.addWidget(self.programs_metric)
        metrics.addWidget(self.selection_metric)
        layout.addLayout(metrics)

        toolbar = CardFrame()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(14, 10, 14, 10)

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

        toolbar_layout.addWidget(self.search_bar, 1)

        # ------------------------------------------
        # Botão atualizar
        # ------------------------------------------

        refresh_button = QPushButton("Atualizar Lista")

        refresh_button.setIcon(get_icon("update"))
        refresh_button.setProperty("role", "secondary")

        refresh_button.clicked.connect(
            self.controller.get_installed_programs
        )

        toolbar_layout.addWidget(refresh_button)
        layout.addWidget(toolbar)

        # ------------------------------------------
        # Lista de programas
        # ------------------------------------------

        content = QSplitter(Qt.Horizontal)
        content.setChildrenCollapsible(False)
        list_card = CardFrame()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(14, 12, 14, 14)
        list_title = QLabel("Aplicativos encontrados")
        list_title.setObjectName("SectionTitle")
        list_layout.addWidget(list_title)
        self.program_listbox = QListWidget()
        self.program_listbox.currentTextChanged.connect(self._selection_changed)
        list_layout.addWidget(self.program_listbox)
        content.addWidget(list_card)

        details_card = CardFrame()
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(18, 18, 18, 18)
        details_title = QLabel("Detalhes do aplicativo")
        details_title.setObjectName("SectionTitle")
        details_layout.addWidget(details_title)
        self.details_label = QLabel(
            "Selecione um aplicativo para revisar antes da remoção.\n\n"
            "A desinstalação solicitará confirmação e mostrará o progresso da operação."
        )
        self.details_label.setWordWrap(True)
        self.details_label.setProperty("muted", True)
        details_layout.addWidget(self.details_label)
        details_layout.addStretch()
        content.addWidget(details_card)
        content.setSizes([600, 400])
        self.content_splitter = content
        layout.addWidget(content, 1)

        # ------------------------------------------
        # Botão desinstalar
        # ------------------------------------------

        uninstall_button = QPushButton("Desinstalar")

        uninstall_button.setIcon(get_icon("delete"))
        uninstall_button.setProperty("role", "danger")

        uninstall_button.clicked.connect(
            self.uninstall_selected_program
        )

        layout.addWidget(uninstall_button)

    def _selection_changed(self, program_name):
        name = str(program_name or "").strip()
        self.selection_metric.set_value(name or "—")
        self.selection_metric.set_detail(
            "Pronto para revisar" if name else "Escolha um aplicativo"
        )
        self.details_label.setText(
            f"{name}\n\nRevise o nome do aplicativo e clique em Desinstalar. "
            "A operação administrativa será exibida em uma janela de progresso."
            if name else
            "Selecione um aplicativo para revisar antes da remoção."
        )

    # =====================================================
    # Atualizar lista de programas
    # =====================================================

    def update_program_list(self, programs):

        self.program_listbox.clear()

        try:
            self.program_listbox.addItems(programs)
            self.programs_metric.set_value(len(programs))
            self.programs_metric.set_detail("Aplicativos encontrados no sistema")
        except Exception:
            pass

    def resizeEvent(self, event):
        self.content_splitter.setOrientation(
            Qt.Vertical if self.width() < 820 else Qt.Horizontal
        )
        super().resizeEvent(event)

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
