"""Project-style customer template management.

Stores customer label projects as .blm (Bin Label Maker) JSON files
in an app data directory for quick save/load by name, similar to the
Drawing-Generator's .dgp project system.

Projects can also be exported/imported to arbitrary locations.
"""
import json
import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional

from src.models.template import Template
from src.models.label_data import LabelData

logger = logging.getLogger(__name__)

BLM_VERSION = "1.0"
PROJECT_EXT = ".blm"


def get_app_data_dir() -> Path:
    """Get the application data directory for storing project files."""
    if os.name == "nt":
        app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
        state_dir = Path(app_data) / "BinLabelMaker"
    else:
        state_dir = Path.home() / ".bin_label_maker"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def get_projects_dir() -> Path:
    """Get the projects subfolder."""
    projects_dir = get_app_data_dir() / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    return projects_dir


class ProjectManager:
    """Manages named customer label projects.

    Projects are saved as .blm JSON files in the app data directory
    for instant access via a combo box dropdown.
    """

    def __init__(self):
        self._projects_dir = get_projects_dir()

    def list_projects(self) -> List[str]:
        """Return sorted list of all saved project names."""
        return sorted(
            p.stem for p in self._projects_dir.glob(f"*{PROJECT_EXT}")
        )

    def save_project(self, name: str, template: Template) -> None:
        """Save a template as a named project."""
        path = self._projects_dir / f"{name}{PROJECT_EXT}"
        data = template.to_dict()
        data["version"] = BLM_VERSION
        data["project_name"] = name

        # Copy images into project's asset folder for portability
        assets_dir = self._projects_dir / f"{name}_assets"
        assets_dir.mkdir(exist_ok=True)

        # Handle logo
        if template.logo_path and os.path.isfile(template.logo_path):
            dest = assets_dir / os.path.basename(template.logo_path)
            if not dest.exists():
                shutil.copy2(template.logo_path, dest)
            data["logo_path"] = str(dest)

        # Handle label images
        for i, label in enumerate(template.labels):
            if label.image_path and os.path.isfile(label.image_path):
                dest = assets_dir / os.path.basename(label.image_path)
                if not dest.exists():
                    shutil.copy2(label.image_path, dest)
                data["labels"][i]["image_path"] = str(dest)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("Saved project: %s", name)

    def load_project(self, name: str) -> Optional[Template]:
        """Load a named project. Returns None if not found."""
        path = self._projects_dir / f"{name}{PROJECT_EXT}"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Template.from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.error("Failed to load project %s: %s", name, e)
            return None

    def delete_project(self, name: str) -> bool:
        """Delete a named project and its assets."""
        path = self._projects_dir / f"{name}{PROJECT_EXT}"
        assets_dir = self._projects_dir / f"{name}_assets"
        deleted = False
        if path.exists():
            path.unlink()
            deleted = True
        if assets_dir.exists():
            shutil.rmtree(assets_dir, ignore_errors=True)
        logger.info("Deleted project: %s", name)
        return deleted

    def rename_project(self, old_name: str, new_name: str) -> bool:
        """Rename a project."""
        old_path = self._projects_dir / f"{old_name}{PROJECT_EXT}"
        new_path = self._projects_dir / f"{new_name}{PROJECT_EXT}"
        if not old_path.exists() or new_path.exists():
            return False
        old_path.rename(new_path)
        # Rename assets dir too
        old_assets = self._projects_dir / f"{old_name}_assets"
        new_assets = self._projects_dir / f"{new_name}_assets"
        if old_assets.exists():
            old_assets.rename(new_assets)
        return True

    def export_project(self, name: str, export_path: str) -> None:
        """Export a project to an arbitrary file location."""
        src_path = self._projects_dir / f"{name}{PROJECT_EXT}"
        if src_path.exists():
            shutil.copy2(src_path, export_path)

    def import_project(self, file_path: str) -> Optional[str]:
        """Import a .blm or .json file as a project. Returns project name."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            name = data.get("project_name") or data.get("customer_name") or Path(file_path).stem
            template = Template.from_dict(data)
            self.save_project(name, template)
            return name
        except Exception as e:
            logger.error("Failed to import project from %s: %s", file_path, e)
            return None
