# -*- coding: utf-8 -*-
"""
Unit and integration tests for the ImageGrid main window from src/igridvu/main_window.py.

To run these tests, you need to install pytest and pytest-qt:
  pip install pytest pytest-qt

Then, from the command line in the project directory, run:
  python3 -m pytest
"""
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest
from PySide6.QtCore import QPoint, QPointF, QStandardPaths, Qt
from PySide6.QtGui import QAction, QColor, QWheelEvent, QImage
from PySide6.QtWidgets import \
    QApplication, QFileDialog, QGridLayout, QMessageBox, QPushButton, QGraphicsTextItem

from igridvu import ImageGrid, ZoomableView


def get_scene_text(view):
    """Helper to extract text from the first QGraphicsTextItem in a scene."""
    text_items = [item for item in view._scene.items() if isinstance(item, QGraphicsTextItem)]
    return text_items[0].toPlainText() if text_items else ""


def test_image_grid_widget_creation(qtbot):
    """Tests that ImageGrid creates the correct number of ZoomableView widgets."""
    pre_path = "test_image_"
    suffixes = ["1.png\n", "2.png\n", "3.png\n"]

    grid = ImageGrid(pre_path, suffixes, suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)

    # Find all ZoomableView widgets that are children of the grid
    views = grid.findChildren(ZoomableView)
    assert len(views) == len(suffixes)


def test_image_grid_layout_wrapping(qtbot):
    """
    Tests that the grid layout correctly wraps to a new row using the
    default number of columns.
    """
    # Create 5 suffixes to test wrapping past the default columns of 4
    suffixes = [f"{i}.png" for i in range(1, 6)]
    grid = ImageGrid("test_prefix_", suffixes, suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)

    layout = grid.grid_layout
    assert isinstance(layout, QGridLayout)
    # The 5th item (index 4) should be at position (row=1, column=0)
    row, col, _row_span, _col_span = layout.getItemPosition(4)
    assert row == 1, "The 5th widget should be on the second row (index 1)"
    assert col == 0, "The 5th widget should be in the first column (index 0)"


def test_image_grid_layout_custom_columns(qtbot):
    """
    Tests that the grid layout correctly uses a custom number of columns.
    """
    # Create 3 suffixes to test wrapping with 2 columns
    suffixes = [f"{i}.png" for i in range(1, 4)]  # 1.png, 2.png, 3.png
    # Set columns to 2
    grid = ImageGrid("test_prefix_", suffixes, suffix_file_path="dummy.txt", columns=2)
    qtbot.addWidget(grid)

    layout = grid.grid_layout
    assert isinstance(layout, QGridLayout)
    # The 3rd item (index 2) should be at (row=1, col=0)
    row, col, _row_span, _col_span = layout.getItemPosition(2)
    assert row == 1, "The 3rd widget should be on the second row (index 1)"
    assert col == 0, "The 3rd widget should be in the first column (index 0)"


def test_image_grid_handles_leading_space_in_suffix(qtbot):
    """
    Tests that ImageGrid correctly handles suffixes with leading spaces,
    which is why rstrip() is used instead of strip().
    """
    pre_path = "test_image"
    # Suffix has a leading space and a trailing newline
    suffixes = [" 1.png"]
    grid = ImageGrid(pre_path, suffixes, suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)

    views = grid.findChildren(ZoomableView)
    # The path passed to the ZoomableView should have the space preserved
    assert views[0].img_path == "test_image 1.png"


def test_image_grid_directory_prefix(tmp_path: Path, qtbot, create_dummy_image):
    """
    Tests that ImageGrid correctly joins paths when the prefix is a directory.
    """
    # The prefix is the temp directory itself
    pre_path = str(tmp_path)
    # The suffix is just the filename
    suffixes = ["image.png"]
    # Create the image at the expected final path
    expected_path = tmp_path / "image.png"
    create_dummy_image(tmp_path, filename="image.png")

    grid = ImageGrid(pre_path, suffixes, suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)

    assert grid.views[0].img_path == str(expected_path)


def test_image_grid_synchronizes_views(tmp_path: Path, qtbot, create_dummy_image):
    """
    Tests that changing one view in the ImageGrid synchronizes all other views
    by calling their setViewRect method.
    """
    # Create two dummy images in the temp path
    create_dummy_image(tmp_path, filename="1.png", width=200, height=200)
    create_dummy_image(tmp_path, filename="2.png", width=200, height=200)

    suffixes = ["1.png", "2.png"]
    grid = ImageGrid(str(tmp_path), suffixes, suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)
    grid.show()
    qtbot.waitActive(grid)

    # Get the views from the grid
    view1, view2 = grid.views

    # Mock the setViewRect method on the second view
    view2.setViewRect = Mock()

    # Simulate a zoom-in wheel event on the first view's viewport
    viewport = view1.viewport()
    center_pos = QPoint(viewport.width() // 2, viewport.height() // 2)
    # Use NoScrollPhase for a single, discrete wheel event.
    wheel_event = QWheelEvent(
        QPointF(center_pos),  # position
        QPointF(view1.mapToGlobal(center_pos)),  # globalPosition
        QPoint(0, 0),  # pixelDelta
        QPoint(0, 120),  # angleDelta
        Qt.NoButton,
        Qt.NoModifier,
        Qt.NoScrollPhase,
        False  # inverted
    )
    QApplication.sendEvent(viewport, wheel_event)

    # Wait for the signal to propagate and the mock to be called
    qtbot.waitUntil(lambda: view2.setViewRect.called, timeout=1000)

    # Assert that the method was called exactly once
    view2.setViewRect.assert_called_once()

    # Verify it was called with the correct rectangle from the source view
    called_rect = view2.setViewRect.call_args.args[0]
    expected_rect = view1.mapToScene(view1.viewport().rect()).boundingRect()

    # Compare components with pytest.approx for floating-point robustness
    assert called_rect.x() == pytest.approx(expected_rect.x())
    assert called_rect.y() == pytest.approx(expected_rect.y())
    assert called_rect.width() == pytest.approx(expected_rect.width())
    assert called_rect.height() == pytest.approx(expected_rect.height())


def test_image_grid_status_bar_hover(tmp_path: Path, qtbot, create_dummy_image):
    """Tests that hovering over a view updates the status bar."""
    img_path = create_dummy_image(tmp_path)
    grid = ImageGrid(str(img_path.parent), [img_path.name], suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)
    grid.show()

    view = grid.views[0]
    status_bar = grid.statusBar()

    # Simulate mouse entering the view
    view.hovered.emit(view.img_path)
    assert status_bar.currentMessage() == f"Path: {view.img_path}"

    # Simulate mouse leaving the view
    view.hovered.emit("")
    assert status_bar.currentMessage() == grid.status_message

def test_image_grid_pixel_info_display(tmp_path: Path, qtbot, create_dummy_image):
    """Tests that moving the mouse over a view updates the pixel info labels on all views,
    including corner and edge cases.
    """
    # Create a 3x3 image with distinct colors for testing
    img_path = create_dummy_image(tmp_path, filename="test_3x3.png", width=3, height=3)
    image = QImage(3, 3, QImage.Format_ARGB32)
    image.fill(Qt.black) # Default to black

    # Assign specific colors to pixels for testing
    colors = {
        (0, 0): QColor(255, 0, 0),   # Red (Top-Left)
        (1, 0): QColor(0, 255, 0),   # Green (Top-Middle)
        (2, 0): QColor(0, 0, 255),   # Blue (Top-Right)
        (0, 1): QColor(255, 255, 0), # Yellow (Middle-Left)
        (1, 1): QColor(255, 0, 255), # Magenta (Center)
        (2, 1): QColor(0, 255, 255), # Cyan (Middle-Right)
        (0, 2): QColor(128, 0, 0),   # Dark Red (Bottom-Left)
        (1, 2): QColor(0, 128, 0),   # Dark Green (Bottom-Middle)
        (2, 2): QColor(0, 0, 128)    # Dark Blue (Bottom-Right)
    }
    for (x, y), color in colors.items():
        image.setPixelColor(x, y, color)
    image.save(str(img_path))

    grid = ImageGrid(str(tmp_path), [img_path.name], suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)
    grid.show()

    view = grid.views[0]
    status_bar = grid.statusBar()

    # Mock set_pixel_info to capture calls
    view.set_pixel_info = Mock()

    # Test various pixel positions
    test_cases = [
        # (scene_pos, expected_pixel_x, expected_pixel_y, expected_color)
        (QPointF(0.1, 0.1), 0, 0, colors[(0,0)]), # Top-Left
        (QPointF(1.5, 0.1), 1, 0, colors[(1,0)]), # Top-Middle
        (QPointF(2.9, 0.1), 2, 0, colors[(2,0)]), # Top-Right
        (QPointF(0.1, 1.5), 0, 1, colors[(0,1)]), # Middle-Left
        (QPointF(1.5, 1.5), 1, 1, colors[(1,1)]), # Center
        (QPointF(2.9, 1.5), 2, 1, colors[(2,1)]), # Middle-Right
        (QPointF(0.1, 2.9), 0, 2, colors[(0,2)]), # Bottom-Left
        (QPointF(1.5, 2.9), 1, 2, colors[(1,2)]), # Bottom-Middle
        (QPointF(2.9, 2.9), 2, 2, colors[(2,2)]), # Bottom-Right
    ]

    for scene_pos, expected_px, expected_py, expected_color in test_cases:
        # Reset mock before each test case
        view.set_pixel_info.reset_mock()

        # Simulate mouse movement
        view.mouseMovedAtScenePos.emit(scene_pos)

        # Construct expected color string (assuming ARGB32 for simplicity, alpha=255)
        expected_value_str = f"({expected_color.red()},{expected_color.green()},{expected_color.blue()},{expected_color.alpha()})"
        expected_info_str = f"({expected_px},{expected_py}) {expected_value_str}"

        # Assert set_pixel_info was called with the correct string
        view.set_pixel_info.assert_called_with(expected_info_str)
        assert status_bar.currentMessage() == f"Path: {view.img_path}"

    # Test fallback behavior (out of bounds) - already covered by test_image_grid_pixel_info_out_of_bounds
    # but good to have a quick check here too for completeness of this test
    view.set_pixel_info.reset_mock()
    view.get_color_at = Mock(return_value=None) # Mock get_color_at to return None
    out_of_bounds_pos = QPointF(100, 100)
    view.mouseMovedAtScenePos.emit(out_of_bounds_pos)
    view.set_pixel_info.assert_called_with(f"({int(out_of_bounds_pos.x())},{int(out_of_bounds_pos.y())}) -1")
    assert status_bar.currentMessage() == f"Path: {view.img_path}"


def test_welcome_page_shown_on_no_suffixes(qtbot):
    """Tests that ImageGrid shows the welcome page when no suffixes are provided."""
    grid = ImageGrid("pre_path", [], suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)

    # Assert that the welcome page is the current widget
    assert grid.stacked_widget.currentWidget() == grid.welcome_widget

    # Assert that no image views were created
    views = grid.findChildren(ZoomableView)
    assert len(views) == 0


def test_image_grid_window_title(qtbot):
    """Tests that the ImageGrid window has an appropriate title."""
    # Case 1: With a prefix and suffixes, showing the grid
    pre_path = "/some/test/directory/prefix_"
    grid_with_prefix = ImageGrid(pre_path, ["a.png"], suffix_file_path="dummy.txt")
    qtbot.addWidget(grid_with_prefix)

    assert "Image Grid Viewer" in grid_with_prefix.windowTitle()
    assert pre_path in grid_with_prefix.windowTitle()

    # Case 2: With no suffixes, showing the welcome screen
    grid_no_prefix = ImageGrid("", [], suffix_file_path="dummy.txt")
    qtbot.addWidget(grid_no_prefix)
    assert grid_no_prefix.windowTitle() == "Image Grid Viewer"


def test_image_grid_view_labels(qtbot):
    """Tests that the labels for each view are set correctly from the suffixes."""
    pre_path = "prefix_"
    suffixes = ["a.png", "b.png"]
    grid = ImageGrid(pre_path, suffixes, suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)

    assert grid.views[0].label_text == "a"
    assert grid.views[1].label_text == "b"


@pytest.mark.parametrize(
    "dialog_filename, save_return, expected_status_contains, save_called",
    [
        ("snapshot.png", True, "Snapshot saved to", True),
        ("", True, "Ready.", False),  # Cancel case
        ("snapshot.png", False, "Error: Failed to save snapshot", True),
    ],
    ids=["success", "cancel", "failure"]
)
def test_save_snapshot(qtbot, tmp_path, monkeypatch, dialog_filename, save_return, expected_status_contains, save_called):
    """Tests the _save_snapshot method for success, cancellation, and failure."""
    # 1. Setup
    grid = ImageGrid("pre_path", ["a.png"], suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)
    grid.show()
    qtbot.waitActive(grid)

    save_path = tmp_path / dialog_filename if dialog_filename else ""

    # 2. Mock dependencies
    # Mock QFileDialog to return a predictable path or cancellation
    monkeypatch.setattr(
        QFileDialog,
        'getSaveFileName',
        lambda *args, **kwargs: (str(save_path), "Images (*.png *.jpg *.bmp)")
    )

    # Mock the `grab` method to return a mock pixmap whose `save` method can be tracked
    mock_pixmap = MagicMock()
    mock_pixmap.save.return_value = save_return
    monkeypatch.setattr(grid, 'grab', lambda: mock_pixmap)

    # Mock QStandardPaths to avoid dependency on the user's "Pictures" folder
    monkeypatch.setattr(QStandardPaths, 'writableLocation', lambda location: str(tmp_path))

    # 3. Action
    grid._save_snapshot()

    # 4. Assertions
    if save_called:
        mock_pixmap.save.assert_called_once_with(str(save_path))
    else:
        mock_pixmap.save.assert_not_called()

    assert expected_status_contains in grid.statusBar().currentMessage()


def test_welcome_page_buttons_connected(qtbot):
    """Tests that the welcome page buttons are connected to the correct slots."""
    grid = ImageGrid("", [], "dummy.txt")
    qtbot.addWidget(grid)

    # Mock the target methods
    grid._open_suffix_editor = Mock()
    grid._prompt_create_examples = Mock()

    # Find buttons by their text
    buttons = grid.welcome_widget.findChildren(QPushButton)
    open_editor_button = next(b for b in buttons if "Suffix Editor" in b.text())
    create_example_button = next(b for b in buttons if "Example Dataset" in b.text())

    # Click buttons and assert that the mocks were called
    qtbot.mouseClick(open_editor_button, Qt.LeftButton)
    grid._open_suffix_editor.assert_called_once()

    qtbot.mouseClick(create_example_button, Qt.LeftButton)
    grid._prompt_create_examples.assert_called_once()

def test_welcome_page_open_dataset_button_connected(qtbot):
    """Tests that the 'Open Dataset...' button on the welcome page is connected to the correct slot."""
    grid = ImageGrid("", [], "dummy.txt")
    qtbot.addWidget(grid)

    # Mock the target method
    grid._prompt_open_dataset = Mock()

    # Find the 'Open Dataset...' button by its text
    buttons = grid.welcome_widget.findChildren(QPushButton)
    open_dataset_button = next(b for b in buttons if "Open Dataset..." in b.text())

    # Click the button and assert that the mock was called
    qtbot.mouseClick(open_dataset_button, Qt.LeftButton)
    grid._prompt_open_dataset.assert_called_once()

def test_path_traversal_is_blocked(tmp_path: Path, qtbot, create_dummy_image):
    """
    Tests that a suffix attempting path traversal is caught and an error is displayed.
    """
    # 1. Setup
    # Create a dummy file that the traversal will attempt to access.
    secret_file_path = tmp_path / "secret.txt"
    secret_file_path.touch()

    # The legitimate image directory
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_dummy_image(image_dir, filename="real.png")

    # The prefix points to the legitimate directory
    pre_path = str(image_dir)
    # The suffix attempts to traverse up and out
    suffixes = ["../secret.txt"]

    # 2. Action
    grid = ImageGrid(pre_path, suffixes, suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)

    # 3. Assertions
    assert len(grid.views) == 1
    view = grid.views[0]

    # The view should not have a pixmap
    assert not view.has_image()

    # The view should display the path traversal error message
    scene_text = get_scene_text(view)
    assert "Path traversal" in scene_text
    assert "attempt" in scene_text

def test_open_dataset_flow(qtbot, monkeypatch, tmp_path: Path):
    """Tests the full flow of opening a new dataset via the file dialog."""
    grid = ImageGrid("old_prefix", ["old.png"], "old_suffix.txt")
    qtbot.addWidget(grid)
    new_dataset_dir = tmp_path / "new_dataset"
    new_dataset_dir.mkdir()
    new_prefix_str = str(new_dataset_dir / "image_")
    suffix_file = new_dataset_dir / "igridvu_suffix.txt"
    suffixes = ["a.png", "b.png"]
    suffix_file.write_text("\n".join(suffixes))
    selected_file = new_dataset_dir / "image_a.png"
    selected_file.touch()
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args, **kwargs: (str(selected_file), ""))
    grid._reload_grid = Mock()
    grid._prompt_open_dataset()
    assert grid.pre_path == new_prefix_str
    assert grid.suffix_file_path == str(suffix_file)
    grid._reload_grid.assert_called_once()

def test_open_dataset_handles_ambiguous_suffixes(qtbot, monkeypatch, tmp_path: Path):
    """Tests that the longest matching suffix is used when opening a dataset."""
    grid = ImageGrid("old_prefix", ["old.png"], "old_suffix.txt")
    qtbot.addWidget(grid)
    new_dataset_dir = tmp_path / "new_dataset"
    new_dataset_dir.mkdir()
    
    # Ambiguous suffixes
    suffixes = ["a.png", "ba.png"]
    suffix_file = new_dataset_dir / "igridvu_suffix.txt"
    suffix_file.write_text("\n".join(suffixes))
    
    # Selected file matches the longer suffix
    selected_file = new_dataset_dir / "image_ba.png"
    selected_file.touch()
    
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args, **kwargs: (str(selected_file), ""))
    grid._reload_grid = Mock()
    
    grid._prompt_open_dataset()
    
    # The prefix should be based on the longest match "ba.png", so "image_"
    expected_prefix = str(new_dataset_dir / "image_")
    assert grid.pre_path == expected_prefix


@pytest.mark.parametrize("load_answer", [QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No])
@patch('igridvu.main_window.create_example_dataset')
def test_create_example_dataset_action_and_load(mock_create_dataset, qtbot, monkeypatch, tmp_path: Path, load_answer):
    """Tests the full flow of creating and optionally loading the example dataset."""
    # 1. Setup
    grid = ImageGrid("", [], "dummy.txt")
    qtbot.addWidget(grid)

    # 2. Mock dependencies
    # Mock all dialogs to prevent them from blocking the test run
    monkeypatch.setattr(
        QFileDialog,
        'getExistingDirectory',
        lambda *args, **kwargs: str(tmp_path)
    )
    mock_info = Mock(return_value=QMessageBox.StandardButton.Ok)
    mock_question = Mock(return_value=load_answer)
    monkeypatch.setattr(QMessageBox, 'information', mock_info)
    monkeypatch.setattr(QMessageBox, 'question', mock_question)

    # The mocked create_example_dataset will return this path, using tmp_path
    # for a clean, isolated test environment.
    example_prefix = str(tmp_path / "testscene" / "scene1_")
    mock_create_dataset.return_value = (True, "Success!", example_prefix)

    # Mock the reload function to check if it's called
    grid._reload_grid = Mock()

    # 3. Action: Find and trigger the action from the menu
    # Find the action directly to avoid potential issues with menu object lifecycles in tests.
    create_action = next(a for a in grid.findChildren(QAction) if a.text() == "Create Example Dataset...")
    create_action.trigger()

    # 4. Assertions
    mock_info.assert_called_once()  # The first confirmation dialog
    mock_create_dataset.assert_called_once_with(tmp_path)
    mock_question.assert_called_once()  # The "load now?" dialog

    if load_answer == QMessageBox.StandardButton.Yes:
        assert grid.pre_path == example_prefix
        assert grid.suffix_file_path == str(Path(example_prefix).parent / "igridvu_suffix.txt")
        grid._reload_grid.assert_called_once()
    else:
        grid._reload_grid.assert_not_called()


def test_image_grid_pixel_info_out_of_bounds(tmp_path: Path, qtbot, create_dummy_image):
    """
    Tests that moving the mouse over a view updates pixel info labels correctly,
    displaying '-1' for views where the pixel is out of bounds.
    """
    # Create two images of different sizes
    img1_path = create_dummy_image(tmp_path, filename="1.png", width=10, height=10)
    img2_path = create_dummy_image(tmp_path, filename="2.png", width=5, height=5)
    suffixes = [img1_path.name, img2_path.name]
    grid = ImageGrid(str(tmp_path), suffixes, suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)
    grid.show()

    view1, view2 = grid.views

    # Mock get_color_at for both views
    # For view1 (larger image), return a color for an in-bounds pixel
    view1.get_color_at = Mock(return_value=QColor(10, 20, 30))
    # For view2 (smaller image), return None for the same scene_pos (out of bounds)
    view2.get_color_at = Mock(return_value=None)

    # Mock set_pixel_info for both views to check their calls
    view1.set_pixel_info = Mock()
    view2.set_pixel_info = Mock()

    # Simulate mouse moving over view1 at a scene position that is in-bounds for view1
    # but out-of-bounds for view2
    scene_pos = QPointF(7, 7) # This pixel is within 10x10 but outside 5x5
    view1.mouseMovedAtScenePos.emit(scene_pos)

    # Check that pixel info labels are updated correctly
    # view1 should show the color
    view1.set_pixel_info.assert_called_with("(7,7) (10,20,30,255)")
    # view2 should show -1 because get_color_at returned None
    view2.set_pixel_info.assert_called_with("(7,7) -1")

    # Check status bar (should show path of the sender view)
    assert grid.statusBar().currentMessage() == f"Path: {view1.img_path}"


def test_welcome_page_shown_on_no_suffixes(qtbot):
    """Tests that ImageGrid shows the welcome page when no suffixes are provided."""
    grid = ImageGrid("pre_path", [], suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)

    # Assert that the welcome page is the current widget
    assert grid.stacked_widget.currentWidget() == grid.welcome_widget

    # Assert that no image views were created
    views = grid.findChildren(ZoomableView)
    assert len(views) == 0


def test_image_grid_window_title(qtbot):
    """Tests that the ImageGrid window has an appropriate title."""
    # Case 1: With a prefix and suffixes, showing the grid
    pre_path = "/some/test/directory/prefix_"
    grid_with_prefix = ImageGrid(pre_path, ["a.png"], suffix_file_path="dummy.txt")
    qtbot.addWidget(grid_with_prefix)

    assert "Image Grid Viewer" in grid_with_prefix.windowTitle()
    assert pre_path in grid_with_prefix.windowTitle()

    # Case 2: With no suffixes, showing the welcome screen
    grid_no_prefix = ImageGrid("", [], suffix_file_path="dummy.txt")
    qtbot.addWidget(grid_no_prefix)
    assert grid_no_prefix.windowTitle() == "Image Grid Viewer"


def test_image_grid_view_labels(qtbot):
    """Tests that the labels for each view are set correctly from the suffixes."""
    pre_path = "prefix_"
    suffixes = ["a.png", "b.png"]
    grid = ImageGrid(pre_path, suffixes, suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)

    assert grid.views[0].label_text == "a"
    assert grid.views[1].label_text == "b"


@pytest.mark.parametrize(
    "dialog_filename, save_return, expected_status_contains, save_called",
    [
        ("snapshot.png", True, "Snapshot saved to", True),
        ("", True, "Ready.", False),  # Cancel case
        ("snapshot.png", False, "Error: Failed to save snapshot", True),
    ],
    ids=["success", "cancel", "failure"]
)
def test_save_snapshot(qtbot, tmp_path, monkeypatch, dialog_filename, save_return, expected_status_contains, save_called):
    """Tests the _save_snapshot method for success, cancellation, and failure."""
    # 1. Setup
    grid = ImageGrid("pre_path", ["a.png"], suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)
    grid.show()
    qtbot.waitActive(grid)

    save_path = tmp_path / dialog_filename if dialog_filename else ""

    # 2. Mock dependencies
    # Mock QFileDialog to return a predictable path or cancellation
    monkeypatch.setattr(
        QFileDialog,
        'getSaveFileName',
        lambda *args, **kwargs: (str(save_path), "Images (*.png *.jpg *.bmp)")
    )

    # Mock the `grab` method to return a mock pixmap whose `save` method can be tracked
    mock_pixmap = MagicMock()
    mock_pixmap.save.return_value = save_return
    monkeypatch.setattr(grid, 'grab', lambda: mock_pixmap)

    # Mock QStandardPaths to avoid dependency on the user's "Pictures" folder
    monkeypatch.setattr(QStandardPaths, 'writableLocation', lambda location: str(tmp_path))

    # 3. Action
    grid._save_snapshot()

    # 4. Assertions
    if save_called:
        mock_pixmap.save.assert_called_once_with(str(save_path))
    else:
        mock_pixmap.save.assert_not_called()

    assert expected_status_contains in grid.statusBar().currentMessage()


def test_welcome_page_buttons_connected(qtbot):
    """Tests that the welcome page buttons are connected to the correct slots."""
    grid = ImageGrid("", [], "dummy.txt")
    qtbot.addWidget(grid)

    # Mock the target methods
    grid._open_suffix_editor = Mock()
    grid._prompt_create_examples = Mock()

    # Find buttons by their text
    buttons = grid.welcome_widget.findChildren(QPushButton)
    open_editor_button = next(b for b in buttons if "Suffix Editor" in b.text())
    create_example_button = next(b for b in buttons if "Example Dataset" in b.text())

    # Click buttons and assert that the mocks were called
    qtbot.mouseClick(open_editor_button, Qt.LeftButton)
    grid._open_suffix_editor.assert_called_once()

    qtbot.mouseClick(create_example_button, Qt.LeftButton)
    grid._prompt_create_examples.assert_called_once()

def test_welcome_page_open_dataset_button_connected(qtbot):
    """Tests that the 'Open Dataset...' button on the welcome page is connected to the correct slot."""
    grid = ImageGrid("", [], "dummy.txt")
    qtbot.addWidget(grid)

    # Mock the target method
    grid._prompt_open_dataset = Mock()

    # Find the 'Open Dataset...' button by its text
    buttons = grid.welcome_widget.findChildren(QPushButton)
    open_dataset_button = next(b for b in buttons if "Open Dataset..." in b.text())

    # Click the button and assert that the mock was called
    qtbot.mouseClick(open_dataset_button, Qt.LeftButton)
    grid._prompt_open_dataset.assert_called_once()


def test_path_traversal_is_blocked(tmp_path: Path, qtbot, create_dummy_image):
    """
    Tests that a suffix attempting path traversal is caught and an error is displayed.
    """
    # 1. Setup
    # Create a dummy file that the traversal will attempt to access.
    secret_file_path = tmp_path / "secret.txt"
    secret_file_path.touch()

    # The legitimate image directory
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_dummy_image(image_dir, filename="real.png")

    # The prefix points to the legitimate directory
    pre_path = str(image_dir)
    # The suffix attempts to traverse up and out
    suffixes = ["../secret.txt"]

    # 2. Action
    grid = ImageGrid(pre_path, suffixes, suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)

    # 3. Assertions
    assert len(grid.views) == 1
    view = grid.views[0]

    # The view should not have a pixmap
    assert not view.has_image()

    # The view should display the path traversal error message
    scene_text = get_scene_text(view)
    assert "Path traversal" in scene_text
    assert "attempt" in scene_text


def test_open_dataset_flow(qtbot, monkeypatch, tmp_path: Path):
    """Tests the full flow of opening a new dataset via the file dialog."""
    grid = ImageGrid("old_prefix", ["old.png"], "old_suffix.txt")
    qtbot.addWidget(grid)
    new_dataset_dir = tmp_path / "new_dataset"
    new_dataset_dir.mkdir()
    new_prefix_str = str(new_dataset_dir / "image_")
    suffix_file = new_dataset_dir / "igridvu_suffix.txt"
    suffixes = ["a.png", "b.png"]
    suffix_file.write_text("\n".join(suffixes))
    selected_file = new_dataset_dir / "image_a.png"
    selected_file.touch()
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args, **kwargs: (str(selected_file), ""))
    grid._reload_grid = Mock()
    grid._prompt_open_dataset()
    assert grid.pre_path == new_prefix_str
    assert grid.suffix_file_path == str(suffix_file)
    grid._reload_grid.assert_called_once()

def test_open_dataset_handles_ambiguous_suffixes(qtbot, monkeypatch, tmp_path: Path):
    """Tests that the longest matching suffix is used when opening a dataset."""
    grid = ImageGrid("old_prefix", ["old.png"], "old_suffix.txt")
    qtbot.addWidget(grid)
    new_dataset_dir = tmp_path / "new_dataset"
    new_dataset_dir.mkdir()
    
    # Ambiguous suffixes
    suffixes = ["a.png", "ba.png"]
    suffix_file = new_dataset_dir / "igridvu_suffix.txt"
    suffix_file.write_text("\n".join(suffixes))
    
    # Selected file matches the longer suffix
    selected_file = new_dataset_dir / "image_ba.png"
    selected_file.touch()
    
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args, **kwargs: (str(selected_file), ""))
    grid._reload_grid = Mock()
    
    grid._prompt_open_dataset()
    
    # The prefix should be based on the longest match "ba.png", so "image_"
    expected_prefix = str(new_dataset_dir / "image_")
    assert grid.pre_path == expected_prefix


@pytest.mark.parametrize("load_answer", [QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No])
@patch('igridvu.main_window.create_example_dataset')
def test_create_example_dataset_action_and_load(mock_create_dataset, qtbot, monkeypatch, tmp_path: Path, load_answer):
    """Tests the full flow of creating and optionally loading the example dataset."""
    # 1. Setup
    grid = ImageGrid("", [], "dummy.txt")
    qtbot.addWidget(grid)

    # 2. Mock dependencies
    # Mock all dialogs to prevent them from blocking the test run
    monkeypatch.setattr(
        QFileDialog,
        'getExistingDirectory',
        lambda *args, **kwargs: str(tmp_path)
    )
    mock_info = Mock(return_value=QMessageBox.StandardButton.Ok)
    mock_question = Mock(return_value=load_answer)
    monkeypatch.setattr(QMessageBox, 'information', mock_info)
    monkeypatch.setattr(QMessageBox, 'question', mock_question)

    # The mocked create_example_dataset will return this path, using tmp_path
    # for a clean, isolated test environment.
    example_prefix = str(tmp_path / "testscene" / "scene1_")
    mock_create_dataset.return_value = (True, "Success!", example_prefix)

    # Mock the reload function to check if it's called
    grid._reload_grid = Mock()

    # 3. Action: Find and trigger the action from the menu
    # Find the action directly to avoid potential issues with menu object lifecycles in tests.
    create_action = next(a for a in grid.findChildren(QAction) if a.text() == "Create Example Dataset...")
    create_action.trigger()

    # 4. Assertions
    mock_info.assert_called_once()  # The first confirmation dialog
    mock_create_dataset.assert_called_once_with(tmp_path)
    mock_question.assert_called_once()  # The "load now?" dialog

    if load_answer == QMessageBox.StandardButton.Yes:
        assert grid.pre_path == example_prefix
        assert grid.suffix_file_path == str(Path(example_prefix).parent / "igridvu_suffix.txt")
        grid._reload_grid.assert_called_once()
    else:
        grid._reload_grid.assert_not_called()


def test_image_grid_pixel_info_out_of_bounds(tmp_path: Path, qtbot, create_dummy_image):
    """
    Tests that moving the mouse over a view updates pixel info labels correctly,
    displaying '-1' for views where the pixel is out of bounds.
    """
    # Create two images of different sizes
    img1_path = create_dummy_image(tmp_path, filename="1.png", width=10, height=10)
    img2_path = create_dummy_image(tmp_path, filename="2.png", width=5, height=5)
    suffixes = [img1_path.name, img2_path.name]
    grid = ImageGrid(str(tmp_path), suffixes, suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)
    grid.show()

    view1, view2 = grid.views

    # Mock get_color_at for both views
    # For view1 (larger image), return a color for an in-bounds pixel
    view1.get_color_at = Mock(return_value=QColor(10, 20, 30))
    # For view2 (smaller image), return None for the same scene_pos (out of bounds)
    view2.get_color_at = Mock(return_value=None)

    # Mock set_pixel_info for both views to check their calls
    view1.set_pixel_info = Mock()
    view2.set_pixel_info = Mock()

    # Simulate mouse moving over view1 at a scene position that is in-bounds for view1
    # but out-of-bounds for view2
    scene_pos = QPointF(7, 7) # This pixel is within 10x10 but outside 5x5
    view1.mouseMovedAtScenePos.emit(scene_pos)

    # Check that pixel info labels are updated correctly
    # view1 should show the color
    view1.set_pixel_info.assert_called_with("(7,7) (10,20,30,255)")
    # view2 should show -1 because get_color_at returned None
    view2.set_pixel_info.assert_called_with("(7,7) -1")

    # Check status bar (should show path of the sender view)
    assert grid.statusBar().currentMessage() == f"Path: {view1.img_path}"
