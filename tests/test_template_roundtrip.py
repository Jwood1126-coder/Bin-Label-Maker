"""Tests for save/load roundtrip fidelity."""
import json
import os
import pytest

from src.models.template import Template, DESC_MODE_SHORT
from src.models.label_data import LabelData
from src.services.template_io import TemplateIO


class TestTemplateRoundtrip:
    def test_empty_template_roundtrip(self, tmp_path):
        io = TemplateIO()
        original = Template()
        path = str(tmp_path / "test.blm")
        io.save(original, path)
        loaded = io.load(path)

        assert loaded.customer_name == original.customer_name
        assert loaded.avery_template_id == original.avery_template_id
        assert loaded.qr_base_url == original.qr_base_url
        assert loaded.xref_key == original.xref_key
        assert loaded.description_mode == original.description_mode
        assert loaded.start_offset == original.start_offset
        assert loaded.labels == []

    def test_full_template_roundtrip(self, tmp_path):
        io = TemplateIO()
        original = Template(
            customer_name="ACME Corp",
            avery_template_id="5163",
            qr_base_url="https://example.com/",
            xref_key="parker_part_number",
            description_mode=DESC_MODE_SHORT,
            start_offset=3,
            labels=[
                LabelData(
                    brennan_part_number="2404-04-02",
                    customer_part_number="PARKER-001",
                    description="Full description text",
                    short_description="Short desc",
                    xrefs={"parker_part_number": "PARKER-001", "swagelok_part_number": "SWAG-001"},
                ),
                LabelData(
                    brennan_part_number="2404-06-04",
                    customer_part_number="PARKER-002",
                    description="Another full desc",
                    short_description="Another short",
                    xrefs={"parker_part_number": "PARKER-002"},
                ),
            ],
        )
        path = str(tmp_path / "test.blm")
        io.save(original, path)
        loaded = io.load(path)

        assert loaded.customer_name == "ACME Corp"
        assert loaded.avery_template_id == "5163"
        assert loaded.qr_base_url == "https://example.com/"
        assert loaded.xref_key == "parker_part_number"
        assert loaded.description_mode == DESC_MODE_SHORT
        assert loaded.start_offset == 3
        assert len(loaded.labels) == 2
        assert loaded.labels[0].brennan_part_number == "2404-04-02"
        assert loaded.labels[0].customer_part_number == "PARKER-001"
        assert loaded.labels[0].description == "Full description text"
        assert loaded.labels[0].short_description == "Short desc"
        assert loaded.labels[0].xrefs == {"parker_part_number": "PARKER-001", "swagelok_part_number": "SWAG-001"}
        assert loaded.labels[1].brennan_part_number == "2404-06-04"
        assert loaded.labels[1].xrefs == {"parker_part_number": "PARKER-002"}

    def test_forward_compatible_loading(self, tmp_path):
        """Unknown fields in JSON should be tolerated."""
        path = str(tmp_path / "future.blm")
        data = {
            "customer_name": "Test",
            "avery_template_id": "5160",
            "future_field": "some_value",
            "labels": [
                {
                    "brennan_part_number": "X-1",
                    "customer_part_number": "",
                    "description": "test",
                    "short_description": "",
                    "new_future_field": 42,
                }
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f)

        io = TemplateIO()
        loaded = io.load(path)
        assert loaded.customer_name == "Test"
        assert len(loaded.labels) == 1
        assert loaded.labels[0].brennan_part_number == "X-1"

    def test_missing_fields_get_defaults(self, tmp_path):
        """Minimal JSON should load with defaults for missing fields."""
        path = str(tmp_path / "minimal.blm")
        data = {"labels": [{"brennan_part_number": "X-1"}]}
        with open(path, "w") as f:
            json.dump(data, f)

        io = TemplateIO()
        loaded = io.load(path)
        assert loaded.customer_name == ""
        assert loaded.avery_template_id == "5160"
        assert loaded.description_mode == "full"
        assert loaded.start_offset == 0
        assert len(loaded.labels) == 1
        assert loaded.labels[0].xrefs == {}

    def test_xrefs_absent_from_old_files(self, tmp_path):
        """Labels saved before xrefs was added should load with empty xrefs."""
        path = str(tmp_path / "old.blm")
        data = {"labels": [{"brennan_part_number": "X-1", "customer_part_number": "C-1"}]}
        with open(path, "w") as f:
            json.dump(data, f)

        io = TemplateIO()
        loaded = io.load(path)
        assert loaded.labels[0].xrefs == {}
        assert loaded.labels[0].customer_part_number == "C-1"

    def test_xrefs_not_saved_when_empty(self, tmp_path):
        """Labels without xrefs should not include xrefs key in JSON (smaller files)."""
        io = TemplateIO()
        original = Template(labels=[LabelData(brennan_part_number="X-1")])
        path = str(tmp_path / "test.blm")
        io.save(original, path)
        with open(path, "r") as f:
            data = json.load(f)
        assert "xrefs" not in data["labels"][0]


class TestLabelDataXrefs:
    def test_resolve_customer_pn_with_xref(self):
        label = LabelData(
            brennan_part_number="2404-04-02",
            customer_part_number="PARKER-001",
            xrefs={"parker_part_number": "PARKER-001", "swagelok_part_number": "SWAG-001"},
        )
        assert label.resolve_customer_pn("parker_part_number") == "PARKER-001"
        assert label.resolve_customer_pn("swagelok_part_number") == "SWAG-001"
        assert label.resolve_customer_pn("gates_part_number") == ""
        assert label.resolve_customer_pn("") == "PARKER-001"  # no key = manual value

    def test_resolve_customer_pn_no_xrefs(self):
        label = LabelData(
            brennan_part_number="X-1",
            customer_part_number="MANUAL-PN",
        )
        assert label.resolve_customer_pn("parker_part_number") == "MANUAL-PN"
        assert label.resolve_customer_pn("") == "MANUAL-PN"

    def test_available_xref_keys(self):
        label = LabelData(
            xrefs={"parker_part_number": "P-1", "swagelok_part_number": "", "gates_part_number": "G-1"},
        )
        assert label.available_xref_keys() == {"parker_part_number", "gates_part_number"}
