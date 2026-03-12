"""Preview panel showing the rendered label sheet."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
    QHBoxLayout, QPushButton, QLabel, QFrame,
)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QWheelEvent
from src.views.theme import BRENNAN_WHITE


# Preview renders at 2x scale
_PREVIEW_SCALE = 2.0


class ZoomableGraphicsView(QGraphicsView):
    """QGraphicsView with mouse wheel zoom support."""

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
        else:
            self.scale(1 / factor, 1 / factor)


class PreviewPanel(QWidget):
    """Displays a rendered preview of the label sheet with zoom controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Control bar
        ctrl_bar = QFrame()
        ctrl_bar.setObjectName("previewCtrlBar")
        ctrl_bar.setStyleSheet(f"""
            QFrame#previewCtrlBar {{
                background-color: {BRENNAN_WHITE};
                border: 1px solid #D0D0D0;
                border-radius: 4px 4px 0 0;
                padding: 2px;
            }}
        """)
        ctrl_row = QHBoxLayout(ctrl_bar)
        ctrl_row.setContentsMargins(10, 4, 10, 4)

        preview_title = QLabel("Preview")
        preview_title.setProperty("cssClass", "section-header")
        ctrl_row.addWidget(preview_title)
        ctrl_row.addStretch()

        self._page_label = QLabel("Page 1")
        self._page_label.setStyleSheet("font-weight: 500; font-size: 12px;")
        ctrl_row.addWidget(self._page_label)

        self._prev_btn = QPushButton("<")
        self._prev_btn.setFixedSize(28, 28)
        self._prev_btn.clicked.connect(self._prev_page)
        ctrl_row.addWidget(self._prev_btn)

        self._next_btn = QPushButton(">")
        self._next_btn.setFixedSize(28, 28)
        self._next_btn.clicked.connect(self._next_page)
        ctrl_row.addWidget(self._next_btn)

        self._fit_btn = QPushButton("Fit Page")
        self._fit_btn.setFixedWidth(60)
        self._fit_btn.setProperty("cssClass", "secondary")
        self._fit_btn.clicked.connect(self._fit_to_view)
        ctrl_row.addWidget(self._fit_btn)

        layout.addWidget(ctrl_bar)

        # Graphics view with scroll-wheel zoom
        self._scene = QGraphicsScene()
        self._view = ZoomableGraphicsView(self._scene)
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setRenderHint(self._view.renderHints())
        self._view.setStyleSheet("border-radius: 0 0 4px 4px;")
        self._view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        layout.addWidget(self._view)

        self._current_page = 0
        self._total_pages = 1
        self._render_callback = None
        # Stores label grid positions (from the layout engine) for zoom-to-label
        self._label_positions = None  # set externally
        self._per_page = 0
        self._start_offset = 0

        # Debounce timer for preview updates
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(300)
        self._debounce_timer.timeout.connect(self._do_render)

    def set_render_callback(self, callback) -> None:
        self._render_callback = callback

    def set_label_grid(self, positions, per_page: int, start_offset: int) -> None:
        """Set the label grid positions for zoom-to-label support.

        positions: list of Rect from LabelLayoutService.compute_label_positions()
        """
        self._label_positions = positions
        self._per_page = per_page
        self._start_offset = start_offset

    def set_total_pages(self, total: int) -> None:
        self._total_pages = max(1, total)
        if self._current_page >= self._total_pages:
            self._current_page = self._total_pages - 1
        self._update_page_label()

    def request_update(self) -> None:
        self._debounce_timer.start()

    def zoom_to_label(self, label_index: int) -> None:
        """Zoom the preview to show a specific label enlarged."""
        if not self._label_positions or self._per_page <= 0:
            return

        # Figure out which page and slot this label occupies
        slot_index = label_index + self._start_offset
        page = slot_index // self._per_page
        page_slot = slot_index % self._per_page

        # Switch page if needed
        if page != self._current_page:
            self._current_page = page
            self._update_page_label()
            self._do_render()

        if page_slot >= len(self._label_positions):
            return

        pos = self._label_positions[page_slot]
        # Convert from points to preview pixels (preview renders at 2x scale)
        rect = QRectF(
            pos.x * _PREVIEW_SCALE,
            # Preview image is top-down; convert from ReportLab bottom-left origin
            # The preview renderer already handles this, so use the rect as-is
            pos.y * _PREVIEW_SCALE,
            pos.width * _PREVIEW_SCALE,
            pos.height * _PREVIEW_SCALE,
        )
        # Add some padding around the label
        pad = rect.width() * 0.15
        rect.adjust(-pad, -pad, pad, pad)

        self._view.resetTransform()
        self._view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def _do_render(self) -> None:
        if self._render_callback:
            pixmap = self._render_callback(self._current_page)
            self._scene.clear()
            self._scene.addPixmap(pixmap)
            self._scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
            self._fit_to_view()

    def _fit_to_view(self) -> None:
        self._view.resetTransform()
        self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _prev_page(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._update_page_label()
            self._do_render()

    def _next_page(self) -> None:
        if self._current_page < self._total_pages - 1:
            self._current_page += 1
            self._update_page_label()
            self._do_render()

    def _update_page_label(self) -> None:
        self._page_label.setText(f"Page {self._current_page + 1} of {self._total_pages}")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._scene.items():
            self._fit_to_view()
