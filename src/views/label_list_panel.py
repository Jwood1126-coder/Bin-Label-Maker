"""Panel showing the list of all labels in the template with inline editing."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut, QColor

from src.models.label_data import LabelData


class LabelListPanel(QWidget):
    """Table of all labels with add/remove/duplicate/fill controls.

    Table cells are directly editable (double-click to edit).
    Shows 4 columns: Brennan P/N, Customer P/N, Description, Short Desc.
    The description mode controls which column is printed, but both are
    always visible and editable.
    """

    label_selected = Signal(int)    # emits index when row clicked
    add_requested = Signal()
    remove_requested = Signal(int)  # emits index
    duplicate_requested = Signal(int)
    move_requested = Signal(int, int)  # index, direction (-1=up, 1=down)
    fill_sheet_requested = Signal()
    bulk_search_requested = Signal()
    import_csv_requested = Signal()
    label_edited = Signal(int, str, str)  # index, field_name, new_value

    # Column index to field name mapping
    _COL_FIELDS = {
        0: "brennan_pn",
        1: "customer_pn",
        2: "description",
        3: "short_description",
    }

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

        # Button row 3: reorder
        btn_row3 = QHBoxLayout()
        btn_row3.setSpacing(4)

        self._up_btn = QPushButton("\u25B2 Move Up")
        self._up_btn.setProperty("cssClass", "secondary")
        self._up_btn.setToolTip("Move selected label up (Alt+Up)")
        self._up_btn.clicked.connect(self._on_move_up)
        btn_row3.addWidget(self._up_btn)

        self._down_btn = QPushButton("\u25BC Move Down")
        self._down_btn.setProperty("cssClass", "secondary")
        self._down_btn.setToolTip("Move selected label down (Alt+Down)")
        self._down_btn.clicked.connect(self._on_move_down)
        btn_row3.addWidget(self._down_btn)

        btn_row3.addStretch()
        layout.addLayout(btn_row3)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+F"), self, self.bulk_search_requested.emit)
        QShortcut(QKeySequence("Ctrl+Shift+A"), self, self.add_requested.emit)
        QShortcut(QKeySequence("Ctrl+D"), self, self._on_duplicate)
        QShortcut(QKeySequence("Delete"), self, self._on_remove)
        QShortcut(QKeySequence("Alt+Up"), self, self._on_move_up)
        QShortcut(QKeySequence("Alt+Down"), self, self._on_move_down)

        # Table — 4 columns, all editable
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["Brennan P/N", "Customer P/N", "Description", "Short Desc"]
        )
        h = self._table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.cellClicked.connect(self._on_cell_clicked)
        self._table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self._table)

        # Track which description mode is active for visual emphasis
        self._active_desc_mode = "full"

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

    def _on_move_up(self) -> None:
        row = self._table.currentRow()
        if row > 0:
            self.move_requested.emit(row, -1)

    def _on_move_down(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self.move_requested.emit(row, 1)

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
        self._active_desc_mode = description_mode
        self._table.blockSignals(True)
        try:
            self._table.setRowCount(len(labels))
            # Visually indicate which description column is the "active" print column
            active_col = 2 if description_mode == "full" else 3
            inactive_col = 3 if description_mode == "full" else 2
            dimmed = QColor(160, 160, 160)

            for i, label in enumerate(labels):
                item0 = QTableWidgetItem(label.brennan_part_number)
                item0.setToolTip(label.brennan_part_number)
                self._table.setItem(i, 0, item0)

                item1 = QTableWidgetItem(label.customer_part_number)
                item1.setToolTip(label.customer_part_number)
                self._table.setItem(i, 1, item1)

                item2 = QTableWidgetItem(label.description)
                item2.setToolTip(label.description)
                self._table.setItem(i, 2, item2)

                item3 = QTableWidgetItem(label.short_description)
                item3.setToolTip(label.short_description)
                self._table.setItem(i, 3, item3)

                # Dim the inactive description column
                inactive_item = self._table.item(i, inactive_col)
                if inactive_item:
                    inactive_item.setForeground(dimmed)

            # Update header to show which column prints
            headers = ["Brennan P/N", "Customer P/N", "Description", "Short Desc"]
            if description_mode == "full":
                headers[2] = "Description \u2713"
            else:
                headers[3] = "Short Desc \u2713"
            self._table.setHorizontalHeaderLabels(headers)

            if 0 <= selected_index < len(labels):
                self._table.selectRow(selected_index)
        finally:
            self._table.blockSignals(False)

    def get_selected_index(self) -> int:
        return self._table.currentRow()
