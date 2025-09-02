# -*- coding: utf-8 -*-
"""
A QGraphicsView that can zoom and pan, and sync with other views.
"""
import os
from typing import Optional, cast
from pathlib import Path

from PySide6.QtWidgets import (QFrame, QGraphicsView, QGraphicsScene,
                             QLabel, QSizePolicy, QGraphicsPixmapItem)
from PySide6.QtGui import (QPixmap, QPainter, QImageReader, QColor, QResizeEvent, QImage)
from PySide6.QtCore import Qt, Signal as pyqtSignal, QRectF, QPointF, QSize


class ZoomableView(QGraphicsView):
    """A QGraphicsView that can zoom and pan, and sync with other views."""
    # Signal emitted when the view changes (zoom or pan)
    # It carries the new visible rectangle in scene coordinates.
    viewRectChanged = pyqtSignal(QRectF)
    # Signal for hover events to update the status bar
    hovered = pyqtSignal(str)
    # Signal for mouse movement over the scene
    mouseMovedAtScenePos = pyqtSignal(QPointF)

    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
    MAX_IMAGE_DIMENSION = 10000  # Max 10k pixels for width or height

    def __init__(self, img_path: str, label_text: str, error: Optional[str] = None):
        super().__init__()
        self.img_path = img_path
        self.label_text = label_text
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._image: Optional[QImage] = None  # Store QImage for fast pixel access
        self._is_handling_wheel = False
        self._image_aspect_ratio = 0.0

        if error:
            self._show_error_message(error)
        else:
            self._load_safe_pixmap()

        if self.has_image():
            pixmap_size = self._pixmap_item.pixmap().size()
            if pixmap_size.height() > 0 and self._pixmap_item:
                self._image_aspect_ratio = pixmap_size.width() / pixmap_size.height()

        if self._image_aspect_ratio > 0.0:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameStyle(QFrame.StyledPanel)
        # Use ScrollHandDrag for intuitive panning with the left mouse button
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setMouseTracking(True)

        # Create and style the overlay title label
        self._title_label = QLabel(label_text, self)
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setWordWrap(True)
        # Style it to be visible over any image content
        self._title_label.setStyleSheet(
            "background-color: rgba(0, 0, 0, 160);"
            "color: white;"
            "padding: 4px;"
            "border-radius: 4px;"
        )
        # Let mouse events pass through the label to the view underneath
        self._title_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Connect scrollbar signals to detect panning
        self.horizontalScrollBar().valueChanged.connect(self._emit_view_rect_changed)
        self.verticalScrollBar().valueChanged.connect(self._emit_view_rect_changed)

    def has_image(self) -> bool:
        """Returns True if a valid pixmap was loaded."""
        return self._pixmap_item is not None

    def _show_error_message(self, error_msg: str):
        """Displays a given error message in the scene."""
        filename = Path(self.img_path).name
        text_item = self._scene.addText(f"{error_msg}\n{filename}")
        text_item.setDefaultTextColor(QColor(Qt.red))

    def _load_safe_pixmap(self):
        """Safely loads the pixmap, checking for potential resource issues."""
        error_msg = self._get_loading_error()
        if error_msg:
            self._show_error_message(error_msg)
        else:
            # All checks passed. Load QImage first to be the source of truth
            # for pixel data, which is more reliable than pixmap.toImage().
            self._image = QImage(self.img_path)
            # Create QPixmap from the QImage for display.
            pixmap = QPixmap.fromImage(self._image)
            self._pixmap_item = self._scene.addPixmap(pixmap)

    def _get_loading_error(self) -> Optional[str]:
        """
        Runs all pre-load checks and returns an error message string if any fail.
        Returns None if the image is safe to load.
        """
        img_path = Path(self.img_path)
        if not img_path.exists():
            return "Not found"
        if not os.access(str(img_path), os.R_OK):
            return "Permission\ndenied"

        try:
            file_size = img_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE_BYTES:
                size_mb = file_size / (1024 * 1024)
                return f"File too large\n({size_mb:.1f} MB)"
        except OSError as e:
            return f"Cannot access\n{e.strerror}"

        reader = QImageReader(str(img_path))
        if not reader.canRead():
            return "Unrecognized\nformat"

        img_dim = reader.size()
        if img_dim.width() > self.MAX_IMAGE_DIMENSION or img_dim.height() > self.MAX_IMAGE_DIMENSION:
            return f"Dimensions too large\n({img_dim.width()}x{img_dim.height()})"

        # Final check by attempting to load into a QImage.
        image = QImage(str(img_path))
        if image.isNull():
            return "Cannot load\n(Corrupted?)"

        return None

    def showEvent(self, event):
        """Fit the image in the view when the widget is first shown."""
        super().showEvent(event)
        if self.has_image():
            self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)

    def resizeEvent(self, event: QResizeEvent):
        """Handle widget resize to keep the title label positioned correctly."""
        super().resizeEvent(event)
        # Give the label a small margin from the view's edges
        margin = 5
        # Set the label's width to the view's width minus margins
        self._title_label.setFixedWidth(self.width() - (2 * margin))
        # Move the label to the top, with a margin
        self._title_label.move(margin, margin)

    def wheelEvent(self, event):
        """Handle zooming with the mouse wheel."""
        # Use a flag to prevent re-entrant calls and to control signal emission.
        if not self.has_image() or self._is_handling_wheel:
            return

        self._is_handling_wheel = True

        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        # The scale() operation triggers internal updates, including for the
        # scrollbars. We let this happen naturally without blocking signals.
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)

        # The scale() operation is now complete. We can release the flag.
        self._is_handling_wheel = False

        # The scrollbar's valueChanged signal might have fired during scale(),
        # but our flag prevented _emit_view_rect_changed from running.
        # Now, we emit the signal manually, ensuring it happens exactly once
        # after the zoom operation is fully complete.
        self._emit_view_rect_changed()

    def _emit_view_rect_changed(self):
        """Emits the signal with the current view rect."""
        # The flag prevents emission during a wheel event; the handler emits once at the end.
        if self.signalsBlocked() or self._is_handling_wheel:
            return
        # mapToScene gives the rectangle of the viewport in scene coordinates
        self.viewRectChanged.emit(self.mapToScene(self.viewport().rect()).boundingRect())

    def setViewRect(self, rect: QRectF):
        """Sets the view to a specific rectangle, blocking signals to prevent loops."""
        if not self.has_image() or rect.isNull():
            return

        self.blockSignals(True)
        self.fitInView(rect, Qt.KeepAspectRatio)
        self.blockSignals(False)

    def sizeHint(self) -> QSize:
        """Provides a size hint that respects the image's aspect ratio."""
        if self._image_aspect_ratio > 0:
            # Provide a reasonable default size hint.
            base_width = 250
            return QSize(base_width, int(base_width / self._image_aspect_ratio))
        return super().sizeHint()

    def hasHeightForWidth(self) -> bool:
        """Indicates that the widget's preferred height depends on its width."""
        return self._image_aspect_ratio > 0.0

    def heightForWidth(self, width: int) -> int:
        """Returns the preferred height for a given width to maintain aspect ratio."""
        if self.hasHeightForWidth():
            return int(width / self._image_aspect_ratio)
        return super().heightForWidth(width)

    def get_color_at(self, scene_pos: QPointF) -> Optional[QColor]:
        """Gets the QColor of the pixel at a given scene coordinate."""
        if not self._image or not self.has_image():
            return None

        # Convert scene position to the pixmap item's local coordinates (image pixels)
        item_pos = cast(QGraphicsPixmapItem, self._pixmap_item).mapFromScene(scene_pos)

        # Check if the coordinate is within the image's bounds
        if not self._image.rect().contains(item_pos.toPoint()):
            return None

        return self._image.pixelColor(item_pos.toPoint())

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.mouseMovedAtScenePos.emit(self.mapToScene(event.position().toPoint()))

    def enterEvent(self, event):
        """Emits the full image path when the mouse enters the view."""
        self.hovered.emit(self.img_path)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Emits an empty string when the mouse leaves the view."""
        self.hovered.emit("")
        super().leaveEvent(event)