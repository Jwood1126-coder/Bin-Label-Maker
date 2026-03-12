"""Bin Label Maker - Entry Point.

Brennan Industries bin label generator for Avery label sheets.
"""
import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.bootstrap import create_application


def configure_logging() -> None:
    log_dir = Path.home() / ".bin_label_maker" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "app.log"),
            logging.StreamHandler(),
        ],
    )


def main() -> int:
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("Bin Label Maker")
    app.setOrganizationName("Brennan Industries")

    window = create_application()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
