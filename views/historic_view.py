from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from utils.icon_loader import get_icon
from views.components import CardFrame, MetricCard


class HistoricView(QWidget):
    PAGE_SIZE = 50
    THREAT_PAGE_SIZE = 50
    SCAN_TYPE_LABELS = {
        "smart": "Inteligente",
        "quick": "Rápido",
        "full": "Completo",
        "custom": "Personalizado",
    }

    def __init__(self, scan_controller):
        super().__init__()
        self.scan_controller = scan_controller
        self.page = 0
        self.threat_page = 0
        self.selected_scan_id = None
        self.selected_scan = None
        self._loaded_once = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Histórico de Verificações")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(12)

        metrics = QHBoxLayout()
        self.scans_metric = MetricCard("Verificações exibidas", "0", "Página atual", "history", "green")
        self.threats_metric = MetricCard("Ameaças no scan", "0", "Selecione uma verificação", "virus", "orange")
        self.result_metric = MetricCard("Resultado", "—", "Sem seleção", "status", "blue")
        metrics.addWidget(self.scans_metric)
        metrics.addWidget(self.threats_metric)
        metrics.addWidget(self.result_metric)
        layout.addLayout(metrics)

        scans_card = CardFrame()
        scans_layout = QVBoxLayout(scans_card)
        scans_layout.setContentsMargins(14, 12, 14, 14)
        scans_title = QLabel("Verificações realizadas")
        scans_title.setObjectName("SectionTitle")
        scans_layout.addWidget(scans_title)

        self.scan_table = QTableWidget(0, 6)
        self.scan_table.setHorizontalHeaderLabels(
            ["Início", "Tipo", "Alvo", "Arquivos", "Ameaças", "Status"]
        )
        self.scan_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.scan_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.scan_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.scan_table.setAlternatingRowColors(True)
        self.scan_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.scan_table.horizontalHeader().setStretchLastSection(True)
        self.scan_table.itemSelectionChanged.connect(self._load_selected_scan)
        scans_layout.addWidget(self.scan_table)

        scan_navigation = QHBoxLayout()
        self.previous_button = QPushButton("Anterior")
        self.next_button = QPushButton("Próxima")
        self.page_label = QLabel("Página 1")
        self.reload_button = QPushButton("Atualizar")
        self.previous_button.clicked.connect(self.previous_page)
        self.next_button.clicked.connect(self.next_page)
        self.reload_button.clicked.connect(self.load_scan_history)
        scan_navigation.addWidget(self.previous_button)
        scan_navigation.addWidget(self.page_label)
        scan_navigation.addWidget(self.next_button)
        scan_navigation.addStretch()
        scan_navigation.addWidget(self.reload_button)
        scans_layout.addLayout(scan_navigation)
        layout.addWidget(scans_card, 1)

        details_card = CardFrame()
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(14, 12, 14, 14)
        self.details_label = QLabel("Selecione um scan para ver as ameaças.")
        self.details_label.setWordWrap(True)
        details_layout.addWidget(self.details_label)

        self.threat_table = QTableWidget(0, 4)
        self.threat_table.setHorizontalHeaderLabels(
            ["Data", "Ameaça", "Ação", "Caminho"]
        )
        self.threat_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.threat_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.threat_table.setAlternatingRowColors(True)
        self.threat_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.threat_table.horizontalHeader().setStretchLastSection(True)
        details_layout.addWidget(self.threat_table)

        threat_navigation = QHBoxLayout()
        self.previous_threat_button = QPushButton("Ameaças anteriores")
        self.next_threat_button = QPushButton("Próximas ameaças")
        self.threat_page_label = QLabel("Página 1")
        self.previous_threat_button.clicked.connect(self.previous_threat_page)
        self.next_threat_button.clicked.connect(self.next_threat_page)
        threat_navigation.addWidget(self.previous_threat_button)
        threat_navigation.addWidget(self.threat_page_label)
        threat_navigation.addWidget(self.next_threat_button)
        threat_navigation.addStretch()
        details_layout.addLayout(threat_navigation)
        layout.addWidget(details_card, 1)

        self.reload_button.setIcon(get_icon("update"))
        self.reload_button.setProperty("role", "secondary")

        self._update_navigation(scan_count=0, threat_count=0)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._loaded_once:
            self.load_scan_history()

    def load_scan_history(self):
        try:
            scans = self.scan_controller.get_scan_history(
                limit=self.PAGE_SIZE,
                offset=self.page * self.PAGE_SIZE,
            )
            self._populate_scans(scans)
            self._loaded_once = True
        except Exception as exc:
            self._show_error(f"Falha ao carregar histórico:\n{exc}")

    def _populate_scans(self, scans):
        self.scan_table.blockSignals(True)
        self.scan_table.setRowCount(0)
        self.selected_scan_id = None
        self.selected_scan = None
        self.threat_table.setRowCount(0)
        self.details_label.setText(
            "Nenhum histórico encontrado."
            if not scans
            else "Selecione um scan para ver as ameaças."
        )

        for scan in scans:
            row = self.scan_table.rowCount()
            self.scan_table.insertRow(row)
            start_item = QTableWidgetItem(str(scan.start_time or "—"))
            start_item.setData(Qt.UserRole, scan.id)
            start_item.setData(Qt.UserRole + 1, scan)
            values = (
                start_item,
                QTableWidgetItem(self._scan_type_label(scan.scan_type)),
                QTableWidgetItem(str(scan.directory_scanned or "—")),
                QTableWidgetItem(str(scan.total_files or 0)),
                QTableWidgetItem(str(scan.threat_count or 0)),
                QTableWidgetItem(str(scan.status or "unknown")),
            )
            for column, item in enumerate(values):
                self.scan_table.setItem(row, column, item)

        self.scan_table.blockSignals(False)
        self.page_label.setText(f"Página {self.page + 1}")
        self.scans_metric.set_value(len(scans))
        self.scans_metric.set_detail(f"Página {self.page + 1}")
        self._update_navigation(scan_count=len(scans), threat_count=0)

    def _load_selected_scan(self):
        row = self.scan_table.currentRow()
        if row < 0:
            return
        item = self.scan_table.item(row, 0)
        if item is None:
            return

        self.selected_scan_id = item.data(Qt.UserRole)
        self.selected_scan = item.data(Qt.UserRole + 1)
        self.threat_page = 0
        self.load_scan_details()

    def load_scan_details(self):
        if not self.selected_scan_id:
            return

        try:
            threats = self.scan_controller.get_scan_threats(
                self.selected_scan_id,
                limit=self.THREAT_PAGE_SIZE,
                offset=self.threat_page * self.THREAT_PAGE_SIZE,
            )
        except Exception as exc:
            self._show_error(
                f"Falha ao carregar detalhes do scan {self.selected_scan_id}:\n{exc}"
            )
            return

        scan = self.selected_scan
        if scan is None:
            self.details_label.setText("O scan selecionado não existe mais.")
            self.threat_table.setRowCount(0)
            return

        error_text = f" | Erro: {scan.error_message}" if scan.error_message else ""
        self.details_label.setText(
            f"Scan #{scan.id} | Fim: {scan.end_time or '—'} | "
            f"Tratadas: {scan.treated_threats} | Falhas: {scan.failed_files}"
            f"{error_text}"
        )
        self.threats_metric.set_value(scan.threat_count or 0)
        self.threats_metric.set_detail(f"Scan #{scan.id}")
        self.result_metric.set_value(str(scan.status or "—"))
        self.result_metric.set_detail(self._scan_type_label(scan.scan_type))
        self._populate_threats(threats)

    def _populate_threats(self, threats):
        self.threat_table.setRowCount(0)
        for threat in threats:
            row = self.threat_table.rowCount()
            self.threat_table.insertRow(row)
            values = (
                threat.detection_time or "—",
                threat.virus_name or "desconhecida",
                threat.action or "—",
                threat.file_path or "—",
            )
            for column, value in enumerate(values):
                self.threat_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(str(value)),
                )

        self.threat_page_label.setText(f"Página {self.threat_page + 1}")
        self._update_navigation(
            scan_count=self.scan_table.rowCount(),
            threat_count=len(threats),
        )

    def previous_page(self):
        if self.page > 0:
            self.page -= 1
            self.load_scan_history()

    def next_page(self):
        if self.scan_table.rowCount() == self.PAGE_SIZE:
            self.page += 1
            self.load_scan_history()

    def previous_threat_page(self):
        if self.selected_scan_id and self.threat_page > 0:
            self.threat_page -= 1
            self.load_scan_details()

    def next_threat_page(self):
        if (
            self.selected_scan_id
            and self.threat_table.rowCount() == self.THREAT_PAGE_SIZE
        ):
            self.threat_page += 1
            self.load_scan_details()

    def _update_navigation(self, scan_count, threat_count):
        self.previous_button.setEnabled(self.page > 0)
        self.next_button.setEnabled(scan_count == self.PAGE_SIZE)
        self.previous_threat_button.setEnabled(self.threat_page > 0)
        self.next_threat_button.setEnabled(
            bool(self.selected_scan_id)
            and threat_count == self.THREAT_PAGE_SIZE
        )

    def _show_error(self, message):
        QMessageBox.critical(self, "Erro", message)

    def _scan_type_label(self, scan_type):
        normalized = str(scan_type or "").strip().lower()
        return self.SCAN_TYPE_LABELS.get(normalized, normalized or "—")
