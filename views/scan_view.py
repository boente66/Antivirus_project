import os
from PyQt5 import QtWidgets, QtCore

from utils.icon_loader import get_icon


class ScanView(QtWidgets.QWidget):

    def __init__(self, parent=None, scan_controller=None):
        super().__init__(parent)

        if scan_controller is None:
            raise ValueError("ScanController não fornecido")

        self.scan_controller = scan_controller

        self._build_ui()
        self._connect_signals()

    # =====================================================
    # UI
    # =====================================================

    def _build_ui(self):

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # -------------------------
        # Título
        # -------------------------

        self.title_label = QtWidgets.QLabel("Aguardando verificação")
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)

        self.title_label.setStyleSheet(
            "font-size:22px;font-weight:bold;color:#264653;"
        )

        layout.addWidget(self.title_label)

        # -------------------------
        # Arquivo atual
        # -------------------------

        self.current_file_label = QtWidgets.QLabel("Arquivo atual: —")

        self.current_file_label.setStyleSheet(
            "font-size:13px;color:#555;"
        )

        layout.addWidget(self.current_file_label)

        # -------------------------
        # Log
        # -------------------------

        self.details_text = QtWidgets.QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMinimumHeight(140)

        layout.addWidget(self.details_text)

        # -------------------------
        # Barra progresso
        # -------------------------

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)

        layout.addWidget(self.progress_bar)

        self.percent_label = QtWidgets.QLabel("0%")
        self.percent_label.setAlignment(QtCore.Qt.AlignCenter)

        layout.addWidget(self.percent_label)

        # -------------------------
        # Cancelar
        # -------------------------

        self.cancel_button = QtWidgets.QPushButton("Cancelar verificação")
        self.cancel_button.setIcon(get_icon("stop"))

        self.cancel_button.clicked.connect(self.cancel_scan)
        self.cancel_button.setEnabled(False)

        layout.addWidget(self.cancel_button)

        # -------------------------
        # Tabela de ameaças
        # -------------------------

        self.threats_table = QtWidgets.QTableWidget(0, 4)

        self.threats_table.setHorizontalHeaderLabels([
            "Arquivo",
            "Caminho",
            "Ameaça",
            "Ação"
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

        layout.addWidget(self.threats_table)

    # =====================================================
    # SINAIS
    # =====================================================

    def _connect_signals(self):

        c = self.scan_controller

        c.scan_started.connect(self.on_scan_started)
        c.progress_updated.connect(self.on_progress)
        c.current_file_changed.connect(self.on_current_file)
        c.threat_detected.connect(self.on_threat_detected)
        c.scan_error.connect(self.on_scan_error)
        c.scan_finished.connect(self.on_scan_finished)

    # =====================================================
    # CALLBACKS
    # =====================================================

    def on_scan_started(self):

        self.title_label.setText("Verificação em andamento…")

        self.details_text.clear()
        self.threats_table.setRowCount(0)

        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")

        self.cancel_button.setEnabled(True)

        self.log("Verificação iniciada.")

    def on_progress(self, value: int):

        try:
            value = max(0, min(100, int(value)))
        except Exception:
            value = 0

        self.progress_bar.setValue(value)
        self.percent_label.setText(f"{value}%")

    def on_current_file(self, file_path: str):

        if not file_path:
            return

        name = os.path.basename(file_path)

        self.current_file_label.setText(
            f"Arquivo atual: {name}"
        )

        self.log(f"Escaneando: {file_path}")

    def on_threat_detected(self, result):

        try:

            if not result or not getattr(result, "infected", False):
                return

            file_path = getattr(result.detected_file, "path", "desconhecido")
            virus_name = getattr(result.virus, "name", "desconhecido")
            action = getattr(result, "action", None) or "-"

            row = self.threats_table.rowCount()
            self.threats_table.insertRow(row)

            # Ícone
            icon_name = "virus"

            if "HEURISTIC" in virus_name:
                icon_name = "warning"

            file_item = QtWidgets.QTableWidgetItem(
                os.path.basename(file_path)
            )

            file_item.setIcon(get_icon(icon_name))

            self.threats_table.setItem(row, 0, file_item)

            self.threats_table.setItem(
                row, 1,
                QtWidgets.QTableWidgetItem(file_path)
            )

            self.threats_table.setItem(
                row, 2,
                QtWidgets.QTableWidgetItem(virus_name)
            )

            self.threats_table.setItem(
                row, 3,
                QtWidgets.QTableWidgetItem(action)
            )

            self.log(f"⚠ Ameaça detectada: {virus_name}")

        except Exception:
            pass

    def on_scan_error(self, message: str):

        if not message:
            message = "Erro desconhecido durante a verificação."

        self.log(f"❌ Erro durante o scan: {message}")

        QtWidgets.QMessageBox.critical(
            self,
            "Erro de verificação",
            message
        )

    def on_scan_finished(self, results: list):

        infected = 0

        try:
            infected = len([
                r for r in results
                if getattr(r, "infected", False)
            ])
        except Exception:
            infected = 0

        self.title_label.setText("Verificação concluída")

        self.current_file_label.setText("Arquivo atual: —")

        self.progress_bar.setValue(100)
        self.percent_label.setText("100%")

        self.cancel_button.setEnabled(False)

        self.log("Verificação finalizada.")
        self.log(f"Ameaças detectadas: {infected}")

        QtWidgets.QMessageBox.information(
            self,
            "Scan concluído",
            f"Verificação finalizada.\nAmeaças encontradas: {infected}"
        )

    # =====================================================
    # UTIL
    # =====================================================

    def log(self, message: str):

        if not message:
            return

        self.details_text.append(message)

        # evita crescer infinito
        if self.details_text.document().blockCount() > 500:
            cursor = self.details_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()

        scrollbar = self.details_text.verticalScrollBar()

        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    # =====================================================
    # CONTROLE
    # =====================================================

    def cancel_scan(self):

        self.log("Cancelando verificação…")

        self.title_label.setText("Verificação cancelada")

        self.cancel_button.setEnabled(False)

        try:
            self.scan_controller.interrupt_scan()
        except Exception:
            pass

    # =====================================================
    # CLEANUP
    # =====================================================

    def closeEvent(self, event):

        try:

            c = self.scan_controller

            c.scan_started.disconnect(self.on_scan_started)
            c.progress_updated.disconnect(self.on_progress)
            c.current_file_changed.disconnect(self.on_current_file)
            c.threat_detected.disconnect(self.on_threat_detected)
            c.scan_error.disconnect(self.on_scan_error)
            c.scan_finished.disconnect(self.on_scan_finished)

        except Exception:
            pass

        event.accept()
