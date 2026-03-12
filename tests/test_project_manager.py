"""Tests for ProjectManager — save/load, sanitization, portability."""
import json
import os
import pytest

from src.models.template import Template
from src.models.label_data import LabelData
from src.services.project_manager import ProjectManager, _sanitize_name


class TestSanitizeName:
    def test_clean_name_unchanged(self):
        assert _sanitize_name("ACME Corp") == "ACME Corp"

    def test_removes_path_separators(self):
        result = _sanitize_name("customer/job")
        assert "/" not in result
        assert "\\" not in result

    def test_removes_special_chars(self):
        result = _sanitize_name('test<>:"|?*name')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result

    def test_empty_becomes_untitled(self):
        assert _sanitize_name("") == "untitled"
        assert _sanitize_name("...") == "untitled"

    def test_dots_and_spaces_stripped(self):
        result = _sanitize_name("  test.  ")
        assert result == "test"


class TestProjectManager:
    @pytest.fixture
    def pm(self, tmp_path, monkeypatch):
        """ProjectManager with a temp projects directory."""
        monkeypatch.setattr(
            "src.services.project_manager.get_projects_dir",
            lambda: tmp_path,
        )
        return ProjectManager()

    def test_save_and_load(self, pm):
        t = Template(customer_name="ACME", avery_template_id="5163")
        t.labels.append(LabelData(brennan_part_number="X-1", description="Test"))
        pm.save_project("ACME", t)
        loaded = pm.load_project("ACME")
        assert loaded is not None
        assert loaded.customer_name == "ACME"
        assert loaded.avery_template_id == "5163"
        assert len(loaded.labels) == 1
        assert loaded.labels[0].brennan_part_number == "X-1"

    def test_list_projects(self, pm):
        pm.save_project("Alpha", Template(customer_name="Alpha"))
        pm.save_project("Beta", Template(customer_name="Beta"))
        projects = pm.list_projects()
        assert "Alpha" in projects
        assert "Beta" in projects

    def test_delete_project(self, pm):
        pm.save_project("Test", Template())
        assert "Test" in pm.list_projects()
        pm.delete_project("Test")
        assert "Test" not in pm.list_projects()

    def test_load_nonexistent_returns_none(self, pm):
        assert pm.load_project("nonexistent") is None

    def test_roundtrip_all_fields(self, pm):
        t = Template(
            customer_name="Full Test",
            avery_template_id="5164",
            qr_base_url="https://example.com/",
            xref_key="parker_part_number",
            description_mode="short",
            start_offset=7,
            labels=[
                LabelData(
                    brennan_part_number="A-1",
                    customer_part_number="C-1",
                    description="Full desc",
                    short_description="Short",
                ),
            ],
        )
        pm.save_project("Full Test", t)
        loaded = pm.load_project("Full Test")
        assert loaded.avery_template_id == "5164"
        assert loaded.qr_base_url == "https://example.com/"
        assert loaded.xref_key == "parker_part_number"
        assert loaded.description_mode == "short"
        assert loaded.start_offset == 7
        assert loaded.labels[0].short_description == "Short"

    def test_import_export(self, pm, tmp_path):
        t = Template(customer_name="Export Test")
        t.labels.append(LabelData(brennan_part_number="E-1"))
        pm.save_project("Export Test", t)

        export_path = str(tmp_path / "exported.blm")
        pm.export_project("Export Test", export_path)
        assert os.path.isfile(export_path)

        # Import into a fresh manager
        name = pm.import_project(export_path)
        assert name == "Export Test"

    def test_sanitized_name_save_load(self, pm):
        """Names with special chars should still save/load."""
        t = Template(customer_name="Test/Special:Name")
        pm.save_project("Test/Special:Name", t)
        loaded = pm.load_project("Test/Special:Name")
        assert loaded is not None
