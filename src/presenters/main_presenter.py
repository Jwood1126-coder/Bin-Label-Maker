"""Top-level application presenter for app-wide coordination."""
import logging

from src.presenters.label_presenter import LabelPresenter

logger = logging.getLogger(__name__)


class MainPresenter:
    """Coordinates app-level actions (menu items, window lifecycle)."""

    def __init__(self, label_presenter: LabelPresenter):
        self.label_presenter = label_presenter

    def on_new(self) -> None:
        self.label_presenter.new_template()

    def on_open(self, file_path: str) -> None:
        self.label_presenter.load_template(file_path)

    def on_save(self, file_path: str) -> None:
        self.label_presenter.save_template(file_path)

    def on_export_pdf(self, output_path: str) -> None:
        self.label_presenter.export_pdf(output_path)
