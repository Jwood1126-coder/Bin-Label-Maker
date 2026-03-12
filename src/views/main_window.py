"""Main application window assembling all panels and connecting to presenters."""
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QFileDialog, QMessageBox, QLabel, QLineEdit, QApplication,
    QFormLayout, QPushButton, QStatusBar, QGroupBox, QComboBox,
    QInputDialog, QSizePolicy, QFrame, QSpinBox,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QAction, QPixmap, QCloseEvent, QKeySequence

from src.models.template import Template, XREF_MANUFACTURERS, DESC_MODE_FULL, DESC_MODE_SHORT
from src.models.label_data import LabelData
from src.models.avery_templates import AVERY_TEMPLATES
from src.presenters.main_presenter import MainPresenter
from src.presenters.label_presenter import LabelPresenter
from src.services.preview_renderer import PreviewRenderer
from src.services.project_manager import ProjectManager
from src.services.label_layout import LabelLayoutService
from src.views.avery_selector import AverySelector
from src.views.label_list_panel import LabelListPanel
from src.views.preview_panel import PreviewPanel
from src.views.bulk_search_dialog import BulkSearchDialog
from src.views.theme import logo_full_path, BRENNAN_BLUE, BRENNAN_WHITE
from src.services.csv_importer import import_labels_from_file, parse_clipboard_text
from src.services.image_utils import download_image


class _ImageDownloadWorker(QObject):
    """Background worker for downloading images without blocking the UI."""
    finished = Signal(list)  # emits list of LabelData
    progress = Signal(int, int)  # current, total
    error = Signal(str)  # emits error message on failure

    def __init__(self, parts: list, xref_key: str):
        super().__init__()
        self._parts = parts
        self._xref_key = xref_key  # captured from main thread before start

    def run(self) -> None:
        try:
            labels = []
            total = len(self._parts)
            for i, part in enumerate(self._parts):
                image_path = None
                image_url = part.get("image_url")
                if image_url:
                    try:
                        image_path = download_image(image_url)
                    except Exception:
                        pass  # skip failed image, label still works

                xrefs = dict(part.get("xrefs", {}))
                # Resolve customer P/N from xrefs using current manufacturer
                customer_pn = ""
                if self._xref_key and xrefs:
                    customer_pn = xrefs.get(self._xref_key, "")

                label = LabelData(
                    brennan_part_number=part.get("brennan_part_number", ""),
                    customer_part_number=customer_pn,
                    description=part.get("description", ""),
                    short_description=part.get("short_description", ""),
                    image_path=image_path,
                    xrefs=xrefs,
                )
                labels.append(label)
                self.progress.emit(i + 1, total)
            self.finished.emit(labels)
        except Exception as e:
            self.error.emit(str(e))


# Shared layout service instance (stateless — safe to reuse)
_layout_service = LabelLayoutService()


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
        self._download_thread: Optional[QThread] = None
        self._last_dir = str(Path.home() / "Documents")
        # Guard flag: True while we are programmatically updating UI widgets.
        # When set, change handlers must NOT propagate to the presenter.
        self._refreshing_ui: bool = False

        self.setWindowTitle("Bin Label Maker \u2014 Brennan Industries")
        self.setMinimumSize(780, 500)
        self.resize(1200, 800)

        # Register this window as the view for the label presenter
        self.label_presenter.set_view(self)

        self._build_menu_bar()
        self._build_ui()
        self._build_status_bar()
        self._connect_signals()

        # Initialize with empty template
        self.label_presenter.new_template()

    # --- Close event / unsaved changes guard ---

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._check_unsaved_changes("quit"):
            event.accept()
        else:
            event.ignore()

    def _check_unsaved_changes(self, action: str = "continue") -> bool:
        """Returns True if it's safe to proceed (saved or user chose to discard)."""
        if not self.label_presenter.is_dirty:
            return True
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            f"You have unsaved changes. Do you want to save before you {action}?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            return self._on_project_save()
        elif reply == QMessageBox.StandardButton.Discard:
            return True
        return False  # Cancel

    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")

        new_action = QAction("New Job", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._on_new)
        file_menu.addAction(new_action)

        save_action = QAction("Save Job", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._on_project_save)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        import_action = QAction("Open Job File...", self)
        import_action.setShortcut(QKeySequence.StandardKey.Open)
        import_action.triggered.connect(self._on_import_file)
        file_menu.addAction(import_action)

        export_template_action = QAction("Export Job File...", self)
        export_template_action.triggered.connect(self._on_export_template)
        file_menu.addAction(export_template_action)

        file_menu.addSeparator()

        import_csv_action = QAction("Import Parts from CSV/Excel...", self)
        import_csv_action.setShortcut("Ctrl+I")
        import_csv_action.triggered.connect(self._on_import_csv)
        file_menu.addAction(import_csv_action)

        paste_action = QAction("Paste Parts from Clipboard", self)
        paste_action.setShortcut("Ctrl+Shift+V")
        paste_action.setToolTip("Paste tab-separated or CSV data from clipboard")
        paste_action.triggered.connect(self._on_paste_labels)
        file_menu.addAction(paste_action)

        file_menu.addSeparator()

        export_action = QAction("Export PDF...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export_pdf)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -- Brand header bar --
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

        # -- Content area --
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 4)
        content_layout.setSpacing(0)

        # Left panel: project bar + label settings + label list
        left_panel = QWidget()
        left_panel.setMinimumWidth(320)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(4)

        # ---- Job bar ----
        project_group = QGroupBox("Customer Job")
        project_layout = QVBoxLayout(project_group)
        project_layout.setContentsMargins(8, 12, 8, 8)
        project_layout.setSpacing(4)

        proj_sel_row = QHBoxLayout()
        proj_sel_row.setSpacing(4)
        self._project_combo = QComboBox()
        self._project_combo.setEditable(True)
        self._project_combo.setPlaceholderText("Customer / job name...")
        self._project_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._project_combo.setToolTip("Select a saved job or type a new name")
        self._refresh_project_list()
        proj_sel_row.addWidget(self._project_combo, 1)
        project_layout.addLayout(proj_sel_row)

        proj_btn_row = QHBoxLayout()
        proj_btn_row.setSpacing(4)

        save_btn = QPushButton("Save")
        save_btn.setToolTip("Save the current job (Ctrl+S)")
        save_btn.clicked.connect(self._on_project_save)
        proj_btn_row.addWidget(save_btn)

        load_btn = QPushButton("Load")
        load_btn.setProperty("cssClass", "secondary")
        load_btn.setToolTip("Load the selected job")
        load_btn.clicked.connect(self._on_project_load)
        proj_btn_row.addWidget(load_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setProperty("cssClass", "danger")
        delete_btn.setToolTip("Permanently delete the selected job")
        delete_btn.clicked.connect(self._on_project_delete)
        proj_btn_row.addWidget(delete_btn)

        save_as_btn = QPushButton("Save As")
        save_as_btn.setProperty("cssClass", "secondary")
        save_as_btn.setToolTip("Save a copy under a new job name")
        save_as_btn.clicked.connect(self._on_project_save_as)
        proj_btn_row.addWidget(save_as_btn)

        project_layout.addLayout(proj_btn_row)

        left_layout.addWidget(project_group)

        # ---- Label Settings ----
        settings_group = QGroupBox("Label Settings")
        settings_layout = QFormLayout(settings_group)
        settings_layout.setContentsMargins(8, 12, 8, 8)
        settings_layout.setSpacing(4)

        self._avery_selector = AverySelector()
        self._avery_selector.setToolTip("Choose the Avery label sheet format for printing")
        settings_layout.addRow("Avery Sheet:", self._avery_selector)

        # Manufacturer cross-reference for Customer P/N
        self._xref_combo = QComboBox()
        self._xref_combo.setToolTip(
            "Select which manufacturer's part number to show as Customer P/N.\n"
            "Only manufacturers with data for the current parts are shown.\n"
            "Add parts first (via Search or Import), then select the manufacturer."
        )
        self._xref_combo.addItem("(none)", "")
        self._xref_combo.currentIndexChanged.connect(self._on_xref_changed)
        settings_layout.addRow("Customer P/N:", self._xref_combo)

        # Description mode: Full Description or Short Description
        self._desc_mode_combo = QComboBox()
        self._desc_mode_combo.setToolTip(
            "Controls which description is shown on the printed label.\n"
            "Full: material + connection sizes\n"
            "Short: compact size codes (e.g. 04MJ x 02MP)\n\n"
            "Both fields are always editable in the table."
        )
        self._desc_mode_combo.addItem("Full Description", DESC_MODE_FULL)
        self._desc_mode_combo.addItem("Short Description", DESC_MODE_SHORT)
        self._desc_mode_combo.currentIndexChanged.connect(self._on_desc_mode_changed)
        settings_layout.addRow("Print Mode:", self._desc_mode_combo)

        # Start offset for partial sheets
        offset_widget = QWidget()
        offset_layout = QHBoxLayout(offset_widget)
        offset_layout.setContentsMargins(0, 0, 0, 0)
        offset_layout.setSpacing(4)
        self._start_offset_spin = QSpinBox()
        self._start_offset_spin.setMinimum(0)
        self._start_offset_spin.setMaximum(29)
        self._start_offset_spin.setValue(0)
        self._start_offset_spin.setSuffix(" labels skipped")
        self._start_offset_spin.setToolTip(
            "Skip this many label positions from the top-left.\n"
            "Use when printing on a partially-used sheet.\n\n"
            "Example: if the first 5 labels were already used,\n"
            "set this to 5 so printing starts at position 6."
        )
        self._start_offset_spin.valueChanged.connect(self._on_start_offset_changed)
        offset_layout.addWidget(self._start_offset_spin, 1)
        settings_layout.addRow("Skip Labels:", offset_widget)

        # QR Base URL
        self._qr_base_url = QLineEdit()
        self._qr_base_url.setPlaceholderText("https://brennaninc.com/")
        self._qr_base_url.setToolTip(
            "Base URL for QR codes. Part number is appended automatically.\n"
            "Example: https://brennaninc.com/ + 2404-04-02"
        )
        self._qr_base_url.textChanged.connect(self._on_qr_url_changed)
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
        logo_btn.setToolTip("Choose a logo image to print on each label")
        logo_btn.clicked.connect(self._pick_logo)
        logo_row.addWidget(logo_btn)
        settings_layout.addRow("Logo:", logo_row_widget)

        left_layout.addWidget(settings_group)

        # ---- Label list (takes remaining vertical space) ----
        self._label_list = LabelListPanel()
        self._label_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._label_list.setMinimumHeight(120)
        left_layout.addWidget(self._label_list, 1)

        # Right panel: preview
        self._preview = PreviewPanel()
        self._preview.setMinimumWidth(200)
        self._preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._preview.set_render_callback(self._render_preview_page)

        # Splitter — left panel gets ~35% by default, preview stretches
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self._preview)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(6)
        # Use proportional initial sizes based on window width
        w = self.width()
        splitter.setSizes([int(w * 0.35), int(w * 0.65)])

        content_layout.addWidget(splitter)
        main_layout.addWidget(content, 1)

    def _build_status_bar(self) -> None:
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_label = QLabel("Ready")
        self._status_bar.addWidget(self._status_label)

    def _connect_signals(self) -> None:
        # Avery selector
        self._avery_selector.template_changed.connect(self._on_avery_changed)

        # Label list
        self._label_list.label_selected.connect(self.label_presenter.select_label)
        self._label_list.add_requested.connect(self.label_presenter.add_label)
        self._label_list.remove_requested.connect(self.label_presenter.remove_label)
        self._label_list.duplicate_requested.connect(self.label_presenter.duplicate_label)
        self._label_list.move_requested.connect(self.label_presenter.move_label)
        self._label_list.fill_sheet_requested.connect(self._on_fill_sheet)
        self._label_list.bulk_search_requested.connect(self._on_bulk_search)
        self._label_list.import_csv_requested.connect(self._on_import_csv)
        self._label_list.label_edited.connect(self._on_label_edited)

    # --- UI change handlers (guard against signal loops during refresh) ---

    def _refresh_xref_combo(self) -> None:
        """Rebuild the xref dropdown to show only manufacturers with data."""
        self._refreshing_ui = True
        try:
            current_key = self._xref_combo.currentData() or ""
            self._xref_combo.clear()
            self._xref_combo.addItem("(none)", "")

            available_keys = self.label_presenter.get_available_xref_keys()
            if available_keys:
                # Build reverse lookup: key -> display name
                key_to_name = {v: k for k, v in XREF_MANUFACTURERS.items() if v}
                for key in sorted(available_keys):
                    display = key_to_name.get(key, key)
                    self._xref_combo.addItem(display, key)

            # Restore previous selection if still available
            idx = self._xref_combo.findData(current_key)
            if idx >= 0:
                self._xref_combo.setCurrentIndex(idx)
            else:
                self._xref_combo.setCurrentIndex(0)
        finally:
            self._refreshing_ui = False

    def _on_avery_changed(self, template_id: str) -> None:
        if not self._refreshing_ui:
            self.label_presenter.set_avery_template(template_id)

    def _on_xref_changed(self, index: int) -> None:
        if not self._refreshing_ui:
            xref_key = self._xref_combo.itemData(index) or ""
            self.label_presenter.set_xref_key(xref_key)

    def _on_desc_mode_changed(self, index: int) -> None:
        if not self._refreshing_ui:
            mode = self._desc_mode_combo.itemData(index) or DESC_MODE_FULL
            self.label_presenter.set_description_mode(mode)

    def _on_start_offset_changed(self, value: int) -> None:
        if not self._refreshing_ui:
            self.label_presenter.set_start_offset(value)

    def _on_qr_url_changed(self, text: str) -> None:
        if not self._refreshing_ui:
            self.label_presenter.set_qr_base_url(text)

    # --- Fill Sheet (with safety check) ---

    def _on_fill_sheet(self) -> None:
        message = self.label_presenter.fill_sheet()
        self._status_label.setText(message)

    # --- Project management ---

    def _refresh_project_list(self) -> None:
        current_text = self._project_combo.currentText()
        self._project_combo.blockSignals(True)
        self._project_combo.clear()
        self._project_combo.addItems(self.project_manager.list_projects())
        if self._current_project_name:
            idx = self._project_combo.findText(self._current_project_name)
            if idx >= 0:
                self._project_combo.setCurrentIndex(idx)
        elif current_text:
            self._project_combo.setEditText(current_text)
        self._project_combo.blockSignals(False)

    def _on_project_save(self) -> bool:
        """Save the current job. Returns True on success."""
        name = self._project_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Enter a customer/job name first.")
            return False
        try:
            self.label_presenter.template.customer_name = name
            self.project_manager.save_project(name, self.label_presenter.template)
            self.label_presenter.mark_clean()
            self._current_project_name = name
            self._refresh_project_list()
            self._status_label.setText(f"Saved job: {name}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Could not save job:\n{e}")
            return False

    def _on_project_load(self) -> None:
        if not self._check_unsaved_changes("load another job"):
            return
        name = self._project_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Select or type a job name.")
            return
        template = self.project_manager.load_project(name)
        if template is None:
            QMessageBox.warning(self, "Warning", f"Job '{name}' not found.")
            return
        self.label_presenter.apply_template(template)
        self._current_project_name = name
        self._status_label.setText(f"Loaded job: {name}")

    def _on_project_save_as(self) -> None:
        current_name = (self._project_combo.currentText().strip()
                        or self.label_presenter.template.customer_name)
        new_name, ok = QInputDialog.getText(
            self, "Save As", "Enter new job name:", text=current_name
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
            self, "Delete Job",
            f"Delete job '{name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.project_manager.delete_project(name)
            self._current_project_name = ""
            self._refresh_project_list()
            self._status_label.setText(f"Deleted job: {name}")

    # --- Menu actions ---

    def _on_new(self) -> None:
        if not self._check_unsaved_changes("create a new job"):
            return
        self._current_project_name = ""
        self._project_combo.setEditText("")
        self.main_presenter.on_new()

    def _on_import_file(self) -> None:
        if not self._check_unsaved_changes("open a job file"):
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Job File", self._last_dir,
            "Label Jobs (*.blm *.json);;All Files (*)"
        )
        if path:
            self._last_dir = str(Path(path).parent)
            name = self.project_manager.import_project(path)
            if name:
                self._current_project_name = name
                template = self.project_manager.load_project(name)
                if template:
                    self.label_presenter.apply_template(template)
                self._refresh_project_list()
                self._status_label.setText(f"Opened job: {name}")
            else:
                QMessageBox.warning(
                    self, "Open Failed", "Could not open the job file."
                )

    def _on_export_template(self) -> None:
        name = (self._current_project_name
                or self.label_presenter.template.customer_name
                or "job")
        suggested = str(Path(self._last_dir) / f"{name}.blm")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Job File", suggested,
            "Label Jobs (*.blm);;JSON (*.json);;All Files (*)"
        )
        if path:
            self._last_dir = str(Path(path).parent)
            if not (path.endswith(".blm") or path.endswith(".json")):
                path += ".blm"
            if self.label_presenter.save_template(path):
                self._status_label.setText(f"Exported job to {path}")
            else:
                self._status_label.setText("Export failed")

    def _on_export_pdf(self) -> None:
        # Run preflight validation
        warnings = self.label_presenter.preflight_check()
        if warnings:
            no_labels = any("No labels" in w for w in warnings)
            if no_labels:
                QMessageBox.warning(self, "Cannot Export", "\n".join(warnings))
                return
            # Show warnings but let user proceed
            msg = "The following issues were found:\n\n" + "\n".join(f"  \u2022 {w}" for w in warnings)
            msg += "\n\nDo you want to export anyway?"
            reply = QMessageBox.question(
                self, "Export Warnings", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        name = (self._current_project_name
                or self.label_presenter.template.customer_name
                or "labels")
        suggested = str(Path(self._last_dir) / f"{name}.pdf")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", suggested,
            "PDF Files (*.pdf);;All Files (*)"
        )
        if path:
            self._last_dir = str(Path(path).parent)
            if not path.endswith(".pdf"):
                path += ".pdf"
            success = self.main_presenter.on_export_pdf(path)
            if success:
                reply = QMessageBox.information(
                    self, "PDF Exported",
                    f"PDF saved to:\n{path}",
                    QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Ok,
                )
                if reply == QMessageBox.StandardButton.Open:
                    if sys.platform == "win32":
                        os.startfile(path)
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", path])
                    else:
                        subprocess.Popen(["xdg-open", path])
                self._status_label.setText(f"PDF exported to {path}")
            else:
                self._status_label.setText("PDF export failed")

    def _pick_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Logo Image", self._last_dir,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if path:
            self._last_dir = str(Path(path).parent)
            self._logo_label.setText(os.path.basename(path))
            self._logo_label.setStyleSheet("color: #333;")
            self.label_presenter.set_logo_path(path)

    # --- CSV/Excel import ---

    def _on_import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Parts from CSV/Excel", self._last_dir,
            "Spreadsheets (*.csv *.xlsx *.xls);;CSV Files (*.csv);;"
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        if not path:
            return
        self._last_dir = str(Path(path).parent)
        try:
            result = import_labels_from_file(path)
            if not result.labels:
                QMessageBox.warning(
                    self, "Import",
                    "No labels found in the file.\n"
                    "Expected columns: brennan_part_number, "
                    "customer_part_number, description",
                )
                return

            self._import_labels(result.labels, source=os.path.basename(path),
                                summary=result.summary())
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import file:\n{e}")

    def _on_paste_labels(self) -> None:
        """Paste labels from clipboard (tab-separated or CSV text)."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if not text or not text.strip():
            self._status_label.setText("Clipboard is empty")
            return
        try:
            result = parse_clipboard_text(text)
            if not result.labels:
                self._status_label.setText("No label data found in clipboard")
                return
            self._import_labels(result.labels, source="clipboard",
                                summary=result.summary())
        except Exception as e:
            QMessageBox.warning(self, "Paste Error", f"Could not parse clipboard data:\n{e}")

    def _import_labels(self, labels: list, source: str = "", summary: str = "") -> None:
        """Common import path for file import and clipboard paste."""
        # Check for duplicates against existing labels
        existing_pns = {l.brennan_part_number for l in self.label_presenter.template.labels
                        if l.brennan_part_number}
        dupe_count = sum(1 for l in labels if l.brennan_part_number in existing_pns)

        # Ask append vs replace vs merge if there are existing labels
        if self.label_presenter.template.labels:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Import Labels")
            info = f"Found {len(labels)} part(s) from {source}."
            if dupe_count:
                info += f"\n{dupe_count} match existing parts in the current job."
            info += f"\n\nYou have {len(self.label_presenter.template.labels)} label(s)."
            msg_box.setText(info)
            if dupe_count:
                msg_box.setInformativeText(
                    "Merge updates existing labels (e.g. fill in Customer P/Ns).\n"
                    "Append adds all as new rows. Replace All clears the job first."
                )
            else:
                msg_box.setInformativeText("Append to existing labels or replace all?")
            if summary:
                msg_box.setDetailedText(summary)

            # Show Merge button when there are matching parts
            merge_btn = None
            if dupe_count:
                merge_btn = msg_box.addButton(
                    "Merge", QMessageBox.ButtonRole.AcceptRole
                )
                msg_box.setDefaultButton(merge_btn)
            append_btn = msg_box.addButton("Append", QMessageBox.ButtonRole.AcceptRole)
            replace_btn = msg_box.addButton("Replace All", QMessageBox.ButtonRole.DestructiveRole)
            msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            if not merge_btn:
                msg_box.setDefaultButton(append_btn)
            msg_box.exec()
            clicked = msg_box.clickedButton()
            if clicked == merge_btn:
                updated, appended = self.label_presenter.merge_labels(labels)
                parts = []
                if updated:
                    parts.append(f"{updated} updated")
                if appended:
                    parts.append(f"{appended} added")
                self._status_label.setText(
                    f"Merged from {source}: {', '.join(parts)}"
                )
                return
            elif clicked == replace_btn:
                self.label_presenter.replace_labels(labels)
                self._status_label.setText(
                    f"Replaced with {len(labels)} labels from {source}"
                )
                return
            elif clicked != append_btn:
                return  # Cancel

        self.label_presenter.add_labels(labels)
        self._status_label.setText(
            f"Imported {len(labels)} labels from {source}"
        )

    # --- Bulk search ---

    def _on_bulk_search(self) -> None:
        xref_key = self.label_presenter.template.xref_key
        dialog = BulkSearchDialog(self.label_presenter.data_source, xref_key, self)
        if dialog.exec():
            selected = dialog.get_selected_parts()
            if not selected:
                return
            self._start_image_download(selected)

    def _start_image_download(self, parts: list) -> None:
        """Download images in a background thread to avoid freezing the UI."""
        self._status_label.setText(f"Downloading images for {len(parts)} parts...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        # Capture xref_key now (thread-safe: don't access presenter from worker)
        xref_key = self.label_presenter.template.xref_key
        self._download_thread = QThread()
        self._download_worker = _ImageDownloadWorker(parts, xref_key)
        self._download_worker.moveToThread(self._download_thread)
        self._download_thread.started.connect(self._download_worker.run)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.finished.connect(self._download_thread.quit)
        self._download_worker.error.connect(self._on_download_error)
        self._download_worker.error.connect(self._download_thread.quit)
        self._download_thread.start()

    def _on_download_progress(self, current: int, total: int) -> None:
        self._status_label.setText(f"Downloading images... {current}/{total}")

    def _on_download_finished(self, labels: list) -> None:
        QApplication.restoreOverrideCursor()
        self.label_presenter.add_labels(labels)
        self._status_label.setText(f"Added {len(labels)} labels from search")
        self._download_thread = None
        self._download_worker = None

    def _on_download_error(self, message: str) -> None:
        QApplication.restoreOverrideCursor()
        self._status_label.setText("Image download failed")
        QMessageBox.warning(self, "Download Error",
                            f"Failed to download part images:\n{message}")
        self._download_thread = None
        self._download_worker = None

    # --- Inline table editing ---

    def _on_label_edited(self, index: int, field: str, value: str) -> None:
        """Handle inline cell edits from the label table."""
        self.label_presenter.update_label_field(index, field, value)

    # --- Preview rendering ---

    def _render_preview_page(self, page: int) -> QPixmap:
        return self.preview_renderer.render(self.label_presenter.template, page)

    # --- View interface (called by LabelPresenter) ---

    def on_template_changed(self, template: Template) -> None:
        """Called when a new template is loaded or created.

        Sets _refreshing_ui to prevent signal handlers from dirtying state.
        """
        self._refreshing_ui = True
        try:
            self._project_combo.setEditText(template.customer_name)
            self._qr_base_url.setText(template.qr_base_url)
            self._avery_selector.set_template_id(template.avery_template_id)

            # Restore description mode
            idx = self._desc_mode_combo.findData(template.description_mode)
            if idx >= 0:
                self._desc_mode_combo.setCurrentIndex(idx)

            # Restore start offset
            self._start_offset_spin.setValue(template.start_offset)

            if template.logo_path:
                self._logo_label.setText(os.path.basename(template.logo_path))
                self._logo_label.setStyleSheet("color: #333;")
            else:
                self._logo_label.setText("No logo selected")
                self._logo_label.setStyleSheet("color: #888; font-style: italic;")
        finally:
            self._refreshing_ui = False

        # Refresh xref dropdown based on available data, then restore selection
        self._refresh_xref_combo()
        if template.xref_key:
            self._refreshing_ui = True
            idx = self._xref_combo.findData(template.xref_key)
            if idx >= 0:
                self._xref_combo.setCurrentIndex(idx)
            self._refreshing_ui = False

        self._label_list.update_labels(
            template.labels, description_mode=template.description_mode
        )
        self._update_status(template)
        self._preview.request_update()

    def on_labels_changed(self, labels: List[LabelData], selected_index: int) -> None:
        """Called when the label list changes (add/remove/edit)."""
        mode = self.label_presenter.template.description_mode
        self._label_list.update_labels(labels, selected_index, description_mode=mode)
        self._refresh_xref_combo()
        self._update_status(self.label_presenter.template)
        self._preview.request_update()

    def on_label_selected(self, label: Optional[LabelData], index: int) -> None:
        """Called when a label is selected in the list."""
        if label and index >= 0:
            self._preview.zoom_to_label(index)

    def on_preview_update_needed(self) -> None:
        """Called when preview needs re-rendering."""
        self._preview.request_update()

    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)

    def _update_status(self, template: Template) -> None:
        geo = AVERY_TEMPLATES.get(template.avery_template_id)
        name = geo.name if geo else "Unknown"
        count = len(template.labels)
        # Update label grid positions for zoom-to-label
        if geo:
            positions = _layout_service.compute_label_positions(geo)
            self._preview.set_label_grid(
                positions, geo.labels_per_page, template.start_offset,
                page_height_pt=geo.page_height_pt,
            )
            # Update start offset max based on template
            self._refreshing_ui = True
            self._start_offset_spin.setMaximum(geo.labels_per_page - 1)
            self._refreshing_ui = False

        per_page = geo.labels_per_page if geo else 0
        pages = (
            max(1, (count + template.start_offset + per_page - 1) // per_page)
            if per_page
            else 1
        )
        project = self._current_project_name or template.customer_name or "Untitled"
        self._status_label.setText(
            f"  {project}  |  {name}  |  {count} labels  |  {pages} page(s)"
        )
        self._preview.set_total_pages(pages)
