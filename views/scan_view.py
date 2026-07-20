import os

from PyQt5 import QtCore, QtWidgets

from utils.icon_loader import get_icon
from views.components import CardFrame, EmptyState, MetricCard


class ScanView(QtWidgets.QWidget):
    def __init__(self, parent=None, scan_controller=None):
        super().__init__(parent)
        if scan_controller is None:
            raise ValueError("ScanController não fornecido")

        self.scan_controller = scan_controller
        self._files_seen = 0
        self._threat_count = 0
        self._failure_count = 0
        self._elapsed = QtCore.QElapsedTimer()
        self._elapsed_timer = QtCore.QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed_metrics)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(12)

        hero = CardFrame(object_name="HeroCard")
        hero_layout = QtWidgets.QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 18, 20, 18)
        hero_layout.setSpacing(18)

        scan_icon = QtWidgets.QLabel()
        scan_icon.setFixedSize(88, 88)
        scan_icon.setAlignment(QtCore.Qt.AlignCenter)
        scan_icon.setPixmap(get_icon("scan").pixmap(56, 56))
        scan_icon.setStyleSheet(
            "background:#EAF8F0;border:1px solid #C7EBD4;border-radius:44px;"
        )
        hero_layout.addWidget(scan_icon, 0, QtCore.Qt.AlignTop)

        main = QtWidgets.QVBoxLayout()
        main.setSpacing(7)
        top = QtWidgets.QHBoxLayout()
        self.title_label = QtWidgets.QLabel("Aguardando verificação")
        self.title_label.setObjectName("SectionTitle")
        top.addWidget(self.title_label)
        top.addStretch()
        self.percent_label = QtWidgets.QLabel("0%")
        self.percent_label.setObjectName("MetricValue")
        self.percent_label.setProperty("accent", "green")
        top.addWidget(self.percent_label)
        main.addLayout(top)

        self.current_file_label = QtWidgets.QLabel("Arquivo atual: —")
        self.current_file_label.setProperty("muted", True)
        self.current_file_label.setWordWrap(True)
        self.current_file_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        main.addWidget(self.current_file_label)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        main.addWidget(self.progress_bar)

        actions = QtWidgets.QHBoxLayout()
        actions.addStretch()
        self.cancel_button = QtWidgets.QPushButton("Cancelar verificação")
        self.cancel_button.setProperty("role", "danger")
        self.cancel_button.setIcon(get_icon("stop"))
        self.cancel_button.clicked.connect(self.cancel_scan)
        self.cancel_button.setEnabled(False)
        actions.addWidget(self.cancel_button)
        main.addLayout(actions)
        hero_layout.addLayout(main, 1)
        layout.addWidget(hero)

        self.metrics_layout = QtWidgets.QGridLayout()
        self.metrics_layout.setSpacing(10)
        self.files_metric = MetricCard(
            "Arquivos analisados", "0", "Nesta sessão", "folder", "green"
        )
        self.threats_metric = MetricCard(
            "Ameaças", "0", "Detectadas", "virus", "red"
        )
        self.failures_metric = MetricCard(
            "Falhas", "0", "Leitura ou engine", "warning", "orange"
        )
        self.time_metric = MetricCard(
            "Tempo", "00:00", "0,0 arquivos/s", "history", "blue"
        )
        self.metric_cards = (
            self.files_metric,
            self.threats_metric,
            self.failures_metric,
            self.time_metric,
        )
        for column, card in enumerate(self.metric_cards):
            self.metrics_layout.addWidget(card, 0, column)
        layout.addLayout(self.metrics_layout)

        self.detail_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.detail_splitter.setChildrenCollapsible(False)

        log_card = CardFrame()
        log_layout = QtWidgets.QVBoxLayout(log_card)
        log_layout.setContentsMargins(13, 12, 13, 13)
        log_title = QtWidgets.QLabel("Atividade recente")
        log_title.setObjectName("SectionTitle")
        log_layout.addWidget(log_title)
        self.details_text = QtWidgets.QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMinimumHeight(145)
        self.details_text.setPlaceholderText(
            "As etapas da verificação aparecerão aqui."
        )
        log_layout.addWidget(self.details_text)
        self.detail_splitter.addWidget(log_card)

        threats_card = CardFrame()
        threats_layout = QtWidgets.QVBoxLayout(threats_card)
        threats_layout.setContentsMargins(13, 12, 13, 13)
        threats_title = QtWidgets.QLabel("Ameaças detectadas")
        threats_title.setObjectName("SectionTitle")
        threats_layout.addWidget(threats_title)
        self.threat_stack = QtWidgets.QStackedWidget()
        self.empty_threats = EmptyState(
            "Nenhuma ameaça encontrada",
            "Os arquivos detectados como ameaça serão exibidos nesta área.",
            "shield",
        )
        self.threat_stack.addWidget(self.empty_threats)

        self.threats_table = QtWidgets.QTableWidget(0, 4)
        self.threats_table.setHorizontalHeaderLabels([
            "Arquivo",
            "Caminho",
            "Ameaça",
            "Ação",
        ])
        header = self.threats_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.threats_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self.threats_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        self.threats_table.setAlternatingRowColors(True)
        self.threat_stack.addWidget(self.threats_table)
        threats_layout.addWidget(self.threat_stack)
        self.detail_splitter.addWidget(threats_card)
        self.detail_splitter.setSizes([480, 480])
        layout.addWidget(self.detail_splitter, 1)

        tip = QtWidgets.QFrame()
        tip.setObjectName("InfoPanel")
        tip_layout = QtWidgets.QHBoxLayout(tip)
        tip_layout.setContentsMargins(12, 9, 12, 9)
        tip_icon = QtWidgets.QLabel()
        tip_icon.setPixmap(get_icon("alert").pixmap(20, 20))
        tip_layout.addWidget(tip_icon)
        tip_text = QtWidgets.QLabel(
            "Dica de segurança: mantenha apenas aplicativos necessários "
            "abertos para uma verificação mais rápida."
        )
        tip_text.setWordWrap(True)
        tip_layout.addWidget(tip_text, 1)
        layout.addWidget(tip)

    def _connect_signals(self):
        controller = self.scan_controller
        controller.scan_started.connect(self.on_scan_started)
        controller.progress_updated.connect(self.on_progress)
        controller.current_file_changed.connect(self.on_current_file)
        controller.threat_detected.connect(self.on_threat_detected)
        controller.scan_error.connect(self.on_scan_error)
        controller.scan_finished.connect(self.on_scan_finished)

    def on_scan_started(self):
        self.title_label.setText("Verificação em andamento…")
        self.details_text.clear()
        self.threats_table.setRowCount(0)
        self.threat_stack.setCurrentWidget(self.empty_threats)
        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")
        self.cancel_button.setEnabled(True)
        self._files_seen = 0
        self._threat_count = 0
        self._failure_count = 0
        self._elapsed.start()
        self._elapsed_timer.start()
        self._refresh_metrics()
        self.log("Verificação iniciada.")

    def on_progress(self, value):
        try:
            value = max(0, min(100, int(value)))
        except Exception:
            value = 0
        self.progress_bar.setValue(value)
        self.percent_label.setText(f"{value}%")

    def on_current_file(self, file_path):
        if not file_path:
            return
        self._files_seen += 1
        self.current_file_label.setText(f"Arquivo atual: {file_path}")
        self.current_file_label.setToolTip(file_path)
        self.log(f"Escaneando: {file_path}")
        self._refresh_metrics()

    def on_threat_detected(self, result):
        try:
            if not result or not getattr(result, "infected", False):
                return
            file_path = getattr(result.detected_file, "path", "desconhecido")
            virus_name = getattr(result.virus, "name", "desconhecido")
            action = getattr(result, "action", None) or "-"
            row = self.threats_table.rowCount()
            self.threats_table.insertRow(row)
            icon_name = "warning" if "HEURISTIC" in virus_name else "virus"
            file_item = QtWidgets.QTableWidgetItem(os.path.basename(file_path))
            file_item.setIcon(get_icon(icon_name))
            self.threats_table.setItem(row, 0, file_item)
            self.threats_table.setItem(
                row, 1, QtWidgets.QTableWidgetItem(file_path)
            )
            self.threats_table.setItem(
                row, 2, QtWidgets.QTableWidgetItem(virus_name)
            )
            self.threats_table.setItem(
                row, 3, QtWidgets.QTableWidgetItem(action)
            )
            self._threat_count += 1
            self.threat_stack.setCurrentWidget(self.threats_table)
            self._refresh_metrics()
            self.log(f"⚠ Ameaça detectada: {virus_name}")
        except Exception as exc:
            self.log(f"Falha ao exibir ameaça detectada: {exc}")

    def on_scan_error(self, message):
        message = message or "Erro desconhecido durante a verificação."
        self._failure_count += 1
        self._refresh_metrics()
        self.log(f"❌ Erro durante o scan: {message}")
        QtWidgets.QMessageBox.critical(self, "Erro de verificação", message)

    def on_scan_finished(self, results):
        self._elapsed_timer.stop()
        infected = len([
            result for result in (results or [])
            if getattr(result, "infected", False)
        ])
        status = getattr(self.scan_controller, "last_scan_status", None)
        titles = {
            "completed": "Verificação concluída",
            "completed_with_failures": "Concluída com falhas",
            "cancelled": "Verificação cancelada",
            "failed": "Verificação falhou",
            "audit_failed": "Falha de auditoria",
        }
        self.title_label.setText(titles.get(status, "Verificação finalizada"))
        self.current_file_label.setText("Arquivo atual: —")
        if status in ("completed", "completed_with_failures"):
            self.progress_bar.setValue(100)
            self.percent_label.setText("100%")
        worker = getattr(self.scan_controller, "worker", None)
        if worker is not None:
            self._files_seen = max(
                self._files_seen,
                int(getattr(worker, "scanned_files", 0) or 0),
            )
            self._failure_count = max(
                self._failure_count,
                int(getattr(worker, "failed_files", 0) or 0),
            )
        self._threat_count = infected
        self._refresh_metrics()
        self.cancel_button.setEnabled(False)
        self.log(f"Verificação finalizada com status: {status or 'unknown'}.")
        self.log(f"Ameaças detectadas: {infected}")
        if status in ("completed", "completed_with_failures"):
            QtWidgets.QMessageBox.information(
                self,
                "Scan finalizado",
                f"Verificação finalizada.\nAmeaças encontradas: {infected}",
            )

    def _update_elapsed_metrics(self):
        self._refresh_metrics()

    def _refresh_metrics(self):
        elapsed_seconds = (
            self._elapsed.elapsed() / 1000
            if self._elapsed.isValid()
            else 0
        )
        minutes, seconds = divmod(int(elapsed_seconds), 60)
        speed = self._files_seen / elapsed_seconds if elapsed_seconds else 0
        self.files_metric.set_value(f"{self._files_seen:,}".replace(",", "."))
        self.threats_metric.set_value(self._threat_count)
        self.failures_metric.set_value(self._failure_count)
        self.time_metric.set_value(f"{minutes:02d}:{seconds:02d}")
        self.time_metric.set_detail(f"{speed:.1f} arquivos/s")

    def log(self, message):
        if not message:
            return
        self.details_text.append(str(message))
        if self.details_text.document().blockCount() > 500:
            cursor = self.details_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
        scrollbar = self.details_text.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def cancel_scan(self):
        self.log("Cancelando verificação…")
        self.title_label.setText("Cancelamento solicitado")
        self.cancel_button.setEnabled(False)
        try:
            self.scan_controller.interrupt_scan()
        except Exception as exc:
            self.log(f"Falha ao solicitar cancelamento: {exc}")

    def resizeEvent(self, event):
        columns = 2 if self.width() < 720 else 4
        for index, card in enumerate(self.metric_cards):
            self.metrics_layout.addWidget(
                card, index // columns, index % columns
            )
        self.detail_splitter.setOrientation(
            QtCore.Qt.Vertical if self.width() < 850 else QtCore.Qt.Horizontal
        )
        super().resizeEvent(event)

    def closeEvent(self, event):
        self._elapsed_timer.stop()
        controller = self.scan_controller
        connections = (
            (controller.scan_started, self.on_scan_started),
            (controller.progress_updated, self.on_progress),
            (controller.current_file_changed, self.on_current_file),
            (controller.threat_detected, self.on_threat_detected),
            (controller.scan_error, self.on_scan_error),
            (controller.scan_finished, self.on_scan_finished),
        )
        for signal, slot in connections:
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                continue
        event.accept()
