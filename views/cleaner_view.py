from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QMessageBox, QProgressBar, QCheckBox, QScrollArea
)
import platform

from controllers.cleaner_controller import CleanerController
from services.cleaner_service import CleanerService


class CleanerView(QtWidgets.QWidget):

    # ======================================================
    # INIT
    # ======================================================

    def __init__(self, parent=None):
        super().__init__(parent)

        self.service = CleanerService()
        self.controller = CleanerController(self.service)

        self._running = False

        self._build_ui()
        self._connect_signals()

    # ======================================================
    # SINAIS
    # ======================================================

    def _connect_signals(self):

        if platform.system() != "Linux":

            QMessageBox.warning(
                self,
                "Limpeza indisponível",
                "A limpeza de sistema está disponível apenas para Linux."
            )

            self.setEnabled(False)
            return

        self.controller.cleaning_progress.connect(self.progress.setValue)

        self.controller.cleaning_log.connect(self._append_log)

        self.controller.cleaning_completed.connect(self._on_finished)

        self.controller.error.connect(
            lambda msg: QMessageBox.critical(self, "Erro", msg)
        )

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ------------------------
        # LADO ESQUERDO
        # ------------------------

        left = QVBoxLayout()

        title = QLabel("Limpeza de Sistema")
        title.setStyleSheet("font-size:20px;font-weight:bold;")

        left.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        options_widget = QtWidgets.QWidget()

        self.options_layout = QVBoxLayout(options_widget)

        self.checks = {}

        for section, items in self._get_options().items():

            lbl = QLabel(section)
            lbl.setStyleSheet("font-weight:bold;margin-top:10px;")

            self.options_layout.addWidget(lbl)

            for item in items:

                cb = QCheckBox(item)
                cb.setChecked(True)

                self.checks[item] = cb

                self.options_layout.addWidget(cb)

        scroll.setWidget(options_widget)

        left.addWidget(scroll)

        # ------------------------
        # BOTÕES
        # ------------------------

        self.analyze_btn = QPushButton("Analisar")
        self.analyze_btn.clicked.connect(self.analyze)

        self.clean_btn = QPushButton("Executar limpeza")
        self.clean_btn.setEnabled(False)
        self.clean_btn.clicked.connect(self.clean)

        self.stop_btn = QPushButton("Parar")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop)

        left.addWidget(self.analyze_btn)
        left.addWidget(self.clean_btn)
        left.addWidget(self.stop_btn)

        main_layout.addLayout(left, 1)

        # ------------------------
        # LADO DIREITO
        # ------------------------

        right = QVBoxLayout()

        log_title = QLabel("Log de limpeza")
        log_title.setStyleSheet("font-weight:bold;")

        right.addWidget(log_title)

        self.log_list = QListWidget()

        right.addWidget(self.log_list)

        self.progress = QProgressBar()
        self.progress.setVisible(False)

        right.addWidget(self.progress)

        main_layout.addLayout(right, 2)

    # ======================================================
    # UTIL
    # ======================================================

    def _get_selected_labels(self):

        return [
            label
            for label, cb in self.checks.items()
            if cb.isChecked()
        ]

    # ------------------------------------------------------

    def _append_log(self, message):

        if not message:
            return

        self.log_list.addItem(message)

        self.log_list.scrollToBottom()

    # ======================================================
    # AÇÕES
    # ======================================================

    def analyze(self):

        if self._running:
            return

        self.log_list.clear()

        self.progress.setVisible(True)
        self.progress.setValue(0)

        selected = self._get_selected_labels()

        if not selected:

            QMessageBox.information(
                self,
                "Nenhuma opção selecionada",
                "Selecione pelo menos uma opção para análise."
            )

            self.progress.setVisible(False)
            return

        self._running = True

        self.stop_btn.setEnabled(True)

        self.controller.start_analyze(selected)

        self.clean_btn.setEnabled(True)

    # ------------------------------------------------------

    def clean(self):

        if self._running:
            return

        if QMessageBox.question(
            self,
            "Confirmação",
            "Deseja realmente executar a limpeza?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return

        self.log_list.clear()

        self.progress.setVisible(True)
        self.progress.setValue(0)

        selected = self._get_selected_labels()

        if not selected:

            QMessageBox.information(
                self,
                "Nenhuma opção selecionada",
                "Selecione pelo menos uma opção para limpeza."
            )

            self.progress.setVisible(False)
            return

        self._running = True

        self.stop_btn.setEnabled(True)

        self.controller.start_clean(selected)

    # ------------------------------------------------------

    def stop(self):

        if not self._running:
            return

        try:

            self.controller.stop()

        except Exception:
            pass

        self._append_log("Processo interrompido pelo usuário.")

        self._running = False

        self.stop_btn.setEnabled(False)

        self.progress.setVisible(False)

    # ======================================================
    # FINALIZAÇÃO
    # ======================================================

    def _on_finished(self, msg):

        self._append_log(msg)

        self.progress.setVisible(False)

        self._running = False

        self.stop_btn.setEnabled(False)

        if "Análise concluída" in msg:

            QMessageBox.information(
                self,
                "Resultado da Análise",
                msg
            )

    # ======================================================
    # OPÇÕES
    # ======================================================

    def _get_options(self):

        return {
            "Navegadores": [
                "Cache do Firefox",
                "Cookies do Firefox",
                "Cache do Chrome",
                "Cookies do Chrome",
            ],
            "Sistema": [
                "Arquivos temporários",
                "Logs do sistema",
            ],
            "Usuário": [
                "Cache de miniaturas",
                "Lixeira",
                "Cache de aplicativos",
            ]
        }