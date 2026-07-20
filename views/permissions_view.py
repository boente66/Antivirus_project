from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget,
    QPushButton, QLineEdit, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt

from controllers.firewall_controller import FirewallController
from utils.icon_loader import get_icon


class PermissionsView(QWidget):

    def __init__(self, controller: FirewallController):
        super().__init__()

        self.controller = controller

        self.init_ui()

    # ----------------------------------------------------
    # UI
    # ----------------------------------------------------

    def init_ui(self):

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        title = QLabel("Permissões de aplicativos")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        # -------------------------
        # Lista de aplicativos
        # -------------------------

        self.app_list = QListWidget()
        self.app_list.setSelectionMode(QListWidget.SingleSelection)

        layout.addWidget(self.app_list)

        # -------------------------
        # Campo de entrada
        # -------------------------

        self.app_input = QLineEdit()
        self.app_input.setPlaceholderText("Nome do aplicativo")

        # Enter adiciona automaticamente
        self.app_input.returnPressed.connect(self.allow_permission)

        layout.addWidget(self.app_input)

        # -------------------------
        # Botões
        # -------------------------

        allow_button = self.create_button(
            "Permitir Aplicativo",
            "resources/icons/shield.svg",
            "#27AE60",
            "#2ECC71",
            self.allow_permission
        )

        block_button = self.create_button(
            "Bloquear Aplicativo",
            "resources/icons/firewall.svg",
            "#E74C3C",
            "#C0392B",
            self.block_permission
        )

        remove_button = self.create_button(
            "Remover Aplicativo",
            "resources/icons/uninstall.svg",
            "#7F8C8D",
            "#95A5A6",
            self.remove_permission
        )

        layout.addWidget(allow_button)
        layout.addWidget(block_button)
        layout.addWidget(remove_button)

        # -------------------------

        self.refresh_permissions()

        self.setLayout(layout)

    # ----------------------------------------------------
    # Criar botão padrão
    # ----------------------------------------------------

    def create_button(self, text, icon_path, color, hover_color, callback):

        btn = QPushButton(text)

        icon_name = icon_path.rsplit("/", 1)[-1].split(".", 1)[0]
        btn.setIcon(get_icon(icon_name))
        btn.setProperty("role", "danger" if "Bloquear" in text else "secondary")

        btn.clicked.connect(callback)

        return btn

    # ----------------------------------------------------
    # Permitir aplicativo
    # ----------------------------------------------------

    def allow_permission(self):

        app_name = self.app_input.text().strip()

        if not app_name:
            QMessageBox.warning(self, "Entrada inválida", "Informe o nome do aplicativo.")
            return

        self.controller.add_permission(app_name, True)

        self.app_input.clear()

        self.refresh_permissions()

        QMessageBox.information(
            self,
            "Permissão Concedida",
            f"{app_name} foi permitido."
        )

    # ----------------------------------------------------
    # Bloquear aplicativo
    # ----------------------------------------------------

    def block_permission(self):

        app_name = self.app_input.text().strip()

        if not app_name:
            QMessageBox.warning(self, "Entrada inválida", "Informe o nome do aplicativo.")
            return

        self.controller.add_permission(app_name, False)

        self.app_input.clear()

        self.refresh_permissions()

        self.show_warning(app_name)

    # ----------------------------------------------------
    # Remover aplicativo
    # ----------------------------------------------------

    def remove_permission(self):

        selected = self.app_list.currentItem()

        if not selected:
            QMessageBox.warning(self, "Seleção necessária", "Selecione um aplicativo da lista.")
            return

        text = selected.text()

        app_name = text.split(" - ")[0]

        self.controller.remove_permission(app_name)

        self.refresh_permissions()

        QMessageBox.information(
            self,
            "Aplicativo removido",
            f"{app_name} removido da lista."
        )

    # ----------------------------------------------------
    # Aviso de impacto
    # ----------------------------------------------------

    def show_warning(self, app_name):

        warning = self.controller.notify_impact(app_name)

        if warning:

            QMessageBox.warning(
                self,
                "Aviso de Impacto",
                warning
            )

    # ----------------------------------------------------
    # Atualizar lista
    # ----------------------------------------------------

    def refresh_permissions(self):

        self.app_list.clear()

        permissions = self.controller.get_permissions()

        self.app_list.addItems(permissions)
