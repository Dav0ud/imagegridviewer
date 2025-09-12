# -*- coding: utf-8 -*-
"""
The main window for the Image Grid Viewer application.
"""
import os
from typing import List, cast
from pathlib import Path
from itertools import islice

from PySide6.QtWidgets import \
    (QWidget, QGridLayout, QApplication,
     QMainWindow, QVBoxLayout, QFileDialog, QMessageBox,
     QStackedWidget, QPushButton, QLabel)
from PySide6.QtGui import QAction, QKeySequence, QFont
from PySide6.QtCore import Qt, QRectF, QPointF, QStandardPaths, QSize

from .zoomable_view import ZoomableView
from .suffix_editor import SuffixEditorDialog
from .config import MAX_IMAGES
from .create_examples import create_example_dataset


class ImageGrid(QMainWindow):
    """A widget that displays a grid of images."""

    def __init__(self, pre_path: str, list_of_suffix: List[str], suffix_file_path: str,
                 columns: int = 4, app_name: str = "Image Grid Viewer"):
        super().__init__()
        self.pre_path = pre_path
        self.list_of_suffix = list_of_suffix
        self.suffix_file_path = suffix_file_path
        self.columns = columns
        self.app_name = app_name
        self.views: List[ZoomableView] = []
        self.initUI()

    def initUI(self):
        """Initializes the UI and lays out the image labels in a grid."""
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Page 1: Welcome/Empty State
        self.welcome_widget = self._create_welcome_page()
        self.stacked_widget.addWidget(self.welcome_widget)

        # Page 2: Grid View
        self.grid_container = QWidget()
        main_layout = QVBoxLayout(self.grid_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        grid_widget = QWidget()
        self.grid_layout = QGridLayout(grid_widget)
        self.grid_layout.setSpacing(0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(grid_widget)
        main_layout.addStretch(1)
        self.stacked_widget.addWidget(self.grid_container)

        # Set up the status bar with a default message
        self.status_message = "Ready. Hover for path. Move over image for pixel values."
        self.statusBar().showMessage(self.status_message)

        self._create_menu_bar()
        self.resize(800, 600)
        self._center_on_screen()

        # Decide which page to show on startup
        if not self.list_of_suffix:
            self.stacked_widget.setCurrentWidget(self.welcome_widget)
            self.setWindowTitle(self.app_name)
        else:
            self._populate_grid(self.list_of_suffix)
            self.stacked_widget.setCurrentWidget(self.grid_container)
            self.setWindowTitle(f"{self.app_name}: {self.pre_path}...")

        self.show()

    def _create_welcome_page(self) -> QWidget:
        """Creates the widget to show when no images are loaded."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)

        title_label = QLabel("Welcome to Image Grid Viewer")
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)

        instructions_label = QLabel(
            "To get started, please load a set of images.\n\n"
            "You can either open a suffix file via the editor,\n"
            "or generate an example dataset to see how the tool works."
        )
        instructions_label.setAlignment(Qt.AlignCenter)

        open_dataset_button = QPushButton("Open Dataset...")
        open_dataset_button.setFixedSize(QSize(220, 32))
        open_dataset_button.clicked.connect(self._prompt_open_dataset)

        open_editor_button = QPushButton("Open Suffix Editor...")
        open_editor_button.setFixedSize(QSize(220, 32))
        open_editor_button.clicked.connect(self._open_suffix_editor)

        create_example_button = QPushButton("Create Example Dataset...")
        create_example_button.setFixedSize(QSize(220, 32))
        create_example_button.clicked.connect(self._prompt_create_examples)

        layout.addWidget(title_label)
        layout.addWidget(instructions_label)
        layout.addWidget(open_dataset_button, 0, Qt.AlignCenter)
        layout.addWidget(open_editor_button, 0, Qt.AlignCenter)
        layout.addWidget(create_example_button, 0, Qt.AlignCenter)

        return widget

    def _clear_grid(self):
        """Removes all widgets from the grid layout and clears the views list."""
        for view in self.views:
            view.deleteLater()
        self.views.clear()

        # Also clear the layout by deleting all its items
        while (item := self.grid_layout.takeAt(0)) is not None:
            if item.widget():
                item.widget().deleteLater()

    def _populate_grid(self, suffixes: List[str]):
        """Populates the grid with views for the given suffixes."""
        self._clear_grid()
        prefix_path = Path(self.pre_path)

        # Security: Define the base directory to prevent path traversal.
        # All resolved image paths must be within this directory.
        try:
            base_dir = prefix_path.resolve() if prefix_path.is_dir() else prefix_path.parent.resolve()
        except (FileNotFoundError, OSError):
            # If the base path doesn't exist, we can't load anything.
            # This can happen if the prefix points to a deleted directory.
            base_dir = None

        for i, suffix in enumerate(suffixes):
            row = i // self.columns
            col = i % self.columns

            clean_suffix = suffix.rstrip()
            # This check-then-act logic is a Time-of-check-to-time-of-use (TOCTOU)
            # race condition. For a local desktop app, the risk is negligible,
            # but it's an anti-pattern in security-sensitive contexts.
            if prefix_path.is_dir():
                full_path_str = str(prefix_path / clean_suffix)
            else:
                full_path_str = self.pre_path + clean_suffix

            label_text = Path(clean_suffix).stem
            error_msg = None

            if base_dir:
                try:
                    # Security: Resolve the path and check it's within the base directory.
                    resolved_path = Path(full_path_str).resolve()
                    # This check prevents path traversal attacks (e.g., suffix being "../...").
                    # It raises ValueError if the path is not a sub-path.
                    resolved_path.relative_to(base_dir)
                except ValueError:
                    error_msg = "Path traversal\nattempt"
                except (FileNotFoundError, OSError):
                    # This can happen if a suffix points to a non-existent path component.
                    # This is a normal "not found" case that ZoomableView will handle,
                    # so we don't need to set a pre-emptive error here.
                    pass
            else:
                error_msg = "Base path\nnot found"

            view = ZoomableView(label_text=label_text, img_path=full_path_str, error=error_msg)
            self._connect_view_signals(view)

            # AlignTop creates a masonry-like layout for images of different aspect ratios
            self.grid_layout.addWidget(view, row, col, Qt.AlignTop)
            self.views.append(view)

    def _connect_view_signals(self, view: ZoomableView):
        """Connects all necessary signals for a ZoomableView instance."""
        view.hovered.connect(self.update_status_bar)
        view.mouseMovedAtScenePos.connect(self._update_pixel_info)
        view.viewRectChanged.connect(self.sync_views)

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

        open_action = QAction("&Open Dataset...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.setStatusTip("Open a different set of images by selecting one image from the dataset")
        open_action.triggered.connect(self._prompt_open_dataset)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("&Save Snapshot...", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.setStatusTip("Save the current grid view as an image")
        save_action.triggered.connect(self._save_snapshot)
        file_menu.addAction(save_action)

        edit_menu = menu_bar.addMenu("&Edit")
        edit_suffixes_action = QAction("Edit &Suffixes...", self)
        edit_suffixes_action.setStatusTip("Open an editor for the suffix list file")
        edit_suffixes_action.triggered.connect(self._open_suffix_editor)
        edit_menu.addAction(edit_suffixes_action)

        help_menu = menu_bar.addMenu("&Help")
        create_examples_action = QAction("Create Example Dataset...", self)
        create_examples_action.setStatusTip(
            "Create a sample set of images to demonstrate the tool's features"
        )
        create_examples_action.triggered.connect(self._prompt_create_examples)
        help_menu.addAction(create_examples_action)

    def _open_suffix_editor(self):
        """Opens the suffix editor dialog and reloads the grid if changes are saved."""
        dialog = SuffixEditorDialog(self.suffix_file_path, MAX_IMAGES, self)
        if dialog.exec():  # True if the dialog was accepted (saved)
            self._reload_grid()

    def _reload_grid(self):
        """Reloads the suffixes from the file and repopulates the grid."""
        if not self.suffix_file_path or not Path(self.suffix_file_path).is_file():
            self.list_of_suffix = []
        else:
            try:
                with open(self.suffix_file_path, 'r', encoding='utf-8') as f:
                    self.list_of_suffix = [line.strip() for line in islice(f, MAX_IMAGES) if line.strip()]
                self.statusBar().showMessage("Grid reloaded with new suffixes.", 5000)
            except (FileNotFoundError, IOError) as e:
                self.list_of_suffix = []
                self.statusBar().showMessage(f"Error reading suffix file: {e}", 5000)

        if self.list_of_suffix:
            self._populate_grid(self.list_of_suffix)
            self.stacked_widget.setCurrentWidget(self.grid_container)
            self.setWindowTitle(f"{self.app_name}: {self.pre_path}...")
        else:
            self._populate_grid([])  # Clear the grid
            self.stacked_widget.setCurrentWidget(self.welcome_widget)
            self.setWindowTitle(self.app_name)

    def _prompt_open_dataset(self):
        """
        Opens a file dialog to let the user select an image from a dataset,
        then deduces the prefix and suffix file to load the new dataset.
        """
        # Start in the directory of the current prefix, if it exists.
        start_dir = str(Path(self.pre_path).parent) if self.pre_path else ""

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image from Dataset",
            start_dir,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if not file_path:
            return  # User cancelled

        selected_file = Path(file_path)
        image_dir = selected_file.parent

        # Find the corresponding suffix file
        suffix_file_path = image_dir / "igridvu_suffix.txt"
        if not suffix_file_path.is_file():
            QMessageBox.warning(
                self,
                "Suffix File Not Found",
                f"Could not find 'igridvu_suffix.txt' in the directory:\n{image_dir}"
            )
            return

        # Read suffixes from the file
        try:
            with open(suffix_file_path, 'r', encoding='utf-8') as f:
                # Security: Use islice to prevent reading a massive file into memory.
                suffixes = [line.strip() for line in islice(f, MAX_IMAGES) if line.strip()]
                if f.readline():
                    QMessageBox.warning(
                        self,
                        "Suffix Limit Reached",
                        f"The suffix file has more than {MAX_IMAGES} lines.\n"
                        f"Only the first {MAX_IMAGES} will be considered for this dataset."
                    )
        except IOError as e:
            QMessageBox.critical(self, "Error Reading File", f"Could not read suffix file:\n{e}")
            return

        if not suffixes:
            QMessageBox.warning(self, "Empty Suffix File", f"The suffix file is empty:\n{suffix_file_path}")
            return

        # Deduce the prefix by finding the longest matching suffix
        best_match_len = -1
        new_prefix = None
        for suffix in suffixes:
            if selected_file.name.endswith(suffix):
                if len(suffix) > best_match_len:
                    best_match_len = len(suffix)
                    prefix_len = len(selected_file.name) - len(suffix)
                    new_prefix = str(selected_file.parent / selected_file.name[:prefix_len])

        if new_prefix is None:
            QMessageBox.warning(self, "Could Not Deduce Prefix", f"The selected file '{selected_file.name}' does not match any suffix in '{suffix_file_path.name}'.")
            return

        # We have a new prefix and suffix file, update the main window state and reload
        self.pre_path = new_prefix
        self.suffix_file_path = str(suffix_file_path)
        self._reload_grid()

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

    def _prompt_create_examples(self):
        """
        Shows a dialog to let the user choose a location and then creates
        the example image set after confirmation.
        """
        # Suggest a default location in the user's "Documents" directory.
        # This is crucial for macOS apps which run from a read-only location.
        default_location = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)

        # Open a dialog to let the user select a directory.
        target_dir_str = QFileDialog.getExistingDirectory(
            self,
            "Choose a Location for the Example Dataset",
            default_location,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if not target_dir_str:
            return  # User cancelled the dialog

        target_dir = Path(target_dir_str)

        # Now, confirm with the user before writing files.
        reply = QMessageBox.information(
            self,
            "Confirm Example Dataset Creation",
            f"This will create a 'testscene' folder with example images in the "
            f"following directory:\n\n{target_dir}\n\nProceed?",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok,
        )

        if reply == QMessageBox.StandardButton.Ok:
            # The create_example_dataset function uses Qt classes, so an application
            # instance must exist. This is guaranteed when called from the GUI.
            success, message, prefix_path_str = create_example_dataset(target_dir)

            if success:
                # Ask the user if they want to load the new dataset
                load_reply = QMessageBox.question(
                    self,
                    "Success",
                    f"{message}\n\nWould you like to load this example dataset now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if load_reply == QMessageBox.StandardButton.Yes:
                    prefix_path = Path(prefix_path_str)
                    self.pre_path = prefix_path_str
                    self.suffix_file_path = str(prefix_path.parent / "igridvu_suffix.txt")
                    self._reload_grid()
            else:
                QMessageBox.critical(self, "Error", message)

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
        """Updates pixel info label on each view at a given scene coordinate."""
        sender_view = cast(ZoomableView, self.sender())
        if not isinstance(sender_view, ZoomableView) or not sender_view.has_image():
            return

        display_x = int(scene_pos.x())
        display_y = int(scene_pos.y())

        for view in self.views:
            color = view.get_color_at(scene_pos)
            if color:
                # Assuming RGBA, show all 4 values if alpha exists
                if view._image and view._image.hasAlphaChannel():
                    value_str = f"({color.red()},{color.green()},{color.blue()},{color.alpha()})"
                else:
                    value_str = f"({color.red()},{color.green()},{color.blue()})"
                info_str = f"({display_x},{display_y}) {value_str}"
                view.set_pixel_info(info_str)
            else:
                # If get_color_at returns None, display -1
                view.set_pixel_info(f"({display_x},{display_y}) -1")

        # Update status bar with path of the sender view
        self.statusBar().showMessage(f"Path: {sender_view.img_path}")
