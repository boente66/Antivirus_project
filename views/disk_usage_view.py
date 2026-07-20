from PyQt5 import QtWidgets, QtCore
from PyQt5.QtChart import QChart, QChartView, QPieSeries
from PyQt5.QtGui import QPainter

from controllers.disk_usage_controller import DiskUsageController
from workers.disk_usage_worker import DiskUsageWorker
from views.components import CardFrame, MetricCard


class DiskUsageView(QtWidgets.QWidget):

    def __init__(self):

        super().__init__()

        self.controller = DiskUsageController()
        self.volumes = []

        self.thread = None
        self.worker = None

        self._build_ui()

        self.load_volumes()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def _build_ui(self):

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 4, 0, 0)
        main_layout.setSpacing(12)

        # -----------------------------------
        # Seleção de disco
        # -----------------------------------

        top_card = CardFrame()
        selector_layout = QtWidgets.QHBoxLayout(top_card)
        selector_layout.setContentsMargins(14, 12, 14, 12)

        label = QtWidgets.QLabel("Escolha o disco:")

        self.volume_combo = QtWidgets.QComboBox()
        self.volume_combo.currentIndexChanged.connect(
            self.load_volume_data
        )

        selector_layout.addWidget(label)
        selector_layout.addWidget(self.volume_combo)

        main_layout.addWidget(top_card)

        # -----------------------------------
        # Resumo do disco
        # -----------------------------------

        metrics = QtWidgets.QHBoxLayout()
        self.total_metric = MetricCard("Capacidade", "—", "Disco selecionado", "disk", "green")
        self.used_metric = MetricCard("Espaço usado", "—", "Aguardando dados", "disk", "blue")
        self.free_metric = MetricCard("Espaço livre", "—", "Aguardando dados", "folder", "purple")
        metrics.addWidget(self.total_metric)
        metrics.addWidget(self.used_metric)
        metrics.addWidget(self.free_metric)
        main_layout.addLayout(metrics)

        self.summary_label = QtWidgets.QLabel("Selecione um disco")
        self.summary_label.setProperty("muted", True)
        self.summary_label.setWordWrap(True)

        # -----------------------------------
        # Barra uso disco
        # -----------------------------------

        self.usage_bar = QtWidgets.QProgressBar()
        self.usage_bar.setValue(0)
        self.usage_bar.setFormat("%p% usado")

        top_card.layout().addWidget(self.usage_bar)

        # -----------------------------------
        # Status scan
        # -----------------------------------

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)

        top_card.layout().addWidget(self.status_label)

        # -----------------------------------
        # progresso scan
        # -----------------------------------

        self.scan_progress = QtWidgets.QProgressBar()
        self.scan_progress.setValue(0)

        top_card.layout().addWidget(self.scan_progress)

        # -----------------------------------
        # botão cancelar
        # -----------------------------------

        self.cancel_button = QtWidgets.QPushButton(
            "Cancelar análise"
        )

        self.cancel_button.clicked.connect(self.cancel_scan)
        self.cancel_button.setEnabled(False)

        self.cancel_button.setProperty("role", "danger")
        top_card.layout().addWidget(self.cancel_button)

        content = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        content.setChildrenCollapsible(False)
        chart_card = CardFrame()
        chart_layout = QtWidgets.QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(14, 12, 14, 14)
        chart_title = QtWidgets.QLabel("Distribuição do disco")
        chart_title.setObjectName("SectionTitle")
        chart_layout.addWidget(chart_title)

        # -----------------------------------
        # gráfico
        # -----------------------------------

        self.chart_container = QtWidgets.QVBoxLayout()
        chart_layout.addLayout(self.chart_container)
        content.addWidget(chart_card)

        # -----------------------------------
        # tabela diretórios
        # -----------------------------------

        table_card = CardFrame()
        table_layout = QtWidgets.QVBoxLayout(table_card)
        table_layout.setContentsMargins(14, 12, 14, 14)
        table_title = QtWidgets.QLabel("Pastas e arquivos por tamanho")
        table_title.setObjectName("SectionTitle")
        table_layout.addWidget(table_title)
        self.table = QtWidgets.QTableWidget()

        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(
            ["Diretório", "Tamanho"]
        )

        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)

        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )

        table_layout.addWidget(self.table)
        content.addWidget(table_card)
        content.setSizes([430, 570])
        self.content_splitter = content
        main_layout.addWidget(content, 1)

    # --------------------------------------------------
    # Conversão tamanho
    # --------------------------------------------------

    def _format_size(self, size):

        for unit in ["B", "KB", "MB", "GB", "TB"]:

            if size < 1024:
                return f"{size:.2f} {unit}"

            size /= 1024

        return f"{size:.2f} PB"

    # --------------------------------------------------
    # carregar volumes
    # --------------------------------------------------

    def load_volumes(self):

        try:

            volumes = self.controller.get_volumes()

            self.volumes = volumes

            self.volume_combo.clear()

            for volume in volumes:

                label = f"{volume['mountpoint']} ({volume['percent']}%)"

                self.volume_combo.addItem(label)

            if volumes:
                self.load_volume_data()

        except Exception as e:

            QtWidgets.QMessageBox.critical(
                self,
                "Erro",
                str(e)
            )

    # --------------------------------------------------
    # carregar dados volume
    # --------------------------------------------------

    def load_volume_data(self):

        index = self.volume_combo.currentIndex()

        if index < 0:
            return

        volume = self.volumes[index]

        mountpoint = volume["mountpoint"]

        try:

            summary = self.controller.get_volume_summary(
                mountpoint
            )

        except Exception as e:

            QtWidgets.QMessageBox.critical(
                self,
                "Erro",
                str(e)
            )

            return

        total = summary["total"]
        used = summary["used"]
        free = summary["free"]
        percent = summary["percent"]

        self.summary_label.setText(
            f"Total: {self._format_size(total)} | "
            f"Usado: {self._format_size(used)} | "
            f"Livre: {self._format_size(free)}"
        )
        self.total_metric.set_value(self._format_size(total))
        self.used_metric.set_value(self._format_size(used))
        self.used_metric.set_detail(f"{percent:.1f}% da capacidade")
        self.free_metric.set_value(self._format_size(free))
        self.free_metric.set_detail("Disponível no volume")

        self.usage_bar.setValue(int(round(percent)))

        self._update_chart(used, free)

        self.start_scan(mountpoint)

    # --------------------------------------------------
    # iniciar scan thread
    # --------------------------------------------------

    def start_scan(self, mountpoint):

        if self.thread:
            return

        self.scan_progress.setValue(0)
        self.status_label.setText("Iniciando análise...")

        self.thread = QtCore.QThread()

        self.worker = DiskUsageWorker(
            self.controller,
            mountpoint
        )

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.progress.connect(
            self.scan_progress.setValue
        )

        self.worker.status.connect(
            self.status_label.setText
        )

        self.worker.finished.connect(
            self.on_scan_finished
        )

        self.worker.error.connect(
            self.show_error
        )

        self.worker.finished.connect(self.thread.quit)

        self.thread.finished.connect(self._cleanup_thread)

        self.thread.start()

        self.cancel_button.setEnabled(True)

    # --------------------------------------------------
    # cleanup thread
    # --------------------------------------------------

    def _cleanup_thread(self):

        if self.thread:

            self.thread.deleteLater()

        self.thread = None
        self.worker = None

    # --------------------------------------------------
    # cancelar scan
    # --------------------------------------------------

    def cancel_scan(self):

        if self.worker:
            self.worker.cancel()

        self.status_label.setText("Análise cancelada")

        self.cancel_button.setEnabled(False)

    # --------------------------------------------------
    # scan terminado
    # --------------------------------------------------

    def on_scan_finished(self, result):

        breakdown = result["breakdown"]

        self._load_table(breakdown)

        self.scan_progress.setValue(100)

        self.status_label.setText("Análise concluída")

        self.cancel_button.setEnabled(False)

    # --------------------------------------------------
    # atualizar gráfico
    # --------------------------------------------------

    def _update_chart(self, used, free):

        while self.chart_container.count():

            item = self.chart_container.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

        series = QPieSeries()

        used_slice = series.append("Usado", used)
        free_slice = series.append("Livre", free)

        used_slice.setLabelVisible(True)
        free_slice.setLabelVisible(True)

        chart = QChart()
        chart.addSeries(series)

        chart.setTitle("Uso do Disco")

        chart.legend().setVisible(True)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        self.chart_container.addWidget(chart_view)

    # --------------------------------------------------
    # carregar tabela
    # --------------------------------------------------

    def _load_table(self, breakdown):

        self.table.setRowCount(len(breakdown))

        for i, item in enumerate(breakdown):

            name = item["name"]
            size = self._format_size(item["size"])

            self.table.setItem(
                i,
                0,
                QtWidgets.QTableWidgetItem(name)
            )

            self.table.setItem(
                i,
                1,
                QtWidgets.QTableWidgetItem(size)
            )

    # --------------------------------------------------
    # erro
    # --------------------------------------------------

    def show_error(self, message):

        QtWidgets.QMessageBox.critical(
            self,
            "Erro",
            message
        )

    def resizeEvent(self, event):
        self.content_splitter.setOrientation(
            QtCore.Qt.Vertical if self.width() < 820 else QtCore.Qt.Horizontal
        )
        super().resizeEvent(event)
