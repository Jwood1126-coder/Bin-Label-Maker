import json
import os
from pathlib import Path
from typing import Optional

from src.models.template import Template


class TemplateIO:
    """Handles saving and loading Template objects as JSON files.

    Image paths are stored relative to the template file location
    for portability between machines.
    """

    def save(self, template: Template, file_path: str) -> None:
        template_dir = os.path.dirname(os.path.abspath(file_path))
        data = template.to_dict()
        data["logo_path"] = self._to_relative(template.logo_path, template_dir)
        for i, label_dict in enumerate(data["labels"]):
            label_dict["image_path"] = self._to_relative(
                template.labels[i].image_path, template_dir
            )
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, file_path: str) -> Template:
        template_dir = os.path.dirname(os.path.abspath(file_path))
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["logo_path"] = self._to_absolute(data.get("logo_path"), template_dir)
        for label_dict in data.get("labels", []):
            label_dict["image_path"] = self._to_absolute(
                label_dict.get("image_path"), template_dir
            )
        return Template.from_dict(data)

    def _to_relative(self, path: Optional[str], base_dir: str) -> Optional[str]:
        if not path:
            return None
        try:
            return os.path.relpath(path, base_dir)
        except ValueError:
            return path

    def _to_absolute(self, path: Optional[str], base_dir: str) -> Optional[str]:
        if not path:
            return None
        if os.path.isabs(path):
            return path
        return os.path.normpath(os.path.join(base_dir, path))
