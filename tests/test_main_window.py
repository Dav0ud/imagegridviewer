# -*- coding: utf-8 -*-
"""
Unit and integration tests for the ImageGrid main window from src/igridvu/main_window.py.

To run these tests, you need to install pytest and pytest-qt:
  pip install pytest pytest-qt

Then, from the command line in the project directory, run:
  python3 -m pytest
"""
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest
from PySide6.QtCore import Qt, QPoint, QPointF, QStandardPaths
from PySide6.QtGui import QColor, QWheelEvent
from PySide6.QtWidgets import QApplication, QGridLayout, QFileDialog

from igridvu import ImageGrid, ZoomableView


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
    suffixes = [f"{i}.png\n" for i in range(1, 6)]
    # Uses default columns=4
    grid = ImageGrid("test_prefix_", suffixes, suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)

    # The central widget's layout (QVBoxLayout) contains a container widget
    # for the grid. We need to get the QGridLayout from that container.
    main_layout = grid.centralWidget().layout()
    grid_container = main_layout.itemAt(0).widget()
    layout = grid_container.layout()
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
    suffixes = [f"{i}.png\n" for i in range(1, 4)]  # 1.png, 2.png, 3.png
    # Set columns to 2
    grid = ImageGrid("test_prefix_", suffixes, suffix_file_path="dummy.txt", columns=2)
    qtbot.addWidget(grid)

    # The central widget's layout (QVBoxLayout) contains a container widget
    # for the grid. We need to get the QGridLayout from that container.
    main_layout = grid.centralWidget().layout()
    grid_container = main_layout.itemAt(0).widget()
    layout = grid_container.layout()
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
    suffixes = [" 1.png\n"]
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
    suffixes = ["image.png\n"]
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

    suffixes = ["1.png\n", "2.png\n"]
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
    grid = ImageGrid(str(img_path.parent), [img_path.name + "\n"], suffix_file_path="dummy.txt")
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


def test_image_grid_status_bar_pixel_info(tmp_path: Path, qtbot, create_dummy_image):
    """Tests that moving the mouse over a view updates the status bar with pixel info."""
    # Create two images to test synchronization of pixel info
    img1_path = create_dummy_image(tmp_path, filename="1.png")
    img2_path = create_dummy_image(tmp_path, filename="2.png")
    suffixes = [img1_path.name + "\n", img2_path.name + "\n"]
    grid = ImageGrid(str(tmp_path), suffixes, suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)
    grid.show()

    view1, view2 = grid.views
    status_bar = grid.statusBar()

    # Mock the color-fetching method on both views
    view1.get_color_at = Mock(return_value=QColor(10, 20, 30))
    view2.get_color_at = Mock(return_value=QColor(40, 50, 60))

    # Simulate mouse moving over view1
    scene_pos = QPointF(5, 15)
    view1.mouseMovedAtScenePos.emit(scene_pos)

    # Check that the status bar shows combined pixel info from both views
    expected_msg = (
        f"Path: {view1.img_path}  Coords: (5, 15)  |  "
        f"{view1.label_text}: (10,20,30) | {view2.label_text}: (40,50,60)"
    )
    assert status_bar.currentMessage() == expected_msg
    view1.get_color_at.assert_called_with(scene_pos)
    view2.get_color_at.assert_called_with(scene_pos)

    # Test fallback behavior when the cursor is not over a valid pixel
    view1.get_color_at.return_value = None
    view1.mouseMovedAtScenePos.emit(scene_pos)

    # The status bar should fall back to showing just the path
    assert status_bar.currentMessage() == f"Path: {view1.img_path}"

    # Test behavior when one view has color and another doesn't (e.g., cursor out of bounds)
    view1.get_color_at.return_value = QColor(10, 20, 30)
    view2.get_color_at.return_value = None
    view1.mouseMovedAtScenePos.emit(scene_pos)
    expected_msg_partial = (
        f"Path: {view1.img_path}  Coords: (5, 15)  |  "
        f"{view1.label_text}: (10,20,30) | {view2.label_text}: ---"
    )
    assert status_bar.currentMessage() == expected_msg_partial


def test_image_grid_empty_suffixes(qtbot):
    """Tests that ImageGrid handles an empty list of suffixes gracefully."""
    grid = ImageGrid("pre_path", [], suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)
    views = grid.findChildren(ZoomableView)
    assert len(views) == 0
    # Check that the status bar shows the default message
    assert grid.statusBar().currentMessage() == grid.status_message


def test_image_grid_window_title(qtbot):
    """Tests that the ImageGrid window has an appropriate title."""
    pre_path = "/some/test/directory/prefix_"
    grid = ImageGrid(pre_path, [], suffix_file_path="dummy.txt")
    qtbot.addWidget(grid)

    # Assuming the title should contain the app name and the prefix path
    assert "Image Grid Viewer" in grid.windowTitle()
    assert pre_path in grid.windowTitle()


def test_image_grid_view_labels(qtbot):
    """Tests that the labels for each view are set correctly from the suffixes."""
    pre_path = "prefix_"
    suffixes = ["a.png\n", "b.png\n"]
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
    grid = ImageGrid("pre_path", ["a.png\n"], suffix_file_path="dummy.txt")
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