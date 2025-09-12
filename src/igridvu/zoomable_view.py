# -*- coding: utf-8 -*-
"""
A QGraphicsView that can zoom and pan, and sync with other views.
"""
import os
from typing import Optional, cast
from pathlib import Path
import ctypes

from PySide6.QtWidgets import (
    QFrame, QGraphicsView, QGraphicsScene,
    QLabel, QSizePolicy, QGraphicsPixmapItem, QMenu
)
from PySide6.QtGui import (
    QPixmap, QPainter, QImageReader, QColor, QResizeEvent, QImage, QAction, qRgb
)
from PySide6.QtCore import Qt, Signal as pyqtSignal, QRectF, QPointF, QSize, QPoint


class ZoomableView(QGraphicsView):
    """A QGraphicsView that can zoom and pan, and sync with other views."""
    # Signal emitted when the view changes (zoom or pan)
    viewRectChanged = pyqtSignal(QRectF)
    # Signal for hover events to update the status bar
    hovered = pyqtSignal(str)
    # Signal for mouse movement over the scene
    mouseMovedAtScenePos = pyqtSignal(QPointF)

    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
    MAX_IMAGE_DIMENSION = 10000  # Max 10k pixels for width or height

    def __init__(self, label_text: str, img_path: Optional[str] = None,
                 image: Optional[QImage] = None, error: Optional[str] = None):
        super().__init__()
        self.img_path = img_path or "in-memory"
        self.label_text = label_text
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._image: Optional[QImage] = image
        self._original_image: Optional[QImage] = None
        self._current_channel: Optional[str] = None
        self._is_handling_wheel = False
        self._image_aspect_ratio = 0.0

        self._setup_ui()

        if error:
            self._show_error_message(error)
        else:
            self._load_safe_pixmap()

        if self.has_image() and self._pixmap_item:
            pixmap_size = self._pixmap_item.pixmap().size()
            if pixmap_size.height() > 0:
                self._image_aspect_ratio = pixmap_size.width() / pixmap_size.height()

        if self._image_aspect_ratio > 0.0:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.horizontalScrollBar().valueChanged.connect(self._emit_view_rect_changed)
        self.verticalScrollBar().valueChanged.connect(self._emit_view_rect_changed)

    def _setup_ui(self):
        """Initialize UI components and view settings."""
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameStyle(QFrame.StyledPanel)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setMouseTracking(True)

        self._title_label = self._create_overlay_label(self.label_text)
        self._pixel_info_label = self._create_overlay_label()

    def _create_overlay_label(self, text: str = "") -> QLabel:
        """Creates a styled QLabel for overlaying on the view."""
        label = QLabel(text, self)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet(
            "background-color: rgba(0, 0, 0, 160);"
            "color: white;"
            "padding: 4px;"
            "border-radius: 4px;"
        )
        label.setAttribute(Qt.WA_TransparentForMouseEvents)
        return label

    def set_pixel_info(self, text: str):
        self._pixel_info_label.setText(text)

    def has_image(self) -> bool:
        return self._pixmap_item is not None

    def _show_error_message(self, error_msg: str):
        filename = Path(self.img_path).name
        text_item = self._scene.addText(f"{error_msg}\n{filename}")
        text_item.setDefaultTextColor(QColor(Qt.red))

    def _load_safe_pixmap(self):
        if self._image:  # Image was provided directly
            pixmap = QPixmap.fromImage(self._image)
            self._pixmap_item = self._scene.addPixmap(pixmap)
            return

        error_msg = self._get_loading_error()
        if error_msg:
            self._show_error_message(error_msg)
        elif self.img_path:
            self._image = QImage(self.img_path)
            if self._image.isNull():
                self._show_error_message("Cannot load\n(Corrupted?)")
            else:
                pixmap = QPixmap.fromImage(self._image)
                self._pixmap_item = self._scene.addPixmap(pixmap)

    def _get_loading_error(self) -> Optional[str]:
        if not self.img_path or self.img_path == "in-memory":
            return "Invalid path"

        img_path = Path(self.img_path)
        if not img_path.is_file():
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

        return None

    def contextMenuEvent(self, event):
        if not self.has_image() or not self._image:
            return

        menu = QMenu(self)
        if self._current_channel:
            restore_action = QAction("Restore Original", self)
            restore_action.triggered.connect(self.restore_original)
            menu.addAction(restore_action)
        else:
            self._add_channel_menu(menu)
        
        menu.exec(event.globalPos())

    def _add_channel_menu(self, menu: QMenu):
        if not self._image:
            return

        channel_menu = menu.addMenu("View Channel")
        
        channels = []
        if not self._image.isGrayscale():
            channels.extend(["Red", "Green", "Blue"])
        if self._image.hasAlphaChannel():
            channels.append("Alpha")

        if not channels:
            channel_menu.setEnabled(False)
            return

        for channel_name in channels:
            action = QAction(channel_name, self)
            action.triggered.connect(lambda checked=False, name=channel_name: self.view_channel(name))
            channel_menu.addAction(action)

    def view_channel(self, channel_name: str):
        if not self._image:
            return

        if not self._original_image:
            self._original_image = self._image.copy()

        channel_image = self.get_channel_image(channel_name)
        if channel_image:
            self._image = channel_image
            self._pixmap_item.setPixmap(QPixmap.fromImage(self._image))
            self._title_label.setText(f"{self.label_text} ({channel_name})")
            self._current_channel = channel_name

    def restore_original(self):
        if not self._original_image:
            return

        self._image = self._original_image
        self._pixmap_item.setPixmap(QPixmap.fromImage(self._image))
        self._title_label.setText(self.label_text)
        self._original_image = None
        self._current_channel = None

    def get_channel_image(self, channel_name: str) -> Optional[QImage]:
        if not self._image:
            return None

        if self._image.isGrayscale():
            return self._image.copy()

        channel_map = {"Red": 2, "Green": 1, "Blue": 0, "Alpha": 3}
        channel_index = channel_map.get(channel_name)

        if channel_index is None or (channel_index == 3 and not self._image.hasAlphaChannel()):
            return None

        width, height = self._image.width(), self._image.height()
        
        # Create an 8-bit indexed image for the channel
        channel_img = QImage(width, height, QImage.Format_Indexed8)
        color_table = [qRgb(i, i, i) for i in range(256)]
        channel_img.setColorTable(color_table)

        # Fast pixel manipulation using memory views
        source_format = self._image.format()
        
        # Ensure source image is in a format we can process
        if source_format not in (QImage.Format_RGB32, QImage.Format_ARGB32, QImage.Format_ARGB32_Premultiplied):
             self._image = self._image.convertToFormat(QImage.Format_ARGB32)

        bytes_per_pixel = self._image.depth() // 8
        
        # Get read-only access to the source image buffer
        source_bits = self._image.constBits()
        
        # Get write access to the destination image buffer
        dest_bits = channel_img.bits()
        
        # Create numpy-like array views from the memory buffers
        source_array = (ctypes.c_uint8 * len(source_bits)).from_buffer_copy(source_bits)
        dest_array = (ctypes.c_uint8 * len(dest_bits)).from_buffer(dest_bits)

        # Iterate over each row and process pixels
        for y in range(height):
            source_line_start = y * self._image.bytesPerLine()
            dest_line_start = y * channel_img.bytesPerLine()
            
            for x in range(width):
                source_idx = source_line_start + x * bytes_per_pixel + channel_index
                dest_idx = dest_line_start + x
                dest_array[dest_idx] = source_array[source_idx]

        return channel_img

    def showEvent(self, event):
        super().showEvent(event)
        if self.has_image():
            self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        margin = 5
        self._title_label.setFixedWidth(self.width() - (2 * margin))
        self._title_label.move(margin, margin)

        self._pixel_info_label.setFixedWidth(self.width() - (2 * margin))
        label_height = self._pixel_info_label.sizeHint().height()
        self._pixel_info_label.move(margin, self.height() - label_height - margin)

    def wheelEvent(self, event):
        if not self.has_image() or self._is_handling_wheel:
            return

        self._is_handling_wheel = True
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(zoom_factor, zoom_factor)
        self._is_handling_wheel = False
        self._emit_view_rect_changed()

    def _emit_view_rect_changed(self):
        if self.signalsBlocked() or self._is_handling_wheel:
            return
        self.viewRectChanged.emit(self.mapToScene(self.viewport().rect()).boundingRect())

    def setViewRect(self, rect: QRectF):
        if not self.has_image() or rect.isNull():
            return

        self.blockSignals(True)
        self.fitInView(rect, Qt.KeepAspectRatio)
        self.blockSignals(False)

    def sizeHint(self) -> QSize:
        if self._image_aspect_ratio > 0:
            base_width = 250
            return QSize(base_width, int(base_width / self._image_aspect_ratio))
        return super().sizeHint()

    def hasHeightForWidth(self) -> bool:
        return self._image_aspect_ratio > 0.0

    def heightForWidth(self, width: int) -> int:
        if self.hasHeightForWidth():
            return int(width / self._image_aspect_ratio)
        return super().heightForWidth(width)

    def get_color_at(self, scene_pos: QPointF) -> Optional[QColor]:
        if not self._image or not self.has_image() or not self._pixmap_item:
            return None

        item_pos = self._pixmap_item.mapFromScene(scene_pos)
        
        # Explicitly floor the coordinates to get the integer pixel position
        pixel_x = int(item_pos.x())
        pixel_y = int(item_pos.y())
        
        # Create a QPoint from the floored integers
        image_pixel_pos = QPoint(pixel_x, pixel_y)

        if not self._image.rect().contains(image_pixel_pos):
            return None

        return self._image.pixelColor(image_pixel_pos)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.mouseMovedAtScenePos.emit(self.mapToScene(event.position().toPoint()))

    def enterEvent(self, event):
        self.hovered.emit(self.img_path)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered.emit("")
        self.set_pixel_info("")
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragMode() == QGraphicsView.ScrollHandDrag:
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragMode() == QGraphicsView.ScrollHandDrag:
            self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)
