# -*- coding: utf-8 -*-
"""
Unit tests for the Image Grid Viewer application.

To run these tests, you need to install pytest and pytest-qt:
  pip install pytest pytest-qt

Then, from the command line in the project directory, run:
  python3 -m pytest

This file contains tests for:

ZoomableView widget handling a valid image.
ZoomableView widget handling a non-existent image.
ZoomableView widget handling a file with no read permissions.
ZoomableView widget handling a file that exceeds the size limit.
ZoomableView widget gracefully handling a missing image.
ImageGrid creating the correct number of ZoomableView widgets.
ImageGrid placing widgets correctly in the grid layout.
ImageGrid handling suffixes with leading spaces.
ImageGrid using a custom number of columns for the layout.
ImageGrid synchronizing zoom and pan across all views.
"""
import os
from pathlib import Path
import pytest
from PySide6.QtGui import QImage, QColor, QWheelEvent, qRgb
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication, QGraphicsTextItem, QGridLayout
from PySide6.QtTest import QTest
import random
from unittest.mock import Mock

# The `pytest-qt` plugin provides the `qtbot` fixture, which is used
# to control and test PyQt widgets.
from igridvu import ImageGrid, ZoomableView


def create_dummy_image(path, width=1, height=1, filename="test.png"):
    """Creates a minimal, valid PNG image with random pixel data for tests."""
    img_path = path / filename
    print(f"Creating dummy image at: {img_path}")  # Debug statement
    image = QImage(width, height, QImage.Format_RGB32)
    for x in range(width):
        for y in range(height):
            image.setPixel(x, y, qRgb(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    image.save(str(img_path))
    return img_path


def test_view_with_valid_image(tmp_path: Path, qtbot):
    """
    Tests that a ZoomableView widget correctly loads a valid image and stores its label.
    """
    # Create a minimal, valid 1x1 pixel PNG image for the test
    img_path = create_dummy_image(tmp_path)
    label = "test_image"

    # Create the view and check its state
    view = ZoomableView(str(img_path), label)
    qtbot.addWidget(view)

    assert view.label_text == label, "The label text should be stored correctly"

    # Check that a pixmap item was created and no text items exist in the scene
    assert view._pixmap_item is not None, "Pixmap item should be created for a valid image"
    assert get_scene_text(view) == "", "Scene should not contain any error text for a valid image"

    

def get_scene_text(view):
    """Helper to extract text from the first QGraphicsTextItem in a scene."""
    text_items = [item for item in view._scene.items() if isinstance(item, QGraphicsTextItem)]
    return text_items[0].toPlainText() if text_items else ""


def test_view_file_not_found(qtbot):
    """
    Tests that a ZoomableView widget handles a non-existent image path gracefully
    by displaying an error message.
    """
    invalid_path = "non_existent_dir/non_existent_image.jpg"
    view = ZoomableView(invalid_path, "test_label")
    qtbot.addWidget(view)

    assert view._pixmap_item is None, "Pixmap item should be null for a non-existent path"
    scene_text = get_scene_text(view)
    assert "Not found" in scene_text, "Error message should indicate file not found"
    assert "non_existent_image.jpg" in scene_text, "Error message should include the filename"


def test_view_permission_denied(tmp_path: Path, qtbot):
    """Tests the error message for a file with no read permissions."""
    img_path = create_dummy_image(tmp_path)
    # Make the file unreadable
    os.chmod(str(img_path), 0o000)

    # On Windows, os.chmod doesn't prevent reading by the owner. Skip test if so.
    if os.access(str(img_path), os.R_OK):
        pytest.skip("os.chmod has no effect on read permissions on this system (e.g., Windows)")

    view = ZoomableView(str(img_path), "test_label")
    qtbot.addWidget(view)

    assert view._pixmap_item is None
    scene_text = get_scene_text(view)
    assert "Permission" in scene_text
    assert "denied" in scene_text

    # Clean up by making it writable again so it can be deleted
    os.chmod(str(img_path), 0o644)


def test_view_file_too_large(tmp_path: Path, qtbot, monkeypatch: pytest.MonkeyPatch):
    """Tests the error message for a file that exceeds the size limit."""
    # Patch the max size to a small value for the test
    monkeypatch.setattr(ZoomableView, "MAX_FILE_SIZE_BYTES", 10)

    # Create a file larger than the patched limit
    large_file_path = tmp_path / "large_file.txt"
    large_file_path.write_text("This file is definitely larger than 10 bytes")

    view = ZoomableView(str(large_file_path), "test_label")
    qtbot.addWidget(view)

    assert view._pixmap_item is None
    assert "File too large" in get_scene_text(view)


def test_view_dimensions_too_large(tmp_path: Path, qtbot, monkeypatch: pytest.MonkeyPatch):
    """Tests the error message for an image with dimensions exceeding the limit."""
    monkeypatch.setattr(ZoomableView, "MAX_IMAGE_DIMENSION", 5)
    img_path = create_dummy_image(tmp_path, width=10, height=10)

    view = ZoomableView(str(img_path), "test_label")
    qtbot.addWidget(view)

    assert view._pixmap_item is None
    scene_text = get_scene_text(view)
    assert "Dimensions too large" in scene_text
    assert "(10x10)" in scene_text


def test_view_unrecognized_format(tmp_path: Path, qtbot):
    """Tests the error message for a file that is not a valid image format."""
    fake_image_path = tmp_path / "not_an_image.png"
    fake_image_path.write_text("this is just a text file")

    view = ZoomableView(str(fake_image_path), "test_label")
    qtbot.addWidget(view)

    assert view._pixmap_item is None
    scene_text = get_scene_text(view)
    assert "Unrecognized" in scene_text
    assert "format" in scene_text


def test_image_grid_widget_creation(qtbot):
    """Tests that ImageGrid creates the correct number of ZoomableView widgets."""
    pre_path = "test_image_"
    suffixes = ["1.png\n", "2.png\n", "3.png\n"]

    grid = ImageGrid(pre_path, suffixes)
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
    grid = ImageGrid("test_prefix_", suffixes)
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
    grid = ImageGrid("test_prefix_", suffixes, columns=2)
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
    grid = ImageGrid(pre_path, suffixes)
    qtbot.addWidget(grid)

    views = grid.findChildren(ZoomableView)
    # The path passed to the ZoomableView should have the space preserved
    assert views[0].img_path == "test_image 1.png"


def test_zoomable_view_emits_signal_on_zoom(tmp_path: Path, qtbot):
    """Tests that wheel events on ZoomableView trigger the viewRectChanged signal."""
    img_path = create_dummy_image(tmp_path, width=200, height=200)
    view = ZoomableView(str(img_path), "test_label")
    qtbot.addWidget(view)
    view.show()  # The view needs to be shown to have a valid viewport

    with qtbot.waitSignal(view.viewRectChanged, timeout=1000) as blocker:
        # Simulate a zoom-in wheel event
        wheel_event = QWheelEvent(
            QPoint(50, 50),  # pos
            QPoint(50, 50),  # globalPos
            QPoint(0, 0),    # pixelDelta
            QPoint(0, 120),  # angleDelta
            Qt.NoButton,
            Qt.NoModifier,
            Qt.NoScrollPhase,
            False  # inverted
        )
        QApplication.sendEvent(view.viewport(), wheel_event)

    assert blocker.signal_triggered, "viewRectChanged signal should be emitted on wheel event"


def test_image_grid_synchronizes_views(tmp_path: Path, qtbot):
    """
    Tests that changing one view in the ImageGrid synchronizes all other views
    by calling their setViewRect method.
    """
    # Create two dummy images in the temp path
    img1 = create_dummy_image(tmp_path, filename="1.png", width=200, height=200)
    img2 = create_dummy_image(tmp_path, filename="2.png", width=200, height=200)
    print(f"Created images: {img1}, {img2}")  # Debug statement

    suffixes = ["1.png\n", "2.png\n"]
    grid = ImageGrid(str(tmp_path), suffixes)
    qtbot.addWidget(grid)
    grid.show()
    qtbot.waitActive(grid)

    # Get the views from the grid
    view1, view2 = grid.views
    print(f"View1 path: {view1.img_path}, View2 path: {view2.img_path}")  # Debug statement

    # Mock the setViewRect method on the second view
    view2.setViewRect = Mock()

    # Simulate a zoom-in wheel event on the first view's viewport
    viewport = view1.viewport()
    center_pos = QPoint(viewport.width() // 2, viewport.height() // 2)
    # Use NoScrollPhase for a single, discrete wheel event.
    wheel_event = QWheelEvent(
        center_pos, view1.mapToGlobal(center_pos), QPoint(0, 0),
        QPoint(0, 120), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False
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
