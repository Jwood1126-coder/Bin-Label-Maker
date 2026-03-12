"""Composition root — single place where all dependencies are wired."""
from src.services.label_layout import LabelLayoutService
from src.services.qr_generator import QRGenerator
from src.services.pdf_renderer import PDFRenderer
from src.services.preview_renderer import PreviewRenderer
from src.services.template_io import TemplateIO
from src.services.project_manager import ProjectManager
from src.services.catsy_mock import MockCatsyService
from src.presenters.label_presenter import LabelPresenter
from src.presenters.main_presenter import MainPresenter
from src.views.main_window import MainWindow


def create_application() -> MainWindow:
    """Wire all dependencies and return the main window."""
    # Services
    qr_generator = QRGenerator(base_url="https://brennaninc.com/parts/")
    layout_service = LabelLayoutService()
    pdf_renderer = PDFRenderer(layout_service, qr_generator)
    preview_renderer = PreviewRenderer(layout_service, qr_generator)
    template_io = TemplateIO()
    project_manager = ProjectManager()
    data_source = MockCatsyService()

    # Presenters
    label_presenter = LabelPresenter(pdf_renderer, template_io, data_source)
    main_presenter = MainPresenter(label_presenter)

    # Main window (registers itself as the view)
    window = MainWindow(main_presenter, label_presenter, preview_renderer, project_manager)

    return window
