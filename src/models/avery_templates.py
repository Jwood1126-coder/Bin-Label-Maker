from dataclasses import dataclass


@dataclass(frozen=True)
class AveryGeometry:
    """Defines the physical layout of an Avery label sheet."""
    name: str
    label_width: float    # inches
    label_height: float   # inches
    columns: int
    rows: int
    top_margin: float     # inches
    left_margin: float    # inches
    h_gap: float          # horizontal gutter between labels (inches)
    v_gap: float          # vertical gutter between labels (inches)
    page_width: float = 8.5   # inches (US Letter)
    page_height: float = 11.0  # inches (US Letter)

    @property
    def labels_per_page(self) -> int:
        return self.columns * self.rows

    @property
    def label_width_pt(self) -> float:
        return self.label_width * 72.0

    @property
    def label_height_pt(self) -> float:
        return self.label_height * 72.0

    @property
    def page_width_pt(self) -> float:
        return self.page_width * 72.0

    @property
    def page_height_pt(self) -> float:
        return self.page_height * 72.0

    @property
    def top_margin_pt(self) -> float:
        return self.top_margin * 72.0

    @property
    def left_margin_pt(self) -> float:
        return self.left_margin * 72.0

    @property
    def h_gap_pt(self) -> float:
        return self.h_gap * 72.0

    @property
    def v_gap_pt(self) -> float:
        return self.v_gap * 72.0


AVERY_TEMPLATES: dict[str, AveryGeometry] = {
    "5160": AveryGeometry(
        name="Avery 5160",
        label_width=2.625, label_height=1.0,
        columns=3, rows=10,
        top_margin=0.5, left_margin=0.1875,
        h_gap=0.125, v_gap=0.0,
    ),
    "5163": AveryGeometry(
        name="Avery 5163",
        label_width=4.0, label_height=2.0,
        columns=2, rows=5,
        top_margin=0.5, left_margin=0.156,
        h_gap=0.188, v_gap=0.0,
    ),
    "5164": AveryGeometry(
        name="Avery 5164",
        label_width=4.0, label_height=3.333,
        columns=2, rows=3,
        top_margin=0.5, left_margin=0.156,
        h_gap=0.188, v_gap=0.167,
    ),
}

DEFAULT_TEMPLATE_ID = "5160"
