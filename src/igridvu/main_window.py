# -*- coding: utf-8 -*-
"""
The main window for the Image Grid Viewer application.
"""
import os
from typing import List
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QGridLayout, QApplication,
                             QMainWindow, QVBoxLayout, QFileDialog)
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt, QRectF, QPointF, QStandardPaths

from .zoomable_view import ZoomableView


class ImageGrid(QMainWindow):
    """A widget that displays a grid of images."""

    def __init__(self, pre_path: str, list_of_suffix: List[str],
                 columns: int = 4, app_name: str = "Image Grid Viewer"):
        super().__init__()
        self.pre_path = pre_path
        self.list_of_suffix = list_of_suffix
        self.columns = columns
        self.app_name = app_name
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
        self.grid_container = QWidget()
        self.views: List[ZoomableView] = []
        layout = QGridLayout(self.grid_container)
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
        main_layout.addWidget(self.grid_container)
        # Add a stretchable space at the bottom, pushing the grid upwards.
        main_layout.addStretch(1)

        # Set up the status bar with a default message
        self.status_message = "Ready. Hover for path. Move over image for pixel values."
        self.statusBar().showMessage(self.status_message)

        self._create_menu_bar()

        self.setWindowTitle(f"{self.app_name}: {self.pre_path}...")
        self.resize(800, 600)
        self._center_on_screen()
        self.show()

    def _center_on_screen(self):
        """Centers the window on the primary screen."""
        frame_geometry = self.frameGeometry()
        center_point = QApplication.primaryScreen().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def _create_menu_bar(self):
        """Creates the main menu bar with a 'File' menu."""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        save_action = QAction("&Save Snapshot...", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.setStatusTip("Save the current grid view as an image")
        save_action.triggered.connect(self._save_snapshot)
        file_menu.addAction(save_action)

    def _save_snapshot(self):
        """Saves a snapshot of the application window to a file."""
        # Grab the window content BEFORE opening the file dialog. This ensures
        # that the status bar text (e.g., pixel info) is captured correctly,
        # as opening the dialog can cause the window to lose focus and reset the text.
        pixmap_to_save = self.grab()

        # Suggest a default path in the user's "Pictures" directory
        pictures_location = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
        default_path = os.path.join(pictures_location, "image_grid_snapshot.png")

        # Open a file dialog to let the user choose where to save
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Snapshot",
            default_path,
            "Images (*.png *.jpg *.bmp)"
        )

        if file_path:
            # Save the previously captured pixmap.
            if pixmap_to_save.save(file_path):
                self.statusBar().showMessage(f"Snapshot saved to {file_path}", 5000)  # Show for 5s
            else:
                self.statusBar().showMessage(f"Error: Failed to save snapshot to {file_path}", 5000)

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

        if sender_view.get_color_at(scene_pos) is None:
            self.update_status_bar(sender_view.img_path)
            return

        x, y = int(scene_pos.x()), int(scene_pos.y())

        def format_pixel_data(view: ZoomableView) -> str:
            """Helper to format pixel data for a single view."""
            color = view.get_color_at(scene_pos)
            value_str = f"({color.red()},{color.green()},{color.blue()})" if color else "---"
            return f"{view.label_text}: {value_str}"

        pixel_info_str = " | ".join(format_pixel_data(v) for v in self.views)

        self.statusBar().showMessage(f"Path: {sender_view.img_path}  Coords: ({x}, {y})  |  {pixel_info_str}")