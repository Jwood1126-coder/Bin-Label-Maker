from dataclasses import dataclass
from typing import Optional


@dataclass
class LabelData:
    """Data for a single bin label."""
    brennan_part_number: str = ""
    customer_part_number: str = ""
    description: str = ""
    short_description: str = ""
    image_path: Optional[str] = None  # relative to template file location

    def is_empty(self) -> bool:
        return not self.brennan_part_number and not self.customer_part_number

    def get_display_description(self, mode: str = "full") -> str:
        """Return the description based on the selected mode.

        If mode is 'short' and short_description exists, use it.
        Otherwise fall back to the full description.
        """
        if mode == "short" and self.short_description:
            return self.short_description
        return self.description

    def to_dict(self) -> dict:
        return {
            "brennan_part_number": self.brennan_part_number,
            "customer_part_number": self.customer_part_number,
            "description": self.description,
            "short_description": self.short_description,
            "image_path": self.image_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LabelData":
        return cls(
            brennan_part_number=data.get("brennan_part_number", ""),
            customer_part_number=data.get("customer_part_number", ""),
            description=data.get("description", ""),
            short_description=data.get("short_description", ""),
            image_path=data.get("image_path"),
        )
