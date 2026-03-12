"""Panel showing the list of all labels in the template."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel,
)
from PySide6.QtCore import Signal

from src.models.label_data import LabelData


class LabelListPanel(QWidget):
    """Table of all labels with add/remove/duplicate/fill controls."""

    label_selected = Signal(int)    # emits index
    add_requested = Signal()
    remove_requested = Signal(int)  # emits index
    duplicate_requested = Signal(int)
    fill_sheet_requested = Signal()
    bulk_search_requested = Signal()
    import_csv_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Section header
        header = QLabel("Labels")
        header.setProperty("cssClass", "section-header")
        layout.addWidget(header)

        # Top button row: add/remove/dup/fill
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self._add_btn = QPushButton("+ Add")
        self._add_btn.clicked.connect(self.add_requested.emit)
        btn_row.addWidget(self._add_btn)

        self._dup_btn = QPushButton("Duplicate")
        self._dup_btn.setProperty("cssClass", "secondary")
        self._dup_btn.clicked.connect(self._on_duplicate)
        btn_row.addWidget(self._dup_btn)

        self._remove_btn = QPushButton("- Remove")
        self._remove_btn.setProperty("cssClass", "danger")
        self._remove_btn.clicked.connect(self._on_remove)
        btn_row.addWidget(self._remove_btn)

        self._fill_btn = QPushButton("Fill Sheet")
        self._fill_btn.setProperty("cssClass", "secondary")
        self._fill_btn.clicked.connect(self.fill_sheet_requested.emit)
        btn_row.addWidget(self._fill_btn)

        layout.addLayout(btn_row)

        # Second row: search parts + import CSV
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(4)

        self._search_btn = QPushButton("Search Parts...")
        self._search_btn.clicked.connect(self.bulk_search_requested.emit)
        btn_row2.addWidget(self._search_btn)

        self._import_btn = QPushButton("Import CSV/Excel...")
        self._import_btn.setProperty("cssClass", "secondary")
        self._import_btn.clicked.connect(self.import_csv_requested.emit)
        btn_row2.addWidget(self._import_btn)

        layout.addLayout(btn_row2)

        # Table
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Brennan P/N", "Customer P/N", "Description"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self._table)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        self.label_selected.emit(row)

    def _on_remove(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self.remove_requested.emit(row)

    def _on_duplicate(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self.duplicate_requested.emit(row)

    def update_labels(self, labels: list[LabelData], selected_index: int = -1) -> None:
        """Refresh the table with the current label list."""
        self._table.setRowCount(len(labels))
        for i, label in enumerate(labels):
            self._table.setItem(i, 0, QTableWidgetItem(label.brennan_part_number))
            self._table.setItem(i, 1, QTableWidgetItem(label.customer_part_number))
            self._table.setItem(i, 2, QTableWidgetItem(label.description))

        if 0 <= selected_index < len(labels):
            self._table.selectRow(selected_index)

    def get_selected_index(self) -> int:
        return self._table.currentRow()
