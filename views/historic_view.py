from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QMessageBox,
    QHBoxLayout
)
from PyQt5.QtCore import Qt


class HistoricView(QWidget):

    MAX_LINES = 800

    # ==================================================
    # INIT
    # ==================================================

    def __init__(self, scan_controller):

        super().__init__()

        self.scan_controller = scan_controller

        self.init_ui()

    # ==================================================
    # UI
    # ==================================================

    def init_ui(self):

        self.setWindowTitle("Histórico de Verificações")

        layout = QVBoxLayout(self)

        layout.setContentsMargins(20, 20, 20, 20)

        # -------------------------------------------------
        # TÍTULO
        # -------------------------------------------------

        self.title_label = QLabel("Histórico de Verificações")

        self.title_label.setAlignment(Qt.AlignCenter)

        self.title_label.setStyleSheet("""
            font-size:22px;
            font-weight:bold;
            margin-bottom:10px;
            color:#2C3E50;
        """)

        layout.addWidget(self.title_label)

        # -------------------------------------------------
        # LOGS
        # -------------------------------------------------

        self.logs_text = QTextEdit()

        self.logs_text.setReadOnly(True)

        self.logs_text.setStyleSheet("""
            background:#FFFFFF;
            border:1px solid #D0D0D0;
            border-radius:8px;
            padding:8px;
            font-size:14px;
        """)

        layout.addWidget(self.logs_text)

        # -------------------------------------------------
        # BOTÕES
        # -------------------------------------------------

        buttons_layout = QHBoxLayout()

        self.load_logs_button = QPushButton("Carregar Histórico")

        self.load_logs_button.setStyleSheet("""
            QPushButton {
                background-color:#3498DB;
                color:white;
                padding:10px 18px;
                font-size:14px;
                border-radius:6px;
            }
            QPushButton:hover {
                background-color:#2E86C1;
            }
        """)

        self.load_logs_button.clicked.connect(
            self.load_scan_history
        )

        self.clear_button = QPushButton("Limpar")

        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color:#95A5A6;
                color:white;
                padding:10px 18px;
                font-size:14px;
                border-radius:6px;
            }
            QPushButton:hover {
                background-color:#7F8C8D;
            }
        """)

        self.clear_button.clicked.connect(
            self.logs_text.clear
        )

        buttons_layout.addWidget(self.load_logs_button)
        buttons_layout.addWidget(self.clear_button)

        layout.addLayout(buttons_layout)

    # ==================================================
    # FORMATAR REGISTRO
    # ==================================================

    def _format_scan(self, scan):

        status = getattr(scan, "status", "UNKNOWN")

        user = getattr(scan, "user", "—")

        start = getattr(scan, "start_time", "—")

        end = getattr(scan, "end_time", None) or "—"

        directory = getattr(scan, "directory_scanned", "—")

        total = getattr(scan, "total_files", 0)

        infected = getattr(scan, "infected_files", 0)

        return (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Usuário: {user}\n"
            f"Início: {start}\n"
            f"Fim: {end}\n"
            f"Pasta: {directory}\n"
            f"Arquivos escaneados: {total}\n"
            f"Infectados: {infected}\n"
            f"Status: {status}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )

    # ==================================================
    # CARREGAR HISTÓRICO
    # ==================================================

    def load_scan_history(self):

        try:

            scans = self.scan_controller.get_scan_history()

            self.logs_text.clear()

            if not scans:

                self.logs_text.append(
                    "Nenhum histórico encontrado."
                )

                return

            for scan in scans:

                text = self._format_scan(scan)

                self.logs_text.append(text)

            self._limit_logs()

            scrollbar = self.logs_text.verticalScrollBar()

            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())

        except Exception as e:

            QMessageBox.critical(
                self,
                "Erro",
                f"Falha ao carregar histórico:\n{e}"
            )

    # ==================================================
    # LIMITAR TAMANHO DO LOG
    # ==================================================

    def _limit_logs(self):

        doc = self.logs_text.document()

        if doc.blockCount() <= self.MAX_LINES:
            return

        cursor = self.logs_text.textCursor()

        while doc.blockCount() > self.MAX_LINES:

            cursor.movePosition(cursor.Start)

            cursor.select(cursor.LineUnderCursor)

            cursor.removeSelectedText()

            cursor.deleteChar()