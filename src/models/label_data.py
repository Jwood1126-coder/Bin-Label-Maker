from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LabelData:
    """Data for a single bin label."""
    brennan_part_number: str = ""
    customer_part_number: str = ""
    description: str = ""
    image_path: Optional[str] = None  # relative to template file location

    def is_empty(self) -> bool:
        return not self.brennan_part_number and not self.customer_part_number

    def to_dict(self) -> dict:
        return {
            "brennan_part_number": self.brennan_part_number,
            "customer_part_number": self.customer_part_number,
            "description": self.description,
            "image_path": self.image_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LabelData":
        return cls(
            brennan_part_number=data.get("brennan_part_number", ""),
            customer_part_number=data.get("customer_part_number", ""),
            description=data.get("description", ""),
            image_path=data.get("image_path"),
        )
