"""Dialog for searching and selecting multiple parts from the data source."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
    QCheckBox, QWidget, QComboBox, QApplication,
)
from PySide6.QtCore import Qt

from src.services.data_source import (
    DataSource, SEARCH_CONTAINS, SEARCH_EXACT, SEARCH_STARTS_WITH,
)


class BulkSearchDialog(QDialog):
    """Search for parts and select multiple to add as labels."""

    def __init__(self, data_source: DataSource, xref_key: str = "", parent=None):
        super().__init__(parent)
        self.data_source = data_source
        self._xref_key = xref_key
        self._results: list[dict] = []
        self._selected: list[dict] = []
        self._checked: int = 0  # running count of checked items

        self.setWindowTitle("Search & Add Parts \u2014 Catsy PIM")
        self.setMinimumSize(750, 500)
        self.resize(950, 650)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Search bar: mode selector + input + button
        search_row = QHBoxLayout()
        search_row.setSpacing(4)

        self._mode_combo = QComboBox()
        self._mode_combo.setToolTip(
            "Contains: part number includes the search text\n"
            "Exact Match: part number matches exactly\n"
            "Starts With: part number begins with the search text"
        )
        self._mode_combo.addItem("Contains", SEARCH_CONTAINS)
        self._mode_combo.addItem("Exact Match", SEARCH_EXACT)
        self._mode_combo.addItem("Starts With", SEARCH_STARTS_WITH)
        search_row.addWidget(self._mode_combo)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(
            "Enter Brennan part number (e.g. 2404, FS6564)..."
        )
        self._search_input.returnPressed.connect(self._do_search)
        search_row.addWidget(self._search_input, 1)

        search_btn = QPushButton("Search")
        search_btn.setToolTip("Search the Catsy catalog (Enter)")
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
        select_all_btn.setToolTip("Check all results")
        select_all_btn.clicked.connect(self._select_all)
        select_row.addWidget(select_all_btn)

        select_none_btn = QPushButton("Select None")
        select_none_btn.setProperty("cssClass", "secondary")
        select_none_btn.setToolTip("Uncheck all results")
        select_none_btn.clicked.connect(self._select_none)
        select_row.addWidget(select_none_btn)
        layout.addLayout(select_row)

        # Results table
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            "", "Brennan P/N", "Customer P/N",
            "Description", "Short Desc", "Material",
        ])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 30)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        # Empty state hint (shown when no results)
        self._empty_hint = QLabel(
            "No results. Try a different search term or mode."
        )
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint.setStyleSheet(
            "color: #999; font-style: italic; font-size: 13px; padding: 20px;"
        )
        self._empty_hint.setVisible(False)
        layout.addWidget(self._empty_hint)

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
        self._add_btn.setToolTip("Add all checked parts to your label sheet")
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
        except Exception as e:
            self._results = []
            QApplication.restoreOverrideCursor()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Search Error",
                f"Search failed:\n{e}\n\nCheck your network connection and try again.",
            )
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._populate_table()

    def _populate_table(self) -> None:
        self._checked = 0
        count = len(self._results)

        # Show/hide empty state
        self._empty_hint.setVisible(count == 0)
        self._table.setVisible(count > 0)

        self._table.setRowCount(count)
        for i, part in enumerate(self._results):
            # Checkbox
            cb = QCheckBox()
            cb.stateChanged.connect(self._on_check_toggled)
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self._table.setCellWidget(i, 0, cb_widget)

            pn = part.get("brennan_part_number", "")
            item1 = QTableWidgetItem(pn)
            item1.setToolTip(pn)
            self._table.setItem(i, 1, item1)

            # Resolve customer P/N from xrefs using selected manufacturer
            customer_pn = ""
            if self._xref_key:
                customer_pn = part.get("xrefs", {}).get(self._xref_key, "")
            if not customer_pn:
                customer_pn = part.get("customer_part_number", "")
            item2 = QTableWidgetItem(customer_pn)
            item2.setToolTip(customer_pn)
            self._table.setItem(i, 2, item2)

            desc = part.get("description", "")
            item3 = QTableWidgetItem(desc)
            item3.setToolTip(desc)
            self._table.setItem(i, 3, item3)

            short = part.get("short_description", "")
            item4 = QTableWidgetItem(short)
            item4.setToolTip(short)
            self._table.setItem(i, 4, item4)

            mat = part.get("material", "")
            self._table.setItem(i, 5, QTableWidgetItem(mat))

        self._result_count.setText(
            f"{count} result{'s' if count != 1 else ''} found"
        )
        self._update_add_count_label()

    def _on_check_toggled(self, state: int) -> None:
        """Update checked count incrementally instead of scanning all rows."""
        if state == Qt.CheckState.Checked.value:
            self._checked += 1
        else:
            self._checked = max(0, self._checked - 1)
        self._update_add_count_label()

    def _update_add_count_label(self) -> None:
        n = self._checked
        if n:
            self._add_count_label.setText(
                f"{n} part{'s' if n != 1 else ''} selected"
            )
        else:
            self._add_count_label.setText("")

    def _select_all(self) -> None:
        for i in range(self._table.rowCount()):
            widget = self._table.cellWidget(i, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and not cb.isChecked():
                    cb.setChecked(True)

    def _select_none(self) -> None:
        for i in range(self._table.rowCount()):
            widget = self._table.cellWidget(i, 0)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and cb.isChecked():
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
