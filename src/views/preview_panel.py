"""Preview panel showing the rendered label sheet."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
    QHBoxLayout, QPushButton, QLabel,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap


class PreviewPanel(QWidget):
    """Displays a rendered preview of the label sheet with zoom controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Zoom controls
        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(QLabel("Preview"))
        ctrl_row.addStretch()

        self._page_label = QLabel("Page 1")
        ctrl_row.addWidget(self._page_label)

        self._prev_btn = QPushButton("<")
        self._prev_btn.setFixedWidth(30)
        self._prev_btn.clicked.connect(self._prev_page)
        ctrl_row.addWidget(self._prev_btn)

        self._next_btn = QPushButton(">")
        self._next_btn.setFixedWidth(30)
        self._next_btn.clicked.connect(self._next_page)
        ctrl_row.addWidget(self._next_btn)

        self._fit_btn = QPushButton("Fit")
        self._fit_btn.clicked.connect(self._fit_to_view)
        ctrl_row.addWidget(self._fit_btn)

        layout.addLayout(ctrl_row)

        # Graphics view
        self._scene = QGraphicsScene()
        self._view = QGraphicsView(self._scene)
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setRenderHint(self._view.renderHints())
        layout.addWidget(self._view)

        self._current_page = 0
        self._total_pages = 1
        self._render_callback = None

        # Debounce timer for preview updates
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(300)
        self._debounce_timer.timeout.connect(self._do_render)

    def set_render_callback(self, callback) -> None:
        """Set the function to call to get a QPixmap for a given page.

        callback(page: int) -> QPixmap
        """
        self._render_callback = callback

    def set_total_pages(self, total: int) -> None:
        self._total_pages = max(1, total)
        if self._current_page >= self._total_pages:
            self._current_page = self._total_pages - 1
        self._update_page_label()

    def request_update(self) -> None:
        """Request a debounced preview re-render."""
        self._debounce_timer.start()

    def _do_render(self) -> None:
        if self._render_callback:
            pixmap = self._render_callback(self._current_page)
            self._scene.clear()
            self._scene.addPixmap(pixmap)
            self._scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
            self._fit_to_view()

    def _fit_to_view(self) -> None:
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
