"""Main application window assembling all panels and connecting to presenters."""
import os
from typing import Optional, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QFileDialog, QMessageBox, QLabel, QLineEdit, QApplication,
    QFormLayout, QPushButton, QStatusBar, QGroupBox, QComboBox,
    QInputDialog, QSizePolicy, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QPixmap

from src.models.template import Template, XREF_MANUFACTURERS
from src.models.label_data import LabelData
from src.models.avery_templates import AVERY_TEMPLATES
from src.presenters.main_presenter import MainPresenter
from src.presenters.label_presenter import LabelPresenter
from src.services.preview_renderer import PreviewRenderer
from src.services.project_manager import ProjectManager
from src.views.avery_selector import AverySelector
from src.views.label_editor import LabelEditor, LookupResultsDialog
from src.views.label_list_panel import LabelListPanel
from src.views.preview_panel import PreviewPanel
from src.views.bulk_search_dialog import BulkSearchDialog
from src.views.theme import logo_full_path, BRENNAN_BLUE, BRENNAN_WHITE
from src.services.csv_importer import import_labels_from_file
from src.services.image_utils import download_image


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(
        self,
        main_presenter: MainPresenter,
        label_presenter: LabelPresenter,
        preview_renderer: PreviewRenderer,
        project_manager: ProjectManager,
    ):
        super().__init__()
        self.main_presenter = main_presenter
        self.label_presenter = label_presenter
        self.preview_renderer = preview_renderer
        self.project_manager = project_manager
        self._current_project_name: str = ""

        self.setWindowTitle("Bin Label Maker - Brennan Industries")
        self.setMinimumSize(900, 600)
        self.resize(1200, 800)

        # Register this window as the view for the label presenter
        self.label_presenter.set_view(self)

        self._build_menu_bar()
        self._build_ui()
        self._build_status_bar()
        self._connect_signals()

        # Initialize with empty template
        self.label_presenter.new_template()

    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("  File  ")

        new_action = QAction("New Template", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new)
        file_menu.addAction(new_action)

        file_menu.addSeparator()

        import_action = QAction("Import Template File...", self)
        import_action.setShortcut("Ctrl+O")
        import_action.triggered.connect(self._on_import_file)
        file_menu.addAction(import_action)

        export_template_action = QAction("Export Template File...", self)
        export_template_action.triggered.connect(self._on_export_template)
        file_menu.addAction(export_template_action)

        file_menu.addSeparator()

        import_csv_action = QAction("Import Parts from CSV/Excel...", self)
        import_csv_action.setShortcut("Ctrl+I")
        import_csv_action.triggered.connect(self._on_import_csv)
        file_menu.addAction(import_csv_action)

        file_menu.addSeparator()

        export_action = QAction("Export PDF...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export_pdf)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Brand header bar ──
        header = QFrame()
        header.setObjectName("brandHeader")
        header.setFixedHeight(56)
        header.setStyleSheet(f"""
            QFrame#brandHeader {{
                background-color: {BRENNAN_WHITE};
                border-bottom: 3px solid {BRENNAN_BLUE};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 4, 12, 4)

        logo_path = logo_full_path()
        if os.path.exists(logo_path):
            logo_label = QLabel()
            pix = QPixmap(logo_path)
            logo_label.setPixmap(pix.scaledToHeight(42, Qt.TransformationMode.SmoothTransformation))
            header_layout.addWidget(logo_label)

        header_layout.addStretch()

        title_label = QLabel("Bin Label Maker")
        title_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 700;
            color: {BRENNAN_BLUE};
            letter-spacing: 0.5px;
        """)
        header_layout.addWidget(title_label)

        main_layout.addWidget(header)

        # ── Content area ──
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 4)
        content_layout.setSpacing(0)

        # Left panel: project bar + template settings + label list + editor
        left_panel = QWidget()
        left_panel.setMinimumWidth(380)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(4)

        # ---- Project bar (compact row) ----
        project_group = QGroupBox("Customer Project")
        project_layout = QVBoxLayout(project_group)
        project_layout.setContentsMargins(8, 12, 8, 8)
        project_layout.setSpacing(4)

        proj_sel_row = QHBoxLayout()
        proj_sel_row.setSpacing(4)
        self._project_combo = QComboBox()
        self._project_combo.setEditable(True)
        self._project_combo.setPlaceholderText("Customer name...")
        self._project_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._refresh_project_list()
        proj_sel_row.addWidget(self._project_combo, 1)

        save_btn = QPushButton("Save")
        save_btn.setFixedWidth(50)
        save_btn.clicked.connect(self._on_project_save)
        proj_sel_row.addWidget(save_btn)

        load_btn = QPushButton("Load")
        load_btn.setFixedWidth(50)
        load_btn.setProperty("cssClass", "secondary")
        load_btn.clicked.connect(self._on_project_load)
        proj_sel_row.addWidget(load_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setFixedWidth(55)
        delete_btn.setProperty("cssClass", "danger")
        delete_btn.clicked.connect(self._on_project_delete)
        proj_sel_row.addWidget(delete_btn)

        save_as_btn = QPushButton("Save As...")
        save_as_btn.setFixedWidth(65)
        save_as_btn.setProperty("cssClass", "secondary")
        save_as_btn.clicked.connect(self._on_project_save_as)
        proj_sel_row.addWidget(save_as_btn)

        project_layout.addLayout(proj_sel_row)

        left_layout.addWidget(project_group)

        # ---- Template settings (collapsible-style compact group) ----
        settings_group = QGroupBox("Template Settings")
        settings_layout = QFormLayout(settings_group)
        settings_layout.setContentsMargins(8, 12, 8, 8)
        settings_layout.setSpacing(4)

        self._customer_name = QLineEdit()
        self._customer_name.setPlaceholderText("Customer name")
        self._customer_name.textChanged.connect(
            lambda t: self.label_presenter.set_customer_name(t)
        )
        settings_layout.addRow("Customer:", self._customer_name)

        self._qr_base_url = QLineEdit()
        self._qr_base_url.setPlaceholderText("https://brennaninc.com/parts/")
        self._qr_base_url.textChanged.connect(
            lambda t: self.label_presenter.set_qr_base_url(t)
        )
        settings_layout.addRow("QR Base URL:", self._qr_base_url)

        # Logo picker
        logo_row_widget = QWidget()
        logo_row = QHBoxLayout(logo_row_widget)
        logo_row.setContentsMargins(0, 0, 0, 0)
        self._logo_label = QLabel("No logo selected")
        self._logo_label.setStyleSheet("color: #888; font-style: italic;")
        logo_row.addWidget(self._logo_label, 1)
        logo_btn = QPushButton("Browse...")
        logo_btn.setProperty("cssClass", "secondary")
        logo_btn.setFixedWidth(70)
        logo_btn.clicked.connect(self._pick_logo)
        logo_row.addWidget(logo_btn)
        settings_layout.addRow("Logo:", logo_row_widget)

        self._avery_selector = AverySelector()
        settings_layout.addRow(self._avery_selector)

        # Manufacturer cross-reference for Customer P/N
        self._xref_combo = QComboBox()
        for display_name, key in XREF_MANUFACTURERS.items():
            self._xref_combo.addItem(display_name, key)
        self._xref_combo.currentIndexChanged.connect(self._on_xref_changed)
        settings_layout.addRow("Customer P/N:", self._xref_combo)

        # Description character limit
        from PySide6.QtWidgets import QSpinBox
        self._desc_limit_spin = QSpinBox()
        self._desc_limit_spin.setRange(0, 500)
        self._desc_limit_spin.setSpecialValueText("Unlimited")
        self._desc_limit_spin.setSuffix(" chars")
        self._desc_limit_spin.setValue(0)
        self._desc_limit_spin.valueChanged.connect(
            lambda v: self.label_presenter.set_description_limit(v)
        )
        settings_layout.addRow("Desc. Limit:", self._desc_limit_spin)

        left_layout.addWidget(settings_group)

        # Label list (takes most vertical space)
        self._label_list = LabelListPanel()
        self._label_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._label_list.setMinimumHeight(120)
        left_layout.addWidget(self._label_list, 1)

        # Label editor (bottom, compact)
        self._label_editor = LabelEditor()
        left_layout.addWidget(self._label_editor, 0)

        # Right panel: preview
        self._preview = PreviewPanel()
        self._preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._preview.set_render_callback(self._render_preview_page)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self._preview)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setHandleWidth(6)

        content_layout.addWidget(splitter)
        main_layout.addWidget(content, 1)

    def _build_status_bar(self) -> None:
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_label = QLabel("Ready")
        self._status_bar.addWidget(self._status_label)

    def _connect_signals(self) -> None:
        # Avery selector
        self._avery_selector.template_changed.connect(
            self.label_presenter.set_avery_template
        )

        # Label list
        self._label_list.label_selected.connect(self.label_presenter.select_label)
        self._label_list.add_requested.connect(self.label_presenter.add_label)
        self._label_list.remove_requested.connect(self.label_presenter.remove_label)
        self._label_list.duplicate_requested.connect(self.label_presenter.duplicate_label)
        self._label_list.fill_sheet_requested.connect(self.label_presenter.fill_sheet)
        self._label_list.bulk_search_requested.connect(self._on_bulk_search)
        self._label_list.import_csv_requested.connect(self._on_import_csv)

        # Label editor
        self._label_editor.label_changed.connect(self._on_editor_changed)
        self._label_editor.lookup_requested.connect(self._on_lookup_requested)

    # --- Project management ---

    def _refresh_project_list(self) -> None:
        projects = self.project_manager.list_projects()
        self._project_combo.clear()
        self._project_combo.addItems(projects)
        if self._current_project_name:
            idx = self._project_combo.findText(self._current_project_name)
            if idx >= 0:
                self._project_combo.setCurrentIndex(idx)

    def _on_project_save(self) -> None:
        name = self._project_combo.currentText().strip()
        if not name:
            name = self._customer_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Enter a customer/project name first.")
            return
        self.label_presenter.template.customer_name = name
        self.project_manager.save_project(name, self.label_presenter.template)
        self._current_project_name = name
        self._refresh_project_list()
        self._status_label.setText(f"Saved project: {name}")

    def _on_project_load(self) -> None:
        name = self._project_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Select or type a project name.")
            return
        template = self.project_manager.load_project(name)
        if template is None:
            QMessageBox.warning(self, "Warning", f"Project '{name}' not found.")
            return
        self.label_presenter.template = template
        self.label_presenter._current_index = 0 if template.labels else -1
        self.label_presenter._notify_template_changed()
        self._current_project_name = name
        self._status_label.setText(f"Loaded project: {name}")

    def _on_project_save_as(self) -> None:
        new_name, ok = QInputDialog.getText(
            self, "Save As", "Enter new project name:"
        )
        if ok and new_name and new_name.strip():
            new_name = new_name.strip()
            self._project_combo.setEditText(new_name)
            self._on_project_save()

    def _on_project_delete(self) -> None:
        name = self._project_combo.currentText().strip()
        if not name:
            return
        reply = QMessageBox.question(
            self, "Delete Project",
            f"Delete project '{name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.project_manager.delete_project(name)
            self._current_project_name = ""
            self._refresh_project_list()
            self._status_label.setText(f"Deleted project: {name}")

    # --- Menu actions ---

    def _on_new(self) -> None:
        self._current_project_name = ""
        self._project_combo.setEditText("")
        self.main_presenter.on_new()

    def _on_import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Template", "",
            "Label Templates (*.blm *.json);;All Files (*)"
        )
        if path:
            name = self.project_manager.import_project(path)
            if name:
                self._current_project_name = name
                template = self.project_manager.load_project(name)
                if template:
                    self.label_presenter.template = template
                    self.label_presenter._current_index = 0 if template.labels else -1
                    self.label_presenter._notify_template_changed()
                self._refresh_project_list()
                self._status_label.setText(f"Imported project: {name}")
            else:
                QMessageBox.warning(self, "Import Failed", "Could not import the template file.")

    def _on_export_template(self) -> None:
        name = self._current_project_name or self._customer_name.text().strip() or "template"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Template", name,
            "Label Templates (*.blm);;JSON (*.json);;All Files (*)"
        )
        if path:
            if not (path.endswith(".blm") or path.endswith(".json")):
                path += ".blm"
            self.label_presenter.save_template(path)
            self._status_label.setText(f"Exported template to {path}")

    def _on_export_pdf(self) -> None:
        name = self._current_project_name or self._customer_name.text().strip() or "labels"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", name,
            "PDF Files (*.pdf);;All Files (*)"
        )
        if path:
            if not path.endswith(".pdf"):
                path += ".pdf"
            self.main_presenter.on_export_pdf(path)
            self._status_label.setText(f"PDF exported to {path}")

    def _pick_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Logo Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if path:
            self._logo_label.setText(path.split("/")[-1])
            self._logo_label.setStyleSheet("color: #333;")
            self.label_presenter.set_logo_path(path)

    def _on_xref_changed(self, index: int) -> None:
        xref_key = self._xref_combo.itemData(index) or ""
        self.label_presenter.set_xref_key(xref_key)

    # --- CSV/Excel import ---

    def _on_import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Parts from CSV/Excel", "",
            "Spreadsheets (*.csv *.xlsx *.xls);;CSV Files (*.csv);;Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        if not path:
            return
        try:
            labels = import_labels_from_file(path)
            if not labels:
                QMessageBox.warning(self, "Import", "No labels found in the file. "
                    "Expected columns: brennan_part_number, customer_part_number, description")
                return
            for label in labels:
                self.label_presenter.template.labels.append(label)
            self.label_presenter._current_index = len(self.label_presenter.template.labels) - 1
            self.label_presenter._notify_list_changed()
            self.label_presenter._notify_label_selected()
            self._status_label.setText(f"Imported {len(labels)} labels from {path.split('/')[-1]}")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import file:\n{e}")

    # --- Bulk search ---

    def _resolve_customer_pn(self, part: dict) -> str:
        """Get the customer part number using the selected xref manufacturer."""
        xref_key = self.label_presenter.template.xref_key
        xrefs = part.get("xrefs", {})
        if xref_key and xrefs:
            return xrefs.get(xref_key, "")
        # If no manufacturer selected, return empty
        return part.get("customer_part_number", "")

    def _apply_desc_limit(self, desc: str) -> str:
        """Truncate description to the configured limit."""
        limit = self.label_presenter.template.description_limit
        if limit > 0 and len(desc) > limit:
            return desc[:limit]
        return desc

    def _on_bulk_search(self) -> None:
        dialog = BulkSearchDialog(self.label_presenter.data_source, self)
        if dialog.exec():
            selected = dialog.get_selected_parts()
            if not selected:
                return
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                for part in selected:
                    # Download image from Catsy if available
                    image_path = None
                    image_url = part.get("image_url")
                    if image_url:
                        image_path = download_image(image_url)

                    label = LabelData(
                        brennan_part_number=part.get("brennan_part_number", ""),
                        customer_part_number=self._resolve_customer_pn(part),
                        description=self._apply_desc_limit(part.get("description", "")),
                        image_path=image_path,
                    )
                    self.label_presenter.template.labels.append(label)
            finally:
                QApplication.restoreOverrideCursor()
            self.label_presenter._current_index = len(self.label_presenter.template.labels) - 1
            self.label_presenter._notify_list_changed()
            self.label_presenter._notify_label_selected()
            self._status_label.setText(f"Added {len(selected)} labels from search")

    # --- Editor change handler ---

    def _on_editor_changed(self) -> None:
        data = self._label_editor.get_data()
        self.label_presenter.update_current_label(**data)

    # --- Catsy lookup ---

    def _on_lookup_requested(self, query: str) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            results = self.label_presenter.lookup_part(query)
        finally:
            QApplication.restoreOverrideCursor()
        if not results:
            QMessageBox.information(self, "Lookup", "No results found.")
            return
        dialog = LookupResultsDialog(results, self)
        if dialog.exec() and dialog.selected_part_number:
            # Find the selected part in results
            part_data = None
            for r in results:
                if r.get("brennan_part_number") == dialog.selected_part_number:
                    part_data = r
                    break
            if not part_data:
                # Fetch fresh from API
                part_data = self.label_presenter.data_source.get_part_details(
                    dialog.selected_part_number
                )
            if part_data:
                # Resolve customer P/N from xref
                part_data["customer_part_number"] = self._resolve_customer_pn(part_data)
                part_data["description"] = self._apply_desc_limit(part_data.get("description", ""))
                # Download image
                image_path = None
                image_url = part_data.get("image_url")
                if image_url:
                    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                    try:
                        image_path = download_image(image_url)
                    finally:
                        QApplication.restoreOverrideCursor()
                self.label_presenter.fill_from_lookup(part_data, image_path)

    # --- Preview rendering ---

    def _render_preview_page(self, page: int) -> QPixmap:
        return self.preview_renderer.render(self.label_presenter.template, page)

    # --- View interface (called by LabelPresenter) ---

    def on_template_changed(self, template: Template) -> None:
        """Called when a new template is loaded or created."""
        self._customer_name.setText(template.customer_name)
        self._qr_base_url.setText(template.qr_base_url)
        self._avery_selector.set_template_id(template.avery_template_id)

        # Restore xref selection
        idx = self._xref_combo.findData(template.xref_key)
        if idx >= 0:
            self._xref_combo.setCurrentIndex(idx)
        else:
            self._xref_combo.setCurrentIndex(0)

        # Restore description limit
        self._desc_limit_spin.setValue(template.description_limit)

        if template.logo_path:
            name = template.logo_path.split("/")[-1] if "/" in template.logo_path else template.logo_path.split("\\")[-1]
            self._logo_label.setText(name)
            self._logo_label.setStyleSheet("color: #333;")
        else:
            self._logo_label.setText("No logo selected")
            self._logo_label.setStyleSheet("color: #888; font-style: italic;")

        self._label_list.update_labels(template.labels)
        self._label_editor.clear()
        self._label_editor.set_enabled(False)
        self._update_status(template)
        self._preview.request_update()

    def on_labels_changed(self, labels: List[LabelData], selected_index: int) -> None:
        """Called when the label list changes (add/remove/edit)."""
        self._label_list.update_labels(labels, selected_index)
        self._update_status(self.label_presenter.template)
        self._preview.request_update()

    def on_label_selected(self, label: Optional[LabelData], index: int) -> None:
        """Called when a label is selected in the list."""
        if label:
            self._label_editor.set_enabled(True)
            self._label_editor.set_data(
                label.brennan_part_number,
                label.customer_part_number,
                label.description,
                label.image_path,
            )
            # Zoom preview to show the selected label
            if index >= 0:
                self._preview.zoom_to_label(index)
        else:
            self._label_editor.set_enabled(False)
            self._label_editor.clear()

    def on_preview_update_needed(self) -> None:
        """Called when preview needs re-rendering."""
        self._preview.request_update()

    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)

    def _update_status(self, template: Template) -> None:
        from src.services.label_layout import LabelLayoutService
        geo = AVERY_TEMPLATES.get(template.avery_template_id)
        name = geo.name if geo else "Unknown"
        count = len(template.labels)
        # Update label grid positions for zoom-to-label
        if geo:
            layout_svc = LabelLayoutService()
            positions = layout_svc.compute_label_positions(geo)
            self._preview.set_label_grid(positions, geo.labels_per_page, template.start_offset)
        per_page = geo.labels_per_page if geo else 0
        pages = max(1, (count + template.start_offset + per_page - 1) // per_page) if per_page else 1
        project = self._current_project_name or template.customer_name or "Untitled"
        self._status_label.setText(
            f"  {project}  |  {name}  |  {count} labels  |  {pages} page(s)"
        )
        self._preview.set_total_pages(pages)
