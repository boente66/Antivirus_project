from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from controllers.cleaner_controller import CleanerController


class CleanerView(QtWidgets.QWidget):
    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self.controller = controller or CleanerController()
        self._running = False
        self._last_analysis = None
        self._build_ui()
        self._connect_signals()

        if not self.controller.supported:
            self.setEnabled(False)
            QMessageBox.warning(self, "Limpeza indisponível", self.controller.support_message)

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

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
            label = QLabel(section)
            label.setStyleSheet("font-weight:bold;margin-top:10px;")
            self.options_layout.addWidget(label)
            for text in items:
                checkbox = QCheckBox(text)
                checkbox.setChecked("Cookies" not in text)
                checkbox.stateChanged.connect(self._invalidate_analysis)
                self.checks[text] = checkbox
                self.options_layout.addWidget(checkbox)
        scroll.setWidget(options_widget)
        left.addWidget(scroll)

        self.analyze_btn = QPushButton("Analisar")
        self.clean_btn = QPushButton("Executar limpeza")
        self.stop_btn = QPushButton("Cancelar")
        self.clean_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self.analyze)
        self.clean_btn.clicked.connect(self.clean)
        self.stop_btn.clicked.connect(self.stop)
        left.addWidget(self.analyze_btn)
        left.addWidget(self.clean_btn)
        left.addWidget(self.stop_btn)
        main_layout.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("Itens analisados"))
        self.items_table = QTableWidget(0, 6)
        self.items_table.setHorizontalHeaderLabels([
            "Categoria", "Caminho", "Tamanho", "Privilégio", "Modo", "Tipo"
        ])
        self.items_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        right.addWidget(self.items_table)

        right.addWidget(QLabel("Log da operação"))
        self.log_list = QListWidget()
        right.addWidget(self.log_list)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        right.addWidget(self.progress)
        main_layout.addLayout(right, 2)

    def _connect_signals(self):
        self.controller.cleaning_started.connect(self._on_started)
        self.controller.cleaning_progress.connect(self._set_progress)
        self.controller.cleaning_log.connect(self._append_log)
        self.controller.analysis_completed.connect(self._on_analysis_completed)
        self.controller.cleaning_completed.connect(self._on_clean_completed)
        self.controller.cleaning_cancelled.connect(self._on_cancelled)
        self.controller.error.connect(self._on_error)

    def analyze(self):
        if self._running:
            return
        selected = self._get_selected_labels()
        if not selected:
            QMessageBox.information(self, "Nenhuma opção", "Selecione ao menos uma opção.")
            return
        self.log_list.clear()
        self.items_table.setRowCount(0)
        self._last_analysis = None
        self.clean_btn.setEnabled(False)
        self.controller.start_analyze(selected)

    def clean(self):
        if self._running:
            return
        selected = self._get_selected_labels()
        if not selected or not self._last_analysis:
            QMessageBox.warning(self, "Limpeza", "Execute uma análise válida primeiro.")
            return
        count = len(self._last_analysis.get("candidates", []))
        answer = QMessageBox.question(
            self,
            "Confirmar limpeza",
            f"Confirmar a limpeza de {count} item(ns) previamente analisado(s)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.controller.start_clean(selected)

    def stop(self):
        if self._running and self.controller.stop():
            self.stop_btn.setEnabled(False)

    def _on_started(self, mode):
        self._running = True
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.analyze_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._append_log(f"Operação iniciada: {mode}")

    def _on_analysis_completed(self, result):
        self._last_analysis = result
        self._populate_candidates(result.get("candidates", []))
        self._finish_ui()
        self.clean_btn.setEnabled(bool(result.get("candidates")))
        QMessageBox.information(self, "Análise concluída", self._format_result(result))

    def _on_clean_completed(self, result):
        self._append_log(self._format_result(result))
        self._last_analysis = None
        self._finish_ui()
        if result.get("status") == "failed":
            title = "Falha na limpeza"
        elif result.get("errors"):
            title = "Limpeza concluída com falhas"
        else:
            title = "Limpeza concluída"
        QMessageBox.information(self, title, self._format_result(result))

    def _on_cancelled(self, result):
        self._append_log("Operação cancelada; itens já processados não foram revertidos.")
        self._last_analysis = None
        self._finish_ui(cancelled=True)
        QMessageBox.warning(self, "Limpeza cancelada", self._format_result(result))

    def _on_error(self, message):
        self._append_log(message)
        self._finish_ui(cancelled=True)
        QMessageBox.critical(self, "Erro na limpeza", str(message))

    def _finish_ui(self, cancelled=False):
        self._running = False
        self.analyze_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if cancelled:
            self.clean_btn.setEnabled(False)
        self.progress.setVisible(False)

    def _populate_candidates(self, candidates):
        self.items_table.setRowCount(0)
        for item in candidates:
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)
            values = [
                item.get("category", ""),
                item.get("path", ""),
                self._format_size(item.get("size", 0)),
                "Sim" if item.get("requires_admin") else "Não",
                "Permanente" if item.get("removal_mode") == "permanent" else "Lixeira",
                item.get("kind", ""),
            ]
            for column, value in enumerate(values):
                self.items_table.setItem(row, column, QTableWidgetItem(str(value)))

    def _invalidate_analysis(self):
        if self._running:
            return
        self._last_analysis = None
        self.clean_btn.setEnabled(False)
        self.items_table.setRowCount(0)

    def _get_selected_labels(self):
        return [text for text, checkbox in self.checks.items() if checkbox.isChecked()]

    def _append_log(self, message):
        if message:
            self.log_list.addItem(str(message))
            self.log_list.scrollToBottom()

    def _set_progress(self, value):
        self.progress.setValue(max(0, min(100, int(value))))

    @staticmethod
    def _format_size(size):
        value = float(size or 0)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024:
                return f"{value:.2f} {unit}"
            value /= 1024
        return f"{value:.2f} TB"

    @staticmethod
    def _format_result(result):
        return (
            f"Status: {result.get('status')}\n"
            f"Selecionados: {result.get('selected', 0)}\n"
            f"Processados: {result.get('processed', 0)}\n"
            f"Removidos: {result.get('removed', 0)}\n"
            f"Ignorados: {result.get('ignored', 0)}\n"
            f"Falhas: {result.get('failed', 0)}\n"
            f"Bytes liberados: {result.get('bytes_freed', 0)}"
        )

    @staticmethod
    def _get_options():
        return {
            "Navegadores": [
                "Cache do Firefox", "Cookies do Firefox",
                "Cache do Chrome", "Cookies do Chrome",
                "Cache do Chromium", "Cookies do Chromium",
                "Cache do Brave", "Cookies do Brave",
                "Cache do Edge", "Cookies do Edge",
                "Cache do Opera", "Cookies do Opera",
            ],
            "Sistema": ["Arquivos temporários"],
            "Usuário": ["Cache de miniaturas", "Lixeira", "Cache de aplicativos"],
        }
