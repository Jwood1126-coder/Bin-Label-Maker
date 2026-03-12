from dataclasses import dataclass, field
from typing import Optional

from src.models.label_data import LabelData
from src.models.avery_templates import DEFAULT_TEMPLATE_ID


# Cross-reference manufacturer keys available in Catsy
# Maps display name -> Catsy attribute key
XREF_MANUFACTURERS = {
    "(none)": "",
    "Parker": "parker_part_number",
    "Parker TFD": "parker_tfd_part_number",
    "Swagelok": "swagelok_part_number",
    "Aeroquip": "aeroquip_part_number",
    "Adaptall": "adaptall_part_number",
    "Danfoss": "danfoss_part_number",
    "Cast": "cast_part_number",
    "EU": "eu_part_number",
    "Voss": "voss_part_number",
    "Stauff": "stauff_part_number",
    "SSP": "ssp_part_number",
    "SMC": "smc_part_number",
    "Gates": "gates_part_number",
    "Weatherhead": "weatherhead_part_number",
    "Fittings Unlimited": "fittings_unlimited_part_number",
    "Tompkins": "tompkins_part_number",
    "Pressure Connections": "pressure_connections_part_number",
    "Airway": "airway_part_number",
}


@dataclass
class Template:
    """A complete label sheet template for a customer."""
    customer_name: str = ""
    avery_template_id: str = DEFAULT_TEMPLATE_ID
    logo_path: Optional[str] = None
    qr_base_url: str = "https://brennaninc.com/parts/"
    xref_key: str = ""  # Catsy attribute key for customer part number mapping
    description_limit: int = 0  # max chars for description (0 = unlimited)
    labels: list[LabelData] = field(default_factory=list)
    start_offset: int = 0

    def to_dict(self) -> dict:
        return {
            "customer_name": self.customer_name,
            "avery_template_id": self.avery_template_id,
            "logo_path": self.logo_path,
            "qr_base_url": self.qr_base_url,
            "xref_key": self.xref_key,
            "description_limit": self.description_limit,
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
            xref_key=data.get("xref_key", ""),
            description_limit=data.get("description_limit", 0),
            start_offset=data.get("start_offset", 0),
            labels=labels,
        )
