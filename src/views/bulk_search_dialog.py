"""Dialog for searching and selecting multiple parts from the data source."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
    QDialogButtonBox, QCheckBox, QWidget, QComboBox, QApplication,
)
from PySide6.QtCore import Qt

from src.services.data_source import (
    DataSource, SEARCH_CONTAINS, SEARCH_EXACT, SEARCH_STARTS_WITH,
)


class BulkSearchDialog(QDialog):
    """Search for parts and select multiple to add as labels."""

    def __init__(self, data_source: DataSource, parent=None):
        super().__init__(parent)
        self.data_source = data_source
        self._results: list[dict] = []
        self._selected: list[dict] = []

        self.setWindowTitle("Search & Add Parts — Catsy PIM")
        self.setMinimumSize(750, 500)
        self.resize(950, 650)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Search bar: mode selector + input + button
        search_row = QHBoxLayout()
        search_row.setSpacing(4)

        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Contains", SEARCH_CONTAINS)
        self._mode_combo.addItem("Exact Match", SEARCH_EXACT)
        self._mode_combo.addItem("Starts With", SEARCH_STARTS_WITH)
        self._mode_combo.setFixedWidth(120)
        search_row.addWidget(self._mode_combo)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Enter Brennan part number (e.g. 2404, FS6564)...")
        self._search_input.returnPressed.connect(self._do_search)
        search_row.addWidget(self._search_input, 1)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._do_search)
        search_row.addWidget(search_btn)
        layout.addLayout(search_row)

        # Select all / none + result count
        select_row = QHBoxLayout()
        self._result_count = QLabel("")
        self._result_count.setStyleSheet("font-weight: 500; color: #555;")
        select_row.addWidget(self._result_count)
        select_row.addStretch()

        select_all_btn = QPushButton("Select All")
        select_all_btn.setProperty("cssClass", "secondary")
        select_all_btn.clicked.connect(self._select_all)
        select_row.addWidget(select_all_btn)

        select_none_btn = QPushButton("Select None")
        select_none_btn.setProperty("cssClass", "secondary")
        select_none_btn.clicked.connect(self._select_none)
        select_row.addWidget(select_none_btn)
        layout.addLayout(select_row)

        # Results table: checkbox, Part#, Description, Series, Material, Xref P/N
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            "", "Brennan P/N", "Description", "Series", "Material", "Xref P/N",
        ])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 30)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        # Dialog buttons
        btn_row = QHBoxLayout()
        self._add_count_label = QLabel("")
        self._add_count_label.setStyleSheet("font-weight: 600; color: #006293;")
        btn_row.addWidget(self._add_count_label)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("cssClass", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._add_btn = QPushButton("Add Selected to Labels")
        self._add_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(self._add_btn)
        layout.addLayout(btn_row)

    def _do_search(self) -> None:
        query = self._search_input.text().strip()
        if not query:
            return

        mode = self._mode_combo.currentData()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._results = self.data_source.search_parts(query, mode)
        finally:
            QApplication.restoreOverrideCursor()
        self._populate_table()

    def _populate_table(self) -> None:
        self._table.setRowCount(len(self._results))
        for i, part in enumerate(self._results):
            # Checkbox
            cb = QCheckBox()
            cb.stateChanged.connect(self._update_add_count)
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self._table.setCellWidget(i, 0, cb_widget)

            self._table.setItem(i, 1, QTableWidgetItem(part.get("brennan_part_number", "")))
            self._table.setItem(i, 2, QTableWidgetItem(part.get("description", "")))
            self._table.setItem(i, 3, QTableWidgetItem(part.get("series", "")))
            self._table.setItem(i, 4, QTableWidgetItem(part.get("material", "")))
            self._table.setItem(i, 5, QTableWidgetItem(part.get("customer_part_number", "")))

        count = len(self._results)
        self._result_count.setText(f"{count} result{'s' if count != 1 else ''} found")
        self._update_add_count()

    def _checked_count(self) -> int:
        count = 0
        for i in range(self._table.rowCount()):
            widget = self._table.cellWidget(i, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    count += 1
        return count

    def _update_add_count(self) -> None:
        n = self._checked_count()
        if n:
            self._add_count_label.setText(f"{n} part{'s' if n != 1 else ''} selected")
        else:
            self._add_count_label.setText("")

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
