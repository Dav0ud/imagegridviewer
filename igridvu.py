# -*- coding: utf-8 -*-
"""
Image Grid Viewer
This is an image grid viewer 

First argument must be the prefix path that is identical for the whole set
of images.

The second argument is the text file which contains a list of suffixes separated by end lines.
If no second argument is provided, it looks into "./igridvu_suffix.txt" per default.

@author Davoud Shahlaei
"""

import sys
import os
import argparse
from typing import List, Optional, cast
from pathlib import Path
from itertools import islice

from PySide6.QtWidgets import (QWidget, QFrame, QGridLayout, QApplication,
                             QMainWindow, QStatusBar, QGraphicsView, QGraphicsScene,
                             QLabel, QVBoxLayout, QSizePolicy, QGraphicsPixmapItem)
from PySide6.QtGui import (QPixmap, QPainter, QImageReader, QColor, QFont, QResizeEvent, QImage)
from PySide6.QtCore import Qt, Signal as pyqtSignal, QRectF, QPointF, QSize

APP_NAME = "Image Grid Viewer"
DEFAULT_SUFFIX_FILE = "igridvu_suffix.txt"

class ImageGrid(QMainWindow):
    """A widget that displays a grid of images."""

    def __init__(self, pre_path: str, list_of_suffix: List[str],
                 columns: int = 4):
        super().__init__()
        self.pre_path = pre_path
        self.list_of_suffix = list_of_suffix
        self.columns = columns
        self.initUI()

    def initUI(self):
        """Initializes the UI and lays out the image labels in a grid."""
        # A QMainWindow requires a central widget to hold the main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create a main vertical layout to hold the grid and a stretch item.
        # This ensures the grid is always pushed to the top of the window.
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create a container widget for the grid itself.
        grid_container = QWidget()
        self.views = []
        layout = QGridLayout(grid_container)
        # Minimize the space between grid cells and around the layout's edges
        # to create a tightly packed grid.
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        prefix_is_dir = os.path.isdir(self.pre_path)

        for i, suffix in enumerate(self.list_of_suffix):
            row = i // self.columns
            col = i % self.columns
            
            clean_suffix = suffix.rstrip()
            # If the prefix is a directory, join paths. Otherwise, concatenate.
            full_path = os.path.join(self.pre_path, clean_suffix) if prefix_is_dir else self.pre_path + clean_suffix

            label_text = Path(clean_suffix).stem

            # The ZoomableView now manages its own title label as an overlay
            view = ZoomableView(full_path, label_text)
            view.hovered.connect(self.update_status_bar)
            view.mouseMovedAtScenePos.connect(self._update_pixel_info)
            view.viewRectChanged.connect(self.sync_views)

            # Add the view directly to the grid. By specifying Qt.AlignTop,
            # we ensure that if a row's height is determined by a taller
            # image, the shorter images in that row will align to the top of
            # their cells instead of stretching, creating a masonry-like layout.
            layout.addWidget(view, row, col, Qt.AlignTop)
            self.views.append(view)

        # Add the grid container to the main layout.
        main_layout.addWidget(grid_container)
        # Add a stretchable space at the bottom, pushing the grid upwards.
        main_layout.addStretch(1)

        # Set up the status bar with a default message
        self.status_message = "Ready. Hover for path. Move over image for pixel values."
        self.statusBar().showMessage(self.status_message)

        self.setWindowTitle(f"{APP_NAME}: {self.pre_path}...")
        self.resize(800, 600)
        self._center_on_screen()
        self.show()

    def _center_on_screen(self):
        """Centers the window on the primary screen."""
        frame_geometry = self.frameGeometry()
        center_point = QApplication.primaryScreen().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def sync_views(self, rect: QRectF):
        """Slot to synchronize all views to the given rectangle."""
        sender_view = self.sender()
        for view in self.views:
            if view is not sender_view:
                view.setViewRect(rect)

    def update_status_bar(self, text: str):
        """Slot to update the status bar message. Restores default when text is empty."""
        # This is now primarily for when the mouse enters/leaves the view area
        if text:
            self.statusBar().showMessage(f"Path: {text}")
        else:
            self.statusBar().showMessage(self.status_message)

    def _update_pixel_info(self, scene_pos: QPointF):
        """Updates status bar with pixel info from all views at a given scene coordinate."""
        sender_view = self.sender()
        if not isinstance(sender_view, ZoomableView) or not sender_view.has_image():
            return

        # If cursor is not over a valid pixel in the source view, do nothing.
        # The leaveEvent will handle clearing the status bar.
        if sender_view.get_color_at(scene_pos) is None:
            self.update_status_bar(sender_view.img_path)
            return

        x, y = int(scene_pos.x()), int(scene_pos.y())

        def format_pixel_data(view: 'ZoomableView') -> str:
            """Helper to format pixel data for a single view."""
            color = view.get_color_at(scene_pos)
            value_str = f"({color.red()},{color.green()},{color.blue()})" if color else "---"
            return f"{view.label_text}: {value_str}"

        pixel_info_str = " | ".join(format_pixel_data(v) for v in self.views)

        self.statusBar().showMessage(f"Path: {sender_view.img_path}  Coords: ({x}, {y})  |  {pixel_info_str}")

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

    def __init__(self, img_path: str, label_text: str):
        super().__init__()
        self.img_path = img_path
        self.label_text = label_text
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._image: Optional[QImage] = None  # Store QImage for fast pixel access
        self._is_handling_wheel = False
        self._image_aspect_ratio = 0.0

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

    def _load_safe_pixmap(self):
        """Safely loads the pixmap, checking for potential resource issues."""
        error_msg = self._get_loading_error()
        if error_msg:
            filename = Path(self.img_path).name
            text_item = self._scene.addText(f"{error_msg}\n{filename}")
            text_item.setDefaultTextColor(QColor(Qt.red))
        else:
            # All checks passed, so we can load the image.
            pixmap = QPixmap(self.img_path)
            self._pixmap_item = self._scene.addPixmap(pixmap)
            self._image = pixmap.toImage()

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

        # Final check by attempting to load into a pixmap.
        pixmap = QPixmap(str(img_path))
        if pixmap.isNull():
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
        self.mouseMovedAtScenePos.emit(self.mapToScene(event.pos()))

    def enterEvent(self, event):
        """Emits the full image path when the mouse enters the view."""
        self.hovered.emit(self.img_path)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Emits an empty string when the mouse leaves the view."""
        self.hovered.emit("")
        super().leaveEvent(event)


def main():
    """Main function to run the application."""
    # Initialize QApplication first, as it can also parse Qt-specific arguments
    app = QApplication(sys.argv)

    parser = argparse.ArgumentParser(
        description="Image Grid Viewer (igridvu). Displays a grid of images from a prefix and a list of suffixes.",
        formatter_class=argparse.RawTextHelpFormatter,  # Keep newlines in help text
        epilog=f"Example: python3 {os.path.basename(__file__)} testimage"
    )
    parser.add_argument(
        "image_prefix",
        help="The common prefix for the image files (e.g., 'testimage')."
    )
    parser.add_argument(
        "suffix_file",
        nargs="?",
        default=None,
        help=f"A text file containing image suffixes, one per line.\nDefaults to '{DEFAULT_SUFFIX_FILE}' in the image prefix directory."
    )
    parser.add_argument(
        "-c", "--columns",
        type=int,
        default=4,
        help="The number of columns in the grid. Defaults to 4."
    )
    args = parser.parse_args()

    if args.suffix_file:
        suffix_file_path = Path(args.suffix_file)
    else:
        # The default is 'igridvu_suffix.txt' in the same directory as the prefix.
        prefix_path = Path(args.image_prefix)
        # If prefix is 'foo/bar_', parent is 'foo'. If 'bar_', parent is '.'.
        suffix_file_path = prefix_path.parent / DEFAULT_SUFFIX_FILE

    # Limit the number of images to prevent excessive resource usage
    MAX_IMAGES = 30

    try:
        # Use encoding='utf-8' for broader compatibility
        with open(suffix_file_path, 'r', encoding='utf-8') as f:
            # Efficiently read up to MAX_IMAGES lines without loading the whole file
            list_of_suffix = list(islice(f, MAX_IMAGES))
            # Check if there were more lines left in the file
            if f.readline():
                print(f"Warning: Suffix file has more than {MAX_IMAGES} lines.", file=sys.stderr)
                print(f"-> Displaying the first {MAX_IMAGES} images.")
    except FileNotFoundError:
        print(f"Error: Suffix file not found at '{suffix_file_path}'", file=sys.stderr)
        sys.exit(1)

    if not list_of_suffix:
        print(f"Info: Suffix file '{suffix_file_path}' is empty. Nothing to display.", file=sys.stderr)
        sys.exit(0)

    # The ImageGrid instance must be stored in a variable for the application to work.
    # We use '_' to indicate that it's not used again in this scope.
    _ = ImageGrid(args.image_prefix, list_of_suffix, columns=args.columns)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
