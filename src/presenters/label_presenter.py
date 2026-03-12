"""Presenter for label editing and list management.

Mediates between the label views and the service layer.
Views call presenter methods; presenter updates views via direct method calls.
"""
import logging
from typing import Optional

from src.models.label_data import LabelData
from src.models.template import Template
from src.models.avery_templates import AVERY_TEMPLATES
from src.services.pdf_renderer import PDFRenderer
from src.services.template_io import TemplateIO
from src.services.data_source import DataSource

logger = logging.getLogger(__name__)


class LabelPresenter:
    """Orchestrates label editing, template management, and PDF export."""

    def __init__(
        self,
        pdf_renderer: PDFRenderer,
        template_io: TemplateIO,
        data_source: DataSource,
        default_logo_path: Optional[str] = None,
    ):
        self.pdf_renderer = pdf_renderer
        self.template_io = template_io
        self.data_source = data_source
        self._default_logo_path = default_logo_path
        self.template = Template()
        self._current_index: int = -1
        self._dirty: bool = False  # tracks unsaved changes
        self._view = None  # set by main_window after construction

    def set_view(self, view) -> None:
        """Called by MainWindow to register the view interface."""
        self._view = view

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def mark_clean(self) -> None:
        self._dirty = False

    @property
    def current_label(self) -> Optional[LabelData]:
        if 0 <= self._current_index < len(self.template.labels):
            return self.template.labels[self._current_index]
        return None

    # --- Template operations ---

    def new_template(self) -> None:
        self.template = Template()
        if self._default_logo_path:
            self.template.logo_path = self._default_logo_path
        self._current_index = -1
        self._dirty = False
        self._notify_template_changed()

    def load_template(self, file_path: str) -> None:
        try:
            self.template = self.template_io.load(file_path)
            self._current_index = 0 if self.template.labels else -1
            self._notify_template_changed()
            logger.info("Loaded template from %s", file_path)
        except Exception as e:
            logger.error("Failed to load template: %s", e)
            if self._view:
                self._view.show_error(f"Failed to load template:\n{e}")

    def save_template(self, file_path: str) -> None:
        try:
            self.template_io.save(self.template, file_path)
            self._dirty = False
            logger.info("Saved template to %s", file_path)
        except Exception as e:
            logger.error("Failed to save template: %s", e)
            if self._view:
                self._view.show_error(f"Failed to save template:\n{e}")

    def export_pdf(self, output_path: str) -> None:
        try:
            self.pdf_renderer.render(self.template, output_path)
            logger.info("Exported PDF to %s", output_path)
        except Exception as e:
            logger.error("Failed to export PDF: %s", e)
            if self._view:
                self._view.show_error(f"Failed to export PDF:\n{e}")

    # --- Avery template selection ---

    def set_avery_template(self, template_id: str) -> None:
        if template_id in AVERY_TEMPLATES:
            self.template.avery_template_id = template_id
            self._dirty = True
            self._notify_preview_update()

    # --- Template metadata ---

    def set_customer_name(self, name: str) -> None:
        self.template.customer_name = name
        self._dirty = True

    def set_qr_base_url(self, url: str) -> None:
        self.template.qr_base_url = url
        self._dirty = True
        self._notify_preview_update()

    def set_logo_path(self, path: Optional[str]) -> None:
        self.template.logo_path = path
        self._dirty = True
        self._notify_preview_update()

    def set_xref_key(self, xref_key: str) -> None:
        self.template.xref_key = xref_key
        self._dirty = True

    def set_description_mode(self, mode: str) -> None:
        self.template.description_mode = mode
        self._dirty = True
        self._notify_list_changed()

    def set_start_offset(self, offset: int) -> None:
        self.template.start_offset = max(0, offset)
        self._dirty = True
        self._notify_preview_update()

    # --- Label list operations ---

    def add_label(self) -> None:
        label = LabelData()
        self.template.labels.append(label)
        self._current_index = len(self.template.labels) - 1
        self._dirty = True
        self._notify_list_changed()
        self._notify_label_selected()

    def remove_label(self, index: int) -> None:
        if 0 <= index < len(self.template.labels):
            self.template.labels.pop(index)
            if self._current_index >= len(self.template.labels):
                self._current_index = len(self.template.labels) - 1
            self._dirty = True
            self._notify_list_changed()
            self._notify_label_selected()

    def duplicate_label(self, index: int) -> None:
        if 0 <= index < len(self.template.labels):
            source = self.template.labels[index]
            copy = LabelData(
                brennan_part_number=source.brennan_part_number,
                customer_part_number=source.customer_part_number,
                description=source.description,
                short_description=source.short_description,
                image_path=source.image_path,
            )
            self.template.labels.insert(index + 1, copy)
            self._current_index = index + 1
            self._dirty = True
            self._notify_list_changed()
            self._notify_label_selected()

    def add_labels(self, labels: list) -> None:
        """Add multiple labels at once (from bulk search, CSV import, etc.)."""
        if not labels:
            return
        for label in labels:
            self.template.labels.append(label)
        self._current_index = len(self.template.labels) - 1
        self._dirty = True
        self._notify_list_changed()
        self._notify_label_selected()

    def apply_template(self, template) -> None:
        """Replace the current template entirely (for project load / import)."""
        self.template = template
        self._current_index = 0 if template.labels else -1
        self._dirty = False
        self._notify_template_changed()

    def fill_sheet(self) -> None:
        """Fill remaining label slots on the current page with copies of selected label."""
        geo = AVERY_TEMPLATES[self.template.avery_template_id]
        per_page = geo.labels_per_page
        current_count = len(self.template.labels) + self.template.start_offset
        remaining = per_page - (current_count % per_page)
        if remaining == per_page:
            return  # already full

        source = self.current_label or LabelData()
        for _ in range(remaining):
            self.template.labels.append(LabelData(
                brennan_part_number=source.brennan_part_number,
                customer_part_number=source.customer_part_number,
                description=source.description,
                short_description=source.short_description,
                image_path=source.image_path,
            ))
        self._dirty = True
        self._notify_list_changed()

    def select_label(self, index: int) -> None:
        self._current_index = index
        self._notify_label_selected()

    # --- Label editing ---

    def update_label_field(self, index: int, field: str, value: str) -> None:
        """Update a single field on a label by index."""
        if 0 <= index < len(self.template.labels):
            label = self.template.labels[index]
            if field == "brennan_pn":
                label.brennan_part_number = value
            elif field == "customer_pn":
                label.customer_part_number = value
            elif field == "description":
                if self.template.description_mode == "short":
                    label.short_description = value
                else:
                    label.description = value
            self._dirty = True
            self._notify_preview_update()

    # --- Catsy lookup ---

    def lookup_part(self, query: str) -> list:
        """Search for parts via the data source. Returns list of result dicts."""
        return self.data_source.search_parts(query)

    # --- View notifications ---

    def _notify_template_changed(self) -> None:
        if self._view:
            self._view.on_template_changed(self.template)

    def _notify_list_changed(self) -> None:
        if self._view:
            self._view.on_labels_changed(self.template.labels, self._current_index)

    def _notify_label_selected(self) -> None:
        if self._view:
            self._view.on_label_selected(self.current_label, self._current_index)

    def _notify_preview_update(self) -> None:
        if self._view:
            self._view.on_preview_update_needed()
