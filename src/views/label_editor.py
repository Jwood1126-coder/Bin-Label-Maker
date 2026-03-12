"""Form widget for editing a single label's data."""
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QPushButton,
    QHBoxLayout, QLabel, QVBoxLayout, QDialog, QListWidget, QListWidgetItem,
    QDialogButtonBox, QGroupBox,
)
from PySide6.QtCore import Signal


class LabelEditor(QWidget):
    """Form for editing one label's fields."""

    label_changed = Signal()  # emitted when any field changes
    lookup_requested = Signal(str)  # emitted with search query

    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False  # guard against feedback loops

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("Label Details")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(4)

        form = QFormLayout()
        form.setSpacing(6)

        self._brennan_pn = QLineEdit()
        self._brennan_pn.setPlaceholderText("e.g. 2404-04-02")
        self._brennan_pn.textChanged.connect(self._on_field_changed)
        form.addRow("Brennan Part #:", self._brennan_pn)

        self._customer_pn = QLineEdit()
        self._customer_pn.setPlaceholderText("e.g. 2021-2-4S")
        self._customer_pn.textChanged.connect(self._on_field_changed)
        form.addRow("Customer Part #:", self._customer_pn)

        self._description = QLineEdit()
        self._description.setPlaceholderText("e.g. 04MJ-02MP Straight")
        self._description.textChanged.connect(self._on_field_changed)
        form.addRow("Description:", self._description)

        # Image status (read-only, populated from Catsy)
        self._image_path_label = QLabel("No image")
        self._image_path_label.setStyleSheet("color: #888; font-style: italic;")
        form.addRow("Part Image:", self._image_path_label)

        group_layout.addLayout(form)

        # Catsy lookup
        lookup_row = QHBoxLayout()
        lookup_row.setSpacing(4)
        self._lookup_input = QLineEdit()
        self._lookup_input.setPlaceholderText("Search by part number...")
        lookup_row.addWidget(self._lookup_input, 1)
        self._lookup_btn = QPushButton("Lookup in Catsy")
        self._lookup_btn.clicked.connect(self._on_lookup)
        lookup_row.addWidget(self._lookup_btn)
        group_layout.addLayout(lookup_row)

        layout.addWidget(group)

    def _on_field_changed(self) -> None:
        if not self._updating:
            self.label_changed.emit()

    def _on_lookup(self) -> None:
        query = self._lookup_input.text().strip()
        if query:
            self.lookup_requested.emit(query)

    def get_data(self) -> dict:
        return {
            "brennan_pn": self._brennan_pn.text(),
            "customer_pn": self._customer_pn.text(),
            "description": self._description.text(),
            "image_path": getattr(self, "_image_path", None),
        }

    def set_data(self, brennan_pn: str, customer_pn: str, description: str, image_path: str = None) -> None:
        self._updating = True
        self._brennan_pn.setText(brennan_pn)
        self._customer_pn.setText(customer_pn)
        self._description.setText(description)
        self._image_path = image_path
        if image_path:
            name = image_path.split("/")[-1] if "/" in image_path else image_path.split("\\")[-1]
            self._image_path_label.setText(name)
            self._image_path_label.setStyleSheet("color: #333;")
        else:
            self._image_path_label.setText("No image")
            self._image_path_label.setStyleSheet("color: #888; font-style: italic;")
        self._updating = False

    def clear(self) -> None:
        self._updating = True
        self._brennan_pn.clear()
        self._customer_pn.clear()
        self._description.clear()
        self._image_path = None
        self._image_path_label.setText("No image")
        self._image_path_label.setStyleSheet("color: #888; font-style: italic;")
        self._updating = False

    def set_enabled(self, enabled: bool) -> None:
        self._brennan_pn.setEnabled(enabled)
        self._customer_pn.setEnabled(enabled)
        self._description.setEnabled(enabled)
        self._lookup_btn.setEnabled(enabled)
        self._lookup_input.setEnabled(enabled)


class LookupResultsDialog(QDialog):
    """Dialog showing Catsy lookup results for the user to select from."""

    def __init__(self, results: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Catsy Lookup Results")
        self.setMinimumWidth(500)
        self.resize(550, 400)
        self.selected_part_number = None

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        header = QLabel(f"Found {len(results)} result(s):")
        header.setProperty("cssClass", "section-header")
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        for r in results:
            item = QListWidgetItem(
                f"{r['brennan_part_number']}  |  {r.get('description', '')[:60]}"
            )
            item.setData(256, r["brennan_part_number"])  # Qt.UserRole
            self._list.addItem(item)
        self._list.itemDoubleClicked.connect(self._on_select)
        layout.addWidget(self._list)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_select(self, item: QListWidgetItem) -> None:
        self.selected_part_number = item.data(256)
        self.accept()

    def _on_accept(self) -> None:
        current = self._list.currentItem()
        if current:
            self.selected_part_number = current.data(256)
        self.accept()
