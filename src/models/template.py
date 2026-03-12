from dataclasses import dataclass, field
from typing import Optional

from src.models.label_data import LabelData
from src.models.avery_templates import DEFAULT_TEMPLATE_ID


@dataclass
class Template:
    """A complete label sheet template for a customer."""
    customer_name: str = ""
    avery_template_id: str = DEFAULT_TEMPLATE_ID
    logo_path: Optional[str] = None       # relative to template file location
    qr_base_url: str = "https://brennaninc.com/parts/"
    labels: list[LabelData] = field(default_factory=list)
    start_offset: int = 0  # skip this many label positions (partial sheet support)

    def to_dict(self) -> dict:
        return {
            "customer_name": self.customer_name,
            "avery_template_id": self.avery_template_id,
            "logo_path": self.logo_path,
            "qr_base_url": self.qr_base_url,
            "start_offset": self.start_offset,
            "labels": [label.to_dict() for label in self.labels],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Template":
        labels = [LabelData.from_dict(ld) for ld in data.get("labels", [])]
        return cls(
            customer_name=data.get("customer_name", ""),
            avery_template_id=data.get("avery_template_id", DEFAULT_TEMPLATE_ID),
            logo_path=data.get("logo_path"),
            qr_base_url=data.get("qr_base_url", "https://brennaninc.com/parts/"),
            start_offset=data.get("start_offset", 0),
            labels=labels,
        )
