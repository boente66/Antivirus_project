from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QTextEdit,
    QPushButton,
    QHBoxLayout
)

from PyQt5.QtCore import Qt
from datetime import datetime


class ProgressDialog(QDialog):

    MAX_LOG_LINES = 500

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Progresso da Desinstalação")
        self.setMinimumSize(520, 340)

        self.worker = None
        self._running = True

        self._build_ui()

    # =====================================================
    # UI
    # =====================================================

    def _build_ui(self):

        layout = QVBoxLayout(self)

        # -----------------------------------------
        # TÍTULO
        # -----------------------------------------

        self.title_label = QLabel("Desinstalando aplicativo...")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.title_label.setStyleSheet(
            "font-size:16px;font-weight:bold;"
        )

        layout.addWidget(self.title_label)

        # -----------------------------------------
        # BARRA DE PROGRESSO
        # -----------------------------------------

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        layout.addWidget(self.progress_bar)

        # -----------------------------------------
        # LABEL DE PERCENTUAL
        # -----------------------------------------

        self.percent_label = QLabel("0%")
        self.percent_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.percent_label)

        # -----------------------------------------
        # ÁREA DE LOG
        # -----------------------------------------

        self.log_area = QTextEdit(self)
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(180)

        layout.addWidget(self.log_area)

        # -----------------------------------------
        # BOTÕES
        # -----------------------------------------

        buttons_layout = QHBoxLayout()

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self._cancel)

        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #E67E22;
                color: white;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #D35400;
            }
        """)

        self.close_button = QPushButton("Fechar")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.close)

        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 8px;
                border-radius: 5px;
            }

            QPushButton:disabled {
                background-color: #A9A9A9;
            }

            QPushButton:hover {
                background-color: #2ECC71;
            }
        """)

        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.close_button)

        layout.addLayout(buttons_layout)

    # =====================================================
    # ASSOCIAR WORKER
    # =====================================================

    def set_worker(self, worker):

        self.worker = worker

    # =====================================================
    # ATUALIZAR PROGRESSO
    # =====================================================

    def update_progress(self, value, message=None):

        try:
            value = max(0, min(100, int(value)))
        except Exception:
            value = 0

        self.progress_bar.setValue(value)

        self.percent_label.setText(f"{value}%")

        if message:
            self.log(message)

    # =====================================================
    # LOG
    # =====================================================

    def log(self, message):

        if not message:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")

        text = f"[{timestamp}] {message}"

        self.log_area.append(text)

        # limitar tamanho do log
        if self.log_area.document().blockCount() > self.MAX_LOG_LINES:

            cursor = self.log_area.textCursor()

            cursor.movePosition(cursor.Start)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()

        scrollbar = self.log_area.verticalScrollBar()

        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    # =====================================================
    # FINALIZAR
    # =====================================================

    def finish(self, message="Desinstalação concluída"):

        self._running = False

        self.update_progress(100)

        self.log(message)

        self.cancel_button.setEnabled(False)

        self.close_button.setEnabled(True)

    # =====================================================
    # CANCELAR PROCESSO
    # =====================================================

    def _cancel(self):

        if not self._running:
            return

        if self.worker:

            try:
                self.worker.stop()
            except Exception:
                pass

        self.log("Processo cancelado pelo usuário.")

        self._running = False

        self.cancel_button.setEnabled(False)

        self.close_button.setEnabled(True)

    # =====================================================
    # BLOQUEAR FECHAMENTO DURANTE EXECUÇÃO
    # =====================================================

    def closeEvent(self, event):

        if self._running:

            event.ignore()

            self.log("Finalize ou cancele o processo antes de fechar.")

        else:

            event.accept()