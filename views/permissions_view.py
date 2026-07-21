from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt

from controllers.firewall_controller import FirewallController
from utils.icon_loader import get_icon
from views.admin_dialog import AdminPermissionDialog


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

        notice = QLabel(
            "Perfis de aplicação publicados pelo UFW. O controle afeta as "
            "portas do perfil, não encerra nem bloqueia processos diretamente."
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)

        # -------------------------
        # Lista de aplicativos
        # -------------------------

        self.app_list = QListWidget()
        self.app_list.setSelectionMode(QListWidget.SingleSelection)
        self.app_list.itemSelectionChanged.connect(self._update_controls)

        layout.addWidget(self.app_list)

        # -------------------------
        # Botões
        # -------------------------

        self.allow_button = self.create_button(
            "Permitir Aplicativo",
            "resources/icons/shield.svg",
            "#27AE60",
            "#2ECC71",
            self.allow_permission
        )

        self.block_button = self.create_button(
            "Bloquear Aplicativo",
            "resources/icons/firewall.svg",
            "#E74C3C",
            "#C0392B",
            self.block_permission
        )

        self.remove_button = self.create_button(
            "Remover Aplicativo",
            "resources/icons/uninstall.svg",
            "#7F8C8D",
            "#95A5A6",
            self.remove_permission
        )

        layout.addWidget(self.allow_button)
        layout.addWidget(self.block_button)
        layout.addWidget(self.remove_button)

        self.refresh_button = self.create_button(
            "Atualizar perfis",
            "resources/icons/update.svg",
            "#3498DB",
            "#5DADE2",
            self.refresh_permissions,
        )
        layout.addWidget(self.refresh_button)

        applications_signal = getattr(self.controller, "applications_updated", None)
        if applications_signal is not None:
            applications_signal.connect(self._display_profiles)
        self.controller.capability_changed.connect(lambda _cap: self._update_controls())
        self._update_controls()

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
        profile = self._selected_profile()
        if profile is None:
            QMessageBox.warning(self, "Seleção necessária", "Selecione um perfil UFW.")
            return
        if not AdminPermissionDialog.request(
            self, f"Permitir tráfego de entrada para o perfil '{profile.name}'."
        ):
            return
        self.controller.add_permission(profile.name, True)

    # ----------------------------------------------------
    # Bloquear aplicativo
    # ----------------------------------------------------

    def block_permission(self):
        profile = self._selected_profile()
        if profile is None:
            QMessageBox.warning(self, "Seleção necessária", "Selecione um perfil UFW.")
            return
        warning = self.controller.notify_impact(profile.name)
        answer = QMessageBox.warning(
            self,
            "Confirmar bloqueio",
            f"{warning}\n\nDeseja continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        if not AdminPermissionDialog.request(
            self, f"Bloquear tráfego de entrada para o perfil '{profile.name}'."
        ):
            return
        self.controller.add_permission(profile.name, False)

    # ----------------------------------------------------
    # Remover aplicativo
    # ----------------------------------------------------

    def remove_permission(self):

        profile = self._selected_profile()
        if profile is None:
            QMessageBox.warning(self, "Seleção necessária", "Selecione um aplicativo da lista.")
            return
        if not profile.managed:
            QMessageBox.warning(
                self,
                "Regra protegida",
                "Somente regras de aplicação criadas pelo Antivírus podem ser removidas.",
            )
            return
        answer = QMessageBox.question(
            self,
            "Remover regra de aplicação",
            f"Remover a regra do perfil '{profile.name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        if not AdminPermissionDialog.request(
            self, f"Remover a regra de aplicação '{profile.name}'."
        ):
            return
        self.controller.remove_permission(profile)

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
        refresh = getattr(self.controller, "refresh_applications", None)
        if refresh is not None:
            refresh()

    def _display_profiles(self, profiles):
        self.app_list.clear()
        for profile in profiles:
            state = {
                "allow": "PERMITIDO",
                "deny": "BLOQUEADO",
            }.get(profile.action, "SEM REGRA")
            item = QListWidgetItem(f"{profile.name} — {state}")
            item.setData(Qt.UserRole, profile)
            self.app_list.addItem(item)
        self._update_controls()

    def _selected_profile(self):
        item = self.app_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _update_controls(self):
        profile = self._selected_profile()
        capability = self.controller.capability
        writable = capability.writable and not capability.write_blocked
        without_rule = profile is not None and profile.action is None
        self.allow_button.setEnabled(writable and without_rule)
        self.block_button.setEnabled(writable and without_rule)
        self.remove_button.setEnabled(
            writable and profile is not None and profile.managed
        )
        self.refresh_button.setEnabled(capability.readable)
