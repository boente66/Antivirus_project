from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QStyle
)
from PyQt5.QtCore import Qt


class AdminPermissionDialog(QDialog):

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------

    def __init__(self, parent=None, reason=""):

        super().__init__(parent)

        self.setWindowTitle("Permissão de Administrador")

        self.setWindowModality(Qt.ApplicationModal)

        self.setMinimumWidth(420)

        self.setAttribute(Qt.WA_DeleteOnClose)

        layout = QVBoxLayout(self)

        layout.setSpacing(15)

        # --------------------------------------------------
        # ICON
        # --------------------------------------------------

        icon_label = QLabel()

        icon = self.style().standardIcon(QStyle.SP_MessageBoxWarning)

        icon_label.setPixmap(icon.pixmap(48, 48))

        icon_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(icon_label)

        # --------------------------------------------------
        # MESSAGE
        # --------------------------------------------------

        message = (
            "Esta operação requer permissões de administrador.\n\n"
            "Será solicitada sua senha para continuar."
        )

        if reason:
            message += f"\n\nMotivo: {reason}"

        label = QLabel(message)

        label.setWordWrap(True)

        label.setAlignment(Qt.AlignCenter)

        layout.addWidget(label)

        # --------------------------------------------------
        # BUTTONS
        # --------------------------------------------------

        btn_layout = QHBoxLayout()

        btn_layout.setSpacing(10)

        self.cancel_btn = QPushButton("Cancelar")

        self.cancel_btn.clicked.connect(self.reject)

        self.confirm_btn = QPushButton("Continuar")

        self.confirm_btn.setDefault(True)

        self.confirm_btn.clicked.connect(self.accept)

        btn_layout.addStretch()

        btn_layout.addWidget(self.cancel_btn)

        btn_layout.addWidget(self.confirm_btn)

        layout.addLayout(btn_layout)

    # --------------------------------------------------
    # STATIC HELPER
    # --------------------------------------------------

    @staticmethod
    def request(parent=None, reason=""):

        dialog = AdminPermissionDialog(parent, reason)

        return dialog.exec_() == QDialog.Accepted