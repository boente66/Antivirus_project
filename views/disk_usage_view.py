from PyQt5 import QtWidgets, QtCore
from PyQt5.QtChart import QChart, QChartView, QPieSeries
from PyQt5.QtGui import QPainter

from controllers.disk_usage_controller import DiskUsageController
from workers.disk_usage_worker import DiskUsageWorker


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
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        # -----------------------------------
        # Seleção de disco
        # -----------------------------------

        selector_layout = QtWidgets.QHBoxLayout()

        label = QtWidgets.QLabel("Escolha o disco:")

        self.volume_combo = QtWidgets.QComboBox()
        self.volume_combo.currentIndexChanged.connect(
            self.load_volume_data
        )

        selector_layout.addWidget(label)
        selector_layout.addWidget(self.volume_combo)

        main_layout.addLayout(selector_layout)

        # -----------------------------------
        # Resumo do disco
        # -----------------------------------

        self.summary_label = QtWidgets.QLabel("Selecione um disco")
        self.summary_label.setAlignment(QtCore.Qt.AlignCenter)

        self.summary_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
        """)

        main_layout.addWidget(self.summary_label)

        # -----------------------------------
        # Barra uso disco
        # -----------------------------------

        self.usage_bar = QtWidgets.QProgressBar()
        self.usage_bar.setValue(0)
        self.usage_bar.setFormat("%p% usado")

        main_layout.addWidget(self.usage_bar)

        # -----------------------------------
        # Status scan
        # -----------------------------------

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)

        main_layout.addWidget(self.status_label)

        # -----------------------------------
        # progresso scan
        # -----------------------------------

        self.scan_progress = QtWidgets.QProgressBar()
        self.scan_progress.setValue(0)

        main_layout.addWidget(self.scan_progress)

        # -----------------------------------
        # botão cancelar
        # -----------------------------------

        self.cancel_button = QtWidgets.QPushButton(
            "Cancelar análise"
        )

        self.cancel_button.clicked.connect(self.cancel_scan)
        self.cancel_button.setEnabled(False)

        main_layout.addWidget(self.cancel_button)

        # -----------------------------------
        # gráfico
        # -----------------------------------

        self.chart_container = QtWidgets.QVBoxLayout()
        main_layout.addLayout(self.chart_container)

        # -----------------------------------
        # tabela diretórios
        # -----------------------------------

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

        main_layout.addWidget(self.table)

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
