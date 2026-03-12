"""Main application window assembling all panels and connecting to presenters."""
from typing import Optional, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QMenuBar, QFileDialog, QMessageBox, QLabel, QLineEdit,
    QFormLayout, QPushButton, QStatusBar, QGroupBox, QComboBox,
    QInputDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QPixmap

from src.models.template import Template
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
        self.setMinimumSize(1100, 700)

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

        file_menu = menu_bar.addMenu("File")

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
        main_layout = QHBoxLayout(central)

        # Left panel: project bar + template settings + label list + editor
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # ---- Project bar (like Drawing-Generator) ----
        project_group = QGroupBox("Customer Project")
        project_layout = QVBoxLayout(project_group)

        # Project selector row
        proj_sel_row = QHBoxLayout()
        self._project_combo = QComboBox()
        self._project_combo.setEditable(True)
        self._project_combo.setPlaceholderText("Type customer name or select...")
        self._project_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._refresh_project_list()
        proj_sel_row.addWidget(self._project_combo, 1)

        save_btn = QPushButton("Save")
        save_btn.setFixedWidth(55)
        save_btn.clicked.connect(self._on_project_save)
        proj_sel_row.addWidget(save_btn)

        load_btn = QPushButton("Load")
        load_btn.setFixedWidth(55)
        load_btn.clicked.connect(self._on_project_load)
        proj_sel_row.addWidget(load_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setFixedWidth(55)
        delete_btn.clicked.connect(self._on_project_delete)
        proj_sel_row.addWidget(delete_btn)

        project_layout.addLayout(proj_sel_row)

        # Save As button
        save_as_row = QHBoxLayout()
        save_as_row.addStretch()
        save_as_btn = QPushButton("Save As...")
        save_as_btn.setFixedWidth(80)
        save_as_btn.clicked.connect(self._on_project_save_as)
        save_as_row.addWidget(save_as_btn)
        project_layout.addLayout(save_as_row)

        left_layout.addWidget(project_group)

        # ---- Template settings group ----
        settings_group = QGroupBox("Template Settings")
        settings_layout = QFormLayout(settings_group)

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
        self._logo_label.setStyleSheet("color: #666;")
        logo_row.addWidget(self._logo_label, 1)
        logo_btn = QPushButton("Browse...")
        logo_btn.clicked.connect(self._pick_logo)
        logo_row.addWidget(logo_btn)
        settings_layout.addRow("Logo:", logo_row_widget)

        self._avery_selector = AverySelector()
        settings_layout.addRow(self._avery_selector)

        left_layout.addWidget(settings_group)

        # Label list
        self._label_list = LabelListPanel()
        left_layout.addWidget(self._label_list, 1)

        # Label editor
        self._label_editor = LabelEditor()
        left_layout.addWidget(self._label_editor)

        # Right panel: preview
        self._preview = PreviewPanel()
        self._preview.set_render_callback(self._render_preview_page)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self._preview)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)

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

        # Label editor
        self._label_editor.label_changed.connect(self._on_editor_changed)
        self._label_editor.lookup_requested.connect(self._on_lookup_requested)

    # --- Project management (Drawing-Generator style) ---

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
            self.label_presenter.set_logo_path(path)

    # --- Editor change handler ---

    def _on_editor_changed(self) -> None:
        data = self._label_editor.get_data()
        self.label_presenter.update_current_label(**data)

    # --- Catsy lookup ---

    def _on_lookup_requested(self, query: str) -> None:
        results = self.label_presenter.lookup_part(query)
        if not results:
            QMessageBox.information(self, "Lookup", "No results found.")
            return
        dialog = LookupResultsDialog(results, self)
        if dialog.exec() and dialog.selected_part_number:
            self.label_presenter.fill_from_lookup(dialog.selected_part_number)

    # --- Preview rendering ---

    def _render_preview_page(self, page: int) -> QPixmap:
        return self.preview_renderer.render(self.label_presenter.template, page)

    # --- View interface (called by LabelPresenter) ---

    def on_template_changed(self, template: Template) -> None:
        """Called when a new template is loaded or created."""
        self._customer_name.setText(template.customer_name)
        self._qr_base_url.setText(template.qr_base_url)
        self._avery_selector.set_template_id(template.avery_template_id)

        if template.logo_path:
            name = template.logo_path.split("/")[-1] if "/" in template.logo_path else template.logo_path.split("\\")[-1]
            self._logo_label.setText(name)
        else:
            self._logo_label.setText("No logo selected")

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
        else:
            self._label_editor.set_enabled(False)
            self._label_editor.clear()

    def on_preview_update_needed(self) -> None:
        """Called when preview needs re-rendering."""
        self._preview.request_update()

    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)

    def _update_status(self, template: Template) -> None:
        geo = AVERY_TEMPLATES.get(template.avery_template_id)
        name = geo.name if geo else "Unknown"
        count = len(template.labels)
        per_page = geo.labels_per_page if geo else 0
        pages = max(1, (count + template.start_offset + per_page - 1) // per_page) if per_page else 1
        project = self._current_project_name or template.customer_name or "Untitled"
        self._status_label.setText(
            f"{project} | {name} | {count} labels | {pages} page(s)"
        )
        self._preview.set_total_pages(pages)
