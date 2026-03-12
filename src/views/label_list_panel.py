"""Panel showing the list of all labels in the template with inline editing."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel,
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence, QShortcut

from src.models.label_data import LabelData


class LabelListPanel(QWidget):
    """Table of all labels with add/remove/duplicate/fill controls.

    Table cells are directly editable (double-click to edit).
    """

    label_selected = Signal(int)    # emits index when row clicked
    add_requested = Signal()
    remove_requested = Signal(int)  # emits index
    duplicate_requested = Signal(int)
    fill_sheet_requested = Signal()
    bulk_search_requested = Signal()
    import_csv_requested = Signal()
    label_edited = Signal(int, str, str)  # index, field_name, new_value

    # Column index to field name mapping
    _COL_FIELDS = {0: "brennan_pn", 1: "customer_pn", 2: "description"}

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Section header
        header = QLabel("Labels")
        header.setProperty("cssClass", "section-header")
        layout.addWidget(header)

        # Button row 1: search + import (primary actions)
        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(4)

        self._search_btn = QPushButton("Search Parts...")
        self._search_btn.setToolTip("Search the Catsy catalog and add parts (Ctrl+F)")
        self._search_btn.clicked.connect(self.bulk_search_requested.emit)
        btn_row1.addWidget(self._search_btn)

        self._import_btn = QPushButton("Import CSV/Excel...")
        self._import_btn.setProperty("cssClass", "secondary")
        self._import_btn.setToolTip("Import labels from a spreadsheet file (Ctrl+I)")
        self._import_btn.clicked.connect(self.import_csv_requested.emit)
        btn_row1.addWidget(self._import_btn)

        layout.addLayout(btn_row1)

        # Button row 2: add/dup/remove/fill
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(4)

        self._add_btn = QPushButton("+ Add")
        self._add_btn.setProperty("cssClass", "secondary")
        self._add_btn.setToolTip("Add a blank label row (Ctrl+Shift+A)")
        self._add_btn.clicked.connect(self.add_requested.emit)
        btn_row2.addWidget(self._add_btn)

        self._dup_btn = QPushButton("Duplicate")
        self._dup_btn.setProperty("cssClass", "secondary")
        self._dup_btn.setToolTip("Duplicate the selected label (Ctrl+D)")
        self._dup_btn.clicked.connect(self._on_duplicate)
        btn_row2.addWidget(self._dup_btn)

        self._remove_btn = QPushButton("- Remove")
        self._remove_btn.setProperty("cssClass", "danger")
        self._remove_btn.setToolTip("Remove the selected label (Delete)")
        self._remove_btn.clicked.connect(self._on_remove)
        btn_row2.addWidget(self._remove_btn)

        self._fill_btn = QPushButton("Fill Sheet")
        self._fill_btn.setProperty("cssClass", "secondary")
        self._fill_btn.setToolTip(
            "Fill remaining slots on the current page with\n"
            "copies of the selected label"
        )
        self._fill_btn.clicked.connect(self.fill_sheet_requested.emit)
        btn_row2.addWidget(self._fill_btn)

        layout.addLayout(btn_row2)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+F"), self, self.bulk_search_requested.emit)
        QShortcut(QKeySequence("Ctrl+Shift+A"), self, self.add_requested.emit)
        QShortcut(QKeySequence("Ctrl+D"), self, self._on_duplicate)
        QShortcut(QKeySequence("Delete"), self, self._on_remove)

        # Table — cells are editable by default
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(
            ["Brennan P/N", "Customer P/N", "Description"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.cellClicked.connect(self._on_cell_clicked)
        self._table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self._table)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        self.label_selected.emit(row)

    def _on_cell_changed(self, row: int, col: int) -> None:
        """Handle inline edits in the table."""
        if self._table.signalsBlocked():
            return
        field = self._COL_FIELDS.get(col)
        if field is None:
            return
        item = self._table.item(row, col)
        if item:
            self.label_edited.emit(row, field, item.text())

    def _on_remove(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self.remove_requested.emit(row)

    def _on_duplicate(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self.duplicate_requested.emit(row)

    def update_labels(self, labels: list[LabelData], selected_index: int = -1,
                      description_mode: str = "full") -> None:
        """Refresh the table with the current label list."""
        self._table.blockSignals(True)
        try:
            self._table.setRowCount(len(labels))
            for i, label in enumerate(labels):
                desc_text = label.get_display_description(description_mode)

                item0 = QTableWidgetItem(label.brennan_part_number)
                item0.setToolTip(label.brennan_part_number)
                self._table.setItem(i, 0, item0)

                item1 = QTableWidgetItem(label.customer_part_number)
                item1.setToolTip(label.customer_part_number)
                self._table.setItem(i, 1, item1)

                item2 = QTableWidgetItem(desc_text)
                item2.setToolTip(desc_text)
                self._table.setItem(i, 2, item2)

            if 0 <= selected_index < len(labels):
                self._table.selectRow(selected_index)
        finally:
            self._table.blockSignals(False)

    def get_selected_index(self) -> int:
        return self._table.currentRow()
