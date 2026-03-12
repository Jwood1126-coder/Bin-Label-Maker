from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LabelData:
    """Data for a single bin label."""
    brennan_part_number: str = ""
    customer_part_number: str = ""
    description: str = ""
    short_description: str = ""
    image_path: Optional[str] = None  # relative to template file location
    xrefs: dict = field(default_factory=dict)  # manufacturer_key -> part_number

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

    def resolve_customer_pn(self, xref_key: str) -> str:
        """Resolve customer part number from stored xrefs.

        If xref_key matches a stored xref, returns that value.
        Otherwise returns the manually-set customer_part_number.
        """
        if xref_key and self.xrefs:
            return self.xrefs.get(xref_key, "")
        return self.customer_part_number

    def available_xref_keys(self) -> set:
        """Return the set of xref keys that have data for this label."""
        return {k for k, v in self.xrefs.items() if v}

    def to_dict(self) -> dict:
        d = {
            "brennan_part_number": self.brennan_part_number,
            "customer_part_number": self.customer_part_number,
            "description": self.description,
            "short_description": self.short_description,
            "image_path": self.image_path,
        }
        if self.xrefs:
            d["xrefs"] = dict(self.xrefs)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "LabelData":
        return cls(
            brennan_part_number=data.get("brennan_part_number", ""),
            customer_part_number=data.get("customer_part_number", ""),
            description=data.get("description", ""),
            short_description=data.get("short_description", ""),
            image_path=data.get("image_path"),
            xrefs=data.get("xrefs", {}),
        )
