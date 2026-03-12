"""Dialog for searching and selecting multiple parts from the data source."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
    QDialogButtonBox, QCheckBox, QWidget,
)
from PySide6.QtCore import Qt

from src.services.data_source import DataSource


class BulkSearchDialog(QDialog):
    """Search for parts and select multiple to add as labels."""

    def __init__(self, data_source: DataSource, parent=None):
        super().__init__(parent)
        self.data_source = data_source
        self._results: list[dict] = []
        self._selected: list[dict] = []

        self.setWindowTitle("Search & Add Parts")
        self.setMinimumSize(650, 500)
        self.resize(700, 550)

        layout = QVBoxLayout(self)

        # Search bar
        search_row = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search by part number, customer number, or description...")
        self._search_input.returnPressed.connect(self._do_search)
        search_row.addWidget(self._search_input, 1)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._do_search)
        search_row.addWidget(search_btn)
        layout.addLayout(search_row)

        # Select all / none
        select_row = QHBoxLayout()
        self._result_count = QLabel("")
        select_row.addWidget(self._result_count)
        select_row.addStretch()

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        select_row.addWidget(select_all_btn)

        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self._select_none)
        select_row.addWidget(select_none_btn)
        layout.addLayout(select_row)

        # Results table with checkboxes
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["", "Brennan P/N", "Customer P/N", "Description"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 30)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._table)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _do_search(self) -> None:
        query = self._search_input.text().strip()
        if not query:
            return
        self._results = self.data_source.search_parts(query)
        self._populate_table()

    def _populate_table(self) -> None:
        self._table.setRowCount(len(self._results))
        for i, part in enumerate(self._results):
            # Checkbox
            cb = QCheckBox()
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self._table.setCellWidget(i, 0, cb_widget)

            self._table.setItem(i, 1, QTableWidgetItem(part.get("brennan_part_number", "")))
            self._table.setItem(i, 2, QTableWidgetItem(part.get("customer_part_number", "")))
            self._table.setItem(i, 3, QTableWidgetItem(part.get("description", "")))

        count = len(self._results)
        self._result_count.setText(f"{count} result{'s' if count != 1 else ''} found")

    def _select_all(self) -> None:
        for i in range(self._table.rowCount()):
            widget = self._table.cellWidget(i, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(True)

    def _select_none(self) -> None:
        for i in range(self._table.rowCount()):
            widget = self._table.cellWidget(i, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(False)

    def _on_accept(self) -> None:
        self._selected = []
        for i in range(self._table.rowCount()):
            widget = self._table.cellWidget(i, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and cb.isChecked() and i < len(self._results):
                    self._selected.append(self._results[i])
        self.accept()

    def get_selected_parts(self) -> list[dict]:
        return self._selected
