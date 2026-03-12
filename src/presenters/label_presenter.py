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

    def save_template(self, file_path: str) -> bool:
        """Save template to file. Returns True on success."""
        try:
            self.template_io.save(self.template, file_path)
            self._dirty = False
            logger.info("Saved template to %s", file_path)
            return True
        except Exception as e:
            logger.error("Failed to save template: %s", e)
            if self._view:
                self._view.show_error(f"Failed to save template:\n{e}")
            return False

    def export_pdf(self, output_path: str) -> bool:
        """Export PDF. Returns True on success."""
        try:
            self.pdf_renderer.render(self.template, output_path)
            logger.info("Exported PDF to %s", output_path)
            return True
        except Exception as e:
            logger.error("Failed to export PDF: %s", e)
            if self._view:
                self._view.show_error(f"Failed to export PDF:\n{e}")
            return False

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
        # Re-resolve customer P/Ns for all labels that have stored xrefs
        for label in self.template.labels:
            if label.xrefs:
                label.customer_part_number = label.resolve_customer_pn(xref_key)
        self._dirty = True
        self._notify_list_changed()

    def get_available_xref_keys(self) -> set:
        """Return the set of xref keys that have data across all labels."""
        keys = set()
        for label in self.template.labels:
            keys.update(label.available_xref_keys())
        return keys

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
                xrefs=dict(source.xrefs),
            )
            self.template.labels.insert(index + 1, copy)
            self._current_index = index + 1
            self._dirty = True
            self._notify_list_changed()
            self._notify_label_selected()

    def move_label(self, index: int, direction: int) -> None:
        """Move a label up (direction=-1) or down (direction=1)."""
        new_index = index + direction
        if 0 <= index < len(self.template.labels) and 0 <= new_index < len(self.template.labels):
            labels = self.template.labels
            labels[index], labels[new_index] = labels[new_index], labels[index]
            self._current_index = new_index
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

    def fill_sheet(self) -> str:
        """Fill remaining label slots on the current page with copies of selected label.

        Returns a status message describing what happened.
        """
        source = self.current_label
        if not source or source.is_empty():
            return "Select a non-empty label first to fill the sheet with copies of it."

        geo = AVERY_TEMPLATES[self.template.avery_template_id]
        per_page = geo.labels_per_page
        current_count = len(self.template.labels) + self.template.start_offset
        remaining = per_page - (current_count % per_page)
        if remaining == per_page:
            return "Sheet is already full."

        for _ in range(remaining):
            self.template.labels.append(LabelData(
                brennan_part_number=source.brennan_part_number,
                customer_part_number=source.customer_part_number,
                description=source.description,
                short_description=source.short_description,
                image_path=source.image_path,
                xrefs=dict(source.xrefs),
            ))
        self._dirty = True
        self._notify_list_changed()
        return f"Added {remaining} copies of '{source.brennan_part_number}' to fill the sheet."

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
                label.description = value
            elif field == "short_description":
                label.short_description = value
            self._dirty = True
            self._notify_preview_update()

    def merge_labels(self, incoming: list) -> tuple:
        """Merge incoming labels into existing by matching Brennan P/N.

        For matching labels: updates customer_part_number (and description/
        short_description if the incoming value is non-empty).
        Non-matching incoming labels are appended.

        Returns (updated_count, appended_count).
        """
        existing_by_pn = {}
        for label in self.template.labels:
            if label.brennan_part_number:
                existing_by_pn.setdefault(label.brennan_part_number, []).append(label)

        updated = 0
        appended = 0
        for inc in incoming:
            matches = existing_by_pn.get(inc.brennan_part_number, [])
            if matches:
                for existing in matches:
                    if inc.customer_part_number:
                        existing.customer_part_number = inc.customer_part_number
                    if inc.description:
                        existing.description = inc.description
                    if inc.short_description:
                        existing.short_description = inc.short_description
                    if inc.xrefs:
                        existing.xrefs.update(inc.xrefs)
                updated += 1
            else:
                self.template.labels.append(inc)
                appended += 1

        if updated or appended:
            self._current_index = len(self.template.labels) - 1
            self._dirty = True
            self._notify_list_changed()
            self._notify_label_selected()

        return updated, appended

    def replace_labels(self, labels: list) -> None:
        """Replace all labels (for import-replace mode)."""
        self.template.labels = list(labels)
        self._current_index = 0 if labels else -1
        self._dirty = True
        self._notify_list_changed()
        self._notify_label_selected()

    def preflight_check(self) -> list[str]:
        """Run preflight validation before export. Returns list of warning messages."""
        import os
        from collections import Counter

        warnings = []
        if not self.template.labels:
            warnings.append("No labels to export.")
            return warnings

        empty_count = sum(1 for l in self.template.labels if l.is_empty())
        if empty_count:
            warnings.append(f"{empty_count} label(s) are completely empty.")

        missing_brennan = sum(1 for l in self.template.labels
                             if not l.brennan_part_number and not l.is_empty())
        if missing_brennan:
            warnings.append(f"{missing_brennan} label(s) have no Brennan part number (no QR code will be generated).")

        # Duplicate detection
        pn_counts = Counter(l.brennan_part_number for l in self.template.labels
                           if l.brennan_part_number)
        dupes = {pn: count for pn, count in pn_counts.items() if count > 1}
        if dupes:
            dupe_list = ", ".join(f"{pn} (\u00d7{count})" for pn, count in list(dupes.items())[:5])
            suffix = f" and {len(dupes) - 5} more" if len(dupes) > 5 else ""
            warnings.append(f"Duplicate part numbers: {dupe_list}{suffix}")

        # Partially filled last page
        geo = AVERY_TEMPLATES.get(self.template.avery_template_id)
        if geo:
            per_page = geo.labels_per_page
            total_slots = len(self.template.labels) + self.template.start_offset
            remainder = total_slots % per_page
            if remainder > 0:
                blank_on_last = per_page - remainder
                warnings.append(f"Last page has {blank_on_last} empty slot(s) out of {per_page}.")

        if self.template.logo_path:
            if not os.path.isfile(self.template.logo_path):
                warnings.append(f"Logo file not found: {self.template.logo_path}")

        return warnings

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
