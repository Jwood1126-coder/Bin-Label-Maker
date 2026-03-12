"""Tests for LabelPresenter logic — dirty tracking, fill sheet, preflight."""
import pytest

from src.models.label_data import LabelData
from src.models.template import Template
from src.models.avery_templates import AVERY_TEMPLATES
from src.services.label_layout import LabelLayoutService
from src.services.qr_generator import QRGenerator
from src.services.pdf_renderer import PDFRenderer
from src.services.template_io import TemplateIO
from src.services.catsy_mock import MockCatsyService
from src.presenters.label_presenter import LabelPresenter


class FakeView:
    """Minimal view stub that records calls."""
    def __init__(self):
        self.calls = []

    def on_template_changed(self, template):
        self.calls.append(("template_changed", template))

    def on_labels_changed(self, labels, index):
        self.calls.append(("labels_changed", len(labels), index))

    def on_label_selected(self, label, index):
        self.calls.append(("label_selected", index))

    def on_preview_update_needed(self):
        self.calls.append(("preview_update",))

    def show_error(self, message):
        self.calls.append(("error", message))


def _make_presenter() -> tuple[LabelPresenter, FakeView]:
    layout = LabelLayoutService()
    qr = QRGenerator()
    pdf = PDFRenderer(layout, qr)
    io = TemplateIO()
    ds = MockCatsyService()
    p = LabelPresenter(pdf, io, ds)
    v = FakeView()
    p.set_view(v)
    return p, v


class TestDirtyTracking:
    def test_new_template_is_clean(self):
        p, v = _make_presenter()
        p.new_template()
        assert not p.is_dirty

    def test_adding_label_marks_dirty(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        assert p.is_dirty

    def test_mark_clean_works(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        assert p.is_dirty
        p.mark_clean()
        assert not p.is_dirty

    def test_apply_template_is_clean(self):
        p, v = _make_presenter()
        p.add_label()
        assert p.is_dirty
        p.apply_template(Template())
        assert not p.is_dirty

    def test_setting_customer_name_marks_dirty(self):
        p, v = _make_presenter()
        p.new_template()
        p.set_customer_name("Test")
        assert p.is_dirty

    def test_setting_avery_template_marks_dirty(self):
        p, v = _make_presenter()
        p.new_template()
        p.set_avery_template("5163")
        assert p.is_dirty

    def test_update_label_field_marks_dirty(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.mark_clean()
        p.update_label_field(0, "brennan_pn", "X-1")
        assert p.is_dirty

    def test_save_template_marks_clean(self, tmp_path):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        assert p.is_dirty
        path = str(tmp_path / "test.blm")
        result = p.save_template(path)
        assert result is True
        assert not p.is_dirty


class TestFillSheet:
    def test_fill_sheet_requires_selection(self):
        p, v = _make_presenter()
        p.new_template()
        msg = p.fill_sheet()
        assert "Select" in msg

    def test_fill_sheet_requires_non_empty_label(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()  # adds empty label
        p.select_label(0)
        msg = p.fill_sheet()
        assert "Select" in msg or "non-empty" in msg

    def test_fill_sheet_fills_correctly(self):
        p, v = _make_presenter()
        p.new_template()
        p.template.avery_template_id = "5160"  # 30 per page
        p.add_label()
        p.template.labels[0].brennan_part_number = "X-1"
        p.select_label(0)
        msg = p.fill_sheet()
        assert "29" in msg  # should fill 29 more to make 30
        assert len(p.template.labels) == 30

    def test_fill_sheet_already_full(self):
        p, v = _make_presenter()
        p.new_template()
        p.template.avery_template_id = "5160"
        for _ in range(30):
            p.template.labels.append(LabelData(brennan_part_number="X-1"))
        p.select_label(0)
        msg = p.fill_sheet()
        assert "full" in msg.lower()
        assert len(p.template.labels) == 30

    def test_fill_sheet_respects_start_offset(self):
        p, v = _make_presenter()
        p.new_template()
        p.template.avery_template_id = "5160"  # 30 per page
        p.template.start_offset = 5
        p.add_label()
        p.template.labels[0].brennan_part_number = "X-1"
        p.select_label(0)
        p.fill_sheet()
        # offset 5 + 1 label = 6 slots used, need 24 more
        assert len(p.template.labels) == 25


class TestPreflight:
    def test_preflight_empty_labels(self):
        p, v = _make_presenter()
        p.new_template()
        warnings = p.preflight_check()
        assert any("No labels" in w for w in warnings)

    def test_preflight_warns_empty_labels(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()  # empty
        p.add_label()
        p.template.labels[1].brennan_part_number = "X-1"
        warnings = p.preflight_check()
        assert any("empty" in w.lower() for w in warnings)

    def test_preflight_warns_missing_brennan(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].customer_part_number = "CUST-1"  # non-empty but no brennan
        warnings = p.preflight_check()
        assert any("Brennan part number" in w for w in warnings)

    def test_preflight_clean_labels_no_critical_warnings(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "X-1"
        warnings = p.preflight_check()
        # Only informational warnings (partial page) expected, no critical issues
        assert not any("empty" in w.lower() and "label" in w.lower() for w in warnings)
        assert not any("No labels" in w for w in warnings)
        assert not any("Brennan part number" in w for w in warnings)


class TestLabelEditing:
    def test_update_description_field(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.update_label_field(0, "description", "Full text")
        assert p.template.labels[0].description == "Full text"

    def test_update_short_description_field(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.update_label_field(0, "short_description", "Short text")
        assert p.template.labels[0].short_description == "Short text"

    def test_replace_labels(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.add_label()
        assert len(p.template.labels) == 2

        new_labels = [LabelData(brennan_part_number="Y-1")]
        p.replace_labels(new_labels)
        assert len(p.template.labels) == 1
        assert p.template.labels[0].brennan_part_number == "Y-1"
        assert p.is_dirty

    def test_move_label_down(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "A"
        p.add_label()
        p.template.labels[1].brennan_part_number = "B"
        p.move_label(0, 1)
        assert p.template.labels[0].brennan_part_number == "B"
        assert p.template.labels[1].brennan_part_number == "A"
        assert p.is_dirty

    def test_move_label_up(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "A"
        p.add_label()
        p.template.labels[1].brennan_part_number = "B"
        p.move_label(1, -1)
        assert p.template.labels[0].brennan_part_number == "B"
        assert p.template.labels[1].brennan_part_number == "A"

    def test_move_label_out_of_bounds_noop(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "A"
        p.mark_clean()
        p.move_label(0, -1)  # can't move first item up
        assert p.template.labels[0].brennan_part_number == "A"
        assert not p.is_dirty  # no change happened


class TestPreflightDuplicates:
    def test_preflight_warns_duplicates(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "X-1"
        p.add_label()
        p.template.labels[1].brennan_part_number = "X-1"
        warnings = p.preflight_check()
        assert any("Duplicate" in w for w in warnings)

    def test_preflight_no_duplicate_warning_for_unique(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "X-1"
        p.add_label()
        p.template.labels[1].brennan_part_number = "X-2"
        warnings = p.preflight_check()
        assert not any("Duplicate" in w for w in warnings)

    def test_preflight_warns_partial_page(self):
        p, v = _make_presenter()
        p.new_template()
        p.template.avery_template_id = "5160"  # 30 per page
        p.add_label()
        p.template.labels[0].brennan_part_number = "X-1"
        warnings = p.preflight_check()
        assert any("empty slot" in w for w in warnings)


class TestXrefResolution:
    def test_set_xref_key_updates_customer_pns(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "2404-04-02"
        p.template.labels[0].xrefs = {
            "parker_part_number": "PARKER-001",
            "swagelok_part_number": "SWAG-001",
        }
        p.template.labels[0].customer_part_number = ""

        p.set_xref_key("parker_part_number")
        assert p.template.labels[0].customer_part_number == "PARKER-001"

        p.set_xref_key("swagelok_part_number")
        assert p.template.labels[0].customer_part_number == "SWAG-001"

        p.set_xref_key("gates_part_number")
        assert p.template.labels[0].customer_part_number == ""

    def test_set_xref_key_no_xrefs_preserves_manual(self):
        """Labels without xrefs (e.g. from CSV import) keep their manual customer P/N."""
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].customer_part_number = "MANUAL-PN"

        p.set_xref_key("parker_part_number")
        assert p.template.labels[0].customer_part_number == "MANUAL-PN"

    def test_get_available_xref_keys(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].xrefs = {"parker_part_number": "P-1", "gates_part_number": "G-1"}
        p.add_label()
        p.template.labels[1].xrefs = {"parker_part_number": "P-2", "swagelok_part_number": "S-2"}

        keys = p.get_available_xref_keys()
        assert keys == {"parker_part_number", "gates_part_number", "swagelok_part_number"}

    def test_duplicate_preserves_xrefs(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].xrefs = {"parker_part_number": "P-1"}
        p.duplicate_label(0)
        assert p.template.labels[1].xrefs == {"parker_part_number": "P-1"}
        # Ensure it's a copy, not a shared reference
        p.template.labels[1].xrefs["new_key"] = "val"
        assert "new_key" not in p.template.labels[0].xrefs


class TestMergeLabels:
    def test_merge_updates_customer_pn(self):
        """Merge should fill in customer P/N on matching Brennan P/Ns."""
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "2404-04-02"
        p.template.labels[0].description = "Existing desc"
        p.add_label()
        p.template.labels[1].brennan_part_number = "2404-06-04"

        incoming = [
            LabelData(brennan_part_number="2404-04-02", customer_part_number="CUST-001"),
            LabelData(brennan_part_number="2404-06-04", customer_part_number="CUST-002"),
        ]
        updated, appended = p.merge_labels(incoming)
        assert updated == 2
        assert appended == 0
        assert p.template.labels[0].customer_part_number == "CUST-001"
        assert p.template.labels[0].description == "Existing desc"  # preserved
        assert p.template.labels[1].customer_part_number == "CUST-002"

    def test_merge_appends_non_matching(self):
        """Parts not in current job should be appended."""
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "2404-04-02"

        incoming = [
            LabelData(brennan_part_number="2404-04-02", customer_part_number="CUST-001"),
            LabelData(brennan_part_number="NEW-PART", customer_part_number="CUST-NEW"),
        ]
        updated, appended = p.merge_labels(incoming)
        assert updated == 1
        assert appended == 1
        assert len(p.template.labels) == 2
        assert p.template.labels[1].brennan_part_number == "NEW-PART"

    def test_merge_does_not_overwrite_with_empty(self):
        """Merge should not blank out existing data with empty incoming fields."""
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "2404-04-02"
        p.template.labels[0].customer_part_number = "EXISTING"
        p.template.labels[0].description = "Existing desc"

        incoming = [
            LabelData(brennan_part_number="2404-04-02", customer_part_number="UPDATED"),
        ]
        updated, _ = p.merge_labels(incoming)
        assert updated == 1
        assert p.template.labels[0].customer_part_number == "UPDATED"
        assert p.template.labels[0].description == "Existing desc"  # not blanked

    def test_merge_marks_dirty(self):
        p, v = _make_presenter()
        p.new_template()
        p.add_label()
        p.template.labels[0].brennan_part_number = "X-1"
        p.mark_clean()

        incoming = [LabelData(brennan_part_number="X-1", customer_part_number="C-1")]
        p.merge_labels(incoming)
        assert p.is_dirty
