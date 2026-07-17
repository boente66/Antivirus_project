# views/quarantine_view.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QMessageBox, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView
)

from PyQt5.QtCore import Qt
from datetime import datetime
import os

from utils.icon_loader import get_icon


class QuarantineView(QWidget):

    def __init__(self, controller):
        super().__init__()

        self.controller = controller

        self._build_ui()
        self._connect_signals()

        self.refresh()

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):

        self.setWindowTitle("Quarentena")
        self.setMinimumWidth(650)

        layout = QVBoxLayout(self)

        # --------------------------------------------------
        # Título
        # --------------------------------------------------

        title = QLabel("Arquivos em Quarentena")
        title.setStyleSheet(
            "font-size:20px;font-weight:bold;"
        )

        layout.addWidget(title)

        # --------------------------------------------------
        # Tabela
        # --------------------------------------------------

        self.table = QTableWidget(0, 5)

        self.table.setHorizontalHeaderLabels([
            "Arquivo",
            "Caminho original",
            "Ameaça",
            "Data",
            "Status/Ação"
        ])

        self.table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()

        header.setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )

        header.setSectionResizeMode(
            1, QHeaderView.Stretch
        )

        header.setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )

        header.setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )

        header.setSectionResizeMode(
            4, QHeaderView.ResizeToContents
        )

        layout.addWidget(self.table)

        # --------------------------------------------------
        # Botões
        # --------------------------------------------------

        btn_layout = QHBoxLayout()

        self.restore_btn = QPushButton("Restaurar")
        self.restore_btn.setIcon(get_icon("restore"))

        self.delete_btn = QPushButton(
            "Excluir Definitivamente"
        )

        self.delete_btn.setIcon(get_icon("delete"))

        btn_layout.addWidget(self.restore_btn)
        btn_layout.addWidget(self.delete_btn)

        layout.addLayout(btn_layout)

    # ======================================================
    # SIGNALS
    # ======================================================

    def _connect_signals(self):

        self.restore_btn.clicked.connect(
            self.restore_selected
        )

        self.delete_btn.clicked.connect(
            self.delete_selected
        )

        self.controller.item_added.connect(self.refresh)
        self.controller.item_removed.connect(self.refresh)
        self.controller.items_refreshed.connect(self._populate)
        self.controller.error.connect(self.show_error)

    # ======================================================
    # REFRESH
    # ======================================================

    def refresh(self):
        self._populate(self.controller.get_items())

    def _populate(self, items):

        self.table.setRowCount(0)

        if not items:

            self.restore_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

            return

        self.restore_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

        items = sorted(
            items,
            key=lambda x: getattr(
                x, "date", None
            ) or getattr(
                x, "timestamp", None
            ) or "",
            reverse=True
        )

        for item in items:

            row = self.table.rowCount()

            self.table.insertRow(row)

            filename, path, threat, date, status = self._extract_data(
                item
            )

            file_item = QTableWidgetItem(filename)

            file_item.setIcon(
                get_icon("virus")
            )

            file_item.setData(
                Qt.UserRole,
                item
            )

            self.table.setItem(
                row, 0, file_item
            )

            self.table.setItem(
                row, 1,
                QTableWidgetItem(path)
            )

            self.table.setItem(
                row, 2,
                QTableWidgetItem(threat)
            )

            self.table.setItem(
                row, 3,
                QTableWidgetItem(date)
            )

            self.table.setItem(
                row, 4,
                QTableWidgetItem(status)
            )

    # ======================================================
    # EXTRAÇÃO
    # ======================================================

    def _extract_data(self, item):

        if isinstance(item, dict):

            path = item.get(
                "original_path"
            ) or item.get(
                "path"
            ) or ""

            date = item.get(
                "date"
            ) or item.get(
                "timestamp"
            )

            threat = item.get("virus_name") or ""
            status = item.get("action") or item.get("status") or ""

        else:

            path = getattr(
                item,
                "original_path",
                None
            ) or getattr(
                item,
                "path",
                ""
            )

            date = getattr(
                item,
                "date",
                None
            ) or getattr(
                item,
                "timestamp",
                None
            )

            threat = getattr(item, "virus_name", "") or ""
            status = (
                getattr(item, "action", None)
                or getattr(item, "status", "")
                or ""
            )

        filename = os.path.basename(path)

        if isinstance(date, datetime):

            date = date.isoformat(
                sep=" ",
                timespec="seconds"
            )

        else:

            date = str(date) if date else ""

        return filename, path, threat, date, status

    # ======================================================
    # SELEÇÃO
    # ======================================================

    def _get_selected_item(self):

        row = self.table.currentRow()

        if row < 0:
            return None

        item = self.table.item(row, 0)

        if not item:
            return None

        return item.data(Qt.UserRole)

    # ======================================================
    # ACTIONS
    # ======================================================

    def restore_selected(self):

        item = self._get_selected_item()

        if not item:
            QMessageBox.warning(
                self,
                "Restaurar Arquivo",
                "Selecione um item da quarentena."
            )
            return

        confirm = QMessageBox.question(
            self,
            "Restaurar Arquivo",
            "Tem certeza que deseja restaurar este arquivo?\n\n"
            "Ele voltará ao local original.",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:

            self.controller.restore_item(item)

    # ------------------------------------------------------

    def delete_selected(self):

        item = self._get_selected_item()

        if not item:
            QMessageBox.warning(
                self,
                "Excluir Definitivamente",
                "Selecione um item da quarentena."
            )
            return

        confirm = QMessageBox.question(
            self,
            "Excluir Definitivamente",
            "Esta ação NÃO pode ser desfeita.\n\n"
            "Deseja excluir permanentemente este arquivo?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:

            self.controller.delete_item(item, confirmed=True)

    # ======================================================
    # ERROR
    # ======================================================

    def show_error(self, msg):

        QMessageBox.critical(
            self,
            "Erro",
            str(msg)
        )
