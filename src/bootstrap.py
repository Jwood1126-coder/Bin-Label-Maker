"""Composition root — single place where all dependencies are wired."""
import logging

from src.services.label_layout import LabelLayoutService
from src.services.qr_generator import QRGenerator
from src.services.pdf_renderer import PDFRenderer
from src.services.preview_renderer import PreviewRenderer
from src.services.template_io import TemplateIO
from src.services.project_manager import ProjectManager
from src.services.catsy_mock import MockCatsyService
from src.services.catsy_live import LiveCatsyService
from src.presenters.label_presenter import LabelPresenter
from src.presenters.main_presenter import MainPresenter
from src.views.main_window import MainWindow

logger = logging.getLogger(__name__)

# Catsy API configuration
CATSY_API_URL = "https://api.catsy.com/v4"
CATSY_BEARER_TOKEN = "081ae682b02945bbb868715f50b705cd"


def _create_data_source():
    """Create the best available data source — live Catsy API with mock fallback."""
    try:
        live = LiveCatsyService(CATSY_API_URL, CATSY_BEARER_TOKEN)
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
    qr_generator = QRGenerator(base_url="https://brennaninc.com/parts/")
    layout_service = LabelLayoutService()
    pdf_renderer = PDFRenderer(layout_service, qr_generator)
    preview_renderer = PreviewRenderer(layout_service, qr_generator)
    template_io = TemplateIO()
    project_manager = ProjectManager()
    data_source = _create_data_source()

    # Presenters
    label_presenter = LabelPresenter(pdf_renderer, template_io, data_source)
    main_presenter = MainPresenter(label_presenter)

    # Main window (registers itself as the view)
    window = MainWindow(main_presenter, label_presenter, preview_renderer, project_manager)

    return window
