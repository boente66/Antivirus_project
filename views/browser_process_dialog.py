from PyQt5 import QtCore, QtWidgets


class BrowserProcessWarningDialog(QtWidgets.QDialog):
    """Apresenta ao usuário o resultado estruturado do pré-check."""

    def __init__(self, browsers, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Navegadores em execução")
        self.setModal(True)
        self.setMinimumWidth(480)

        layout = QtWidgets.QVBoxLayout(self)
        message = QtWidgets.QLabel(
            "Foram encontrados navegadores em execução.\n\n"
            "Durante um escaneamento completo o desempenho poderá ser "
            "reduzido e alguns navegadores podem apresentar travamentos "
            "temporários.\n\n"
            "Recomenda-se fechar esses programas antes de continuar."
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        browser_list = QtWidgets.QListWidget()
        browser_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        seen = set()
        for browser in browsers:
            key = (browser.display_name, browser.pid)
            if key in seen:
                continue
            seen.add(key)
            browser_list.addItem(
                f"{browser.display_name} — {browser.process_name} "
                f"(PID {browser.pid})"
            )
        browser_list.setMinimumHeight(110)
        layout.addWidget(browser_list)

        self.dont_show_checkbox = QtWidgets.QCheckBox(
            "Não mostrar novamente"
        )
        layout.addWidget(self.dont_show_checkbox)

        buttons = QtWidgets.QDialogButtonBox()
        continue_button = buttons.addButton(
            "Continuar",
            QtWidgets.QDialogButtonBox.AcceptRole,
        )
        cancel_button = buttons.addButton(
            "Cancelar",
            QtWidgets.QDialogButtonBox.RejectRole,
        )
        continue_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def dont_show_again(self):
        return self.dont_show_checkbox.isChecked()
