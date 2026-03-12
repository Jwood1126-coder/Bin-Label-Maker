"""Composition root — single place where all dependencies are wired."""
import json
import logging
import os
from pathlib import Path

from src.services.label_layout import LabelLayoutService
from src.services.qr_generator import QRGenerator
from src.services.pdf_renderer import PDFRenderer
from src.services.preview_renderer import PreviewRenderer
from src.services.template_io import TemplateIO
from src.services.project_manager import ProjectManager, get_app_data_dir
from src.services.catsy_mock import MockCatsyService
from src.services.catsy_live import LiveCatsyService
from src.presenters.label_presenter import LabelPresenter
from src.presenters.main_presenter import MainPresenter
from src.views.main_window import MainWindow
from src.views.theme import logo_label_path

logger = logging.getLogger(__name__)

# Catsy API configuration
CATSY_API_URL = "https://api.catsy.com/v4"


def _load_catsy_token() -> str:
    """Load Catsy bearer token from environment or config file.

    Lookup order:
    1. CATSY_BEARER_TOKEN environment variable
    2. config.json in app data directory ({"catsy_bearer_token": "..."})
    3. Returns empty string if neither found
    """
    # 1. Environment variable
    token = os.environ.get("CATSY_BEARER_TOKEN", "").strip()
    if token:
        return token

    # 2. Config file in app data directory
    config_path = get_app_data_dir() / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            token = config.get("catsy_bearer_token", "").strip()
            if token:
                return token
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read config file: %s", e)

    return ""


def _create_data_source():
    """Create the best available data source — live Catsy API with mock fallback."""
    token = _load_catsy_token()
    if not token:
        logger.info("No Catsy API token configured, using mock data. "
                     "Set CATSY_BEARER_TOKEN env var or add to %s/config.json",
                     get_app_data_dir())
        return MockCatsyService()

    try:
        live = LiveCatsyService(CATSY_API_URL, token)
        ok, msg = live.test_connection()
        if ok:
            logger.info("Catsy API connected: %s", msg)
            return live
        else:
            logger.warning("Catsy API unavailable (%s), using mock data", msg)
    except Exception as e:
        logger.warning("Catsy API connection failed (%s), using mock data", e)
    return MockCatsyService()


def create_application() -> MainWindow:
    """Wire all dependencies and return the main window."""
    # Services
    qr_generator = QRGenerator(base_url="https://brennaninc.com/")
    layout_service = LabelLayoutService()
    pdf_renderer = PDFRenderer(layout_service, qr_generator)
    preview_renderer = PreviewRenderer(layout_service, qr_generator)
    template_io = TemplateIO()
    project_manager = ProjectManager()
    data_source = _create_data_source()

    # Default logo for new templates
    default_logo = logo_label_path()
    if not os.path.exists(default_logo):
        default_logo = None

    # Presenters
    label_presenter = LabelPresenter(pdf_renderer, template_io, data_source, default_logo)
    main_presenter = MainPresenter(label_presenter)

    # Main window (registers itself as the view)
    window = MainWindow(main_presenter, label_presenter, preview_renderer, project_manager)

    return window
