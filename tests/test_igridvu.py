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
import pytest # type: ignore
from PySide6.QtGui import QImage, QColor, QWheelEvent, qRgb
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtWidgets import QApplication, QGraphicsTextItem, QGridLayout
from PySide6.QtTest import QTest
import random
from unittest.mock import Mock

# The `pytest-qt` plugin provides the `qtbot` fixture, which is used
# to control and test PyQt widgets.
from src.igridvu import ImageGrid, ZoomableView


def create_dummy_image(path, width=1, height=1, filename="test.png"):
    """Creates a minimal, valid PNG image with random pixel data for tests."""
    img_path = path / filename
    print(f"Creating dummy image at: {img_path}")  # Debug statement
    image = QImage(width, height, QImage.Format_ARGB32)
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


def test_view_corrupted_image(tmp_path: Path, qtbot):
    """Tests the error message for a file that is a corrupted image."""
    corrupted_file = tmp_path / "corrupted.png"
    # Valid PNG header, but followed by junk data instead of valid IHDR chunk
    corrupted_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'junk' * 10)

    view = ZoomableView(str(corrupted_file), "test_label")
    qtbot.addWidget(view)

    assert view._pixmap_item is None
    scene_text = get_scene_text(view)
    assert "Cannot load" in scene_text
    assert "(Corrupted?)" in scene_text


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


def test_image_grid_directory_prefix(tmp_path: Path, qtbot):
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

    grid = ImageGrid(pre_path, suffixes)
    qtbot.addWidget(grid)

    assert grid.views[0].img_path == str(expected_path)

def test_zoomable_view_emits_signal_on_zoom(tmp_path: Path, qtbot):
    """Tests that wheel events on ZoomableView trigger the viewRectChanged signal."""
    img_path = create_dummy_image(tmp_path, width=200, height=200)
    view = ZoomableView(str(img_path), "test_label")
    qtbot.addWidget(view)
    view.show()  # The view needs to be shown to have a valid viewport

    with qtbot.waitSignal(view.viewRectChanged, timeout=1000) as blocker:
        # Simulate a zoom-in wheel event
        wheel_event = QWheelEvent(
            QPointF(50, 50),  # position
            QPointF(50, 50),  # globalPosition
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


def test_image_grid_status_bar_hover(tmp_path: Path, qtbot):
    """Tests that hovering over a view updates the status bar."""
    img_path = create_dummy_image(tmp_path)
    grid = ImageGrid(str(img_path.parent), [img_path.name + "\n"])
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


def test_image_grid_status_bar_pixel_info(tmp_path: Path, qtbot):
    """Tests that moving the mouse over a view updates the status bar with pixel info."""
    # Create two images to test synchronization of pixel info
    img1_path = create_dummy_image(tmp_path, filename="1.png")
    img2_path = create_dummy_image(tmp_path, filename="2.png")
    suffixes = [img1_path.name + "\n", img2_path.name + "\n"]
    grid = ImageGrid(str(tmp_path), suffixes)
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


def test_view_aspect_ratio_methods(tmp_path: Path, qtbot):
    """Tests the aspect-ratio-related methods like heightForWidth and sizeHint."""
    # 1. Test with a valid image (aspect ratio 2:1)
    img_path = create_dummy_image(tmp_path, width=200, height=100)
    view_with_image = ZoomableView(str(img_path), "test")
    qtbot.addWidget(view_with_image)

    assert view_with_image.hasHeightForWidth() is True, "Should have height for width with an image"
    # For a width of 300, height should be 150 to maintain 2:1 ratio
    assert view_with_image.heightForWidth(300) == 150, "heightForWidth should respect aspect ratio"

    hint = view_with_image.sizeHint()
    # sizeHint should also respect the aspect ratio
    assert hint.width() / hint.height() == pytest.approx(2.0)

    # 2. Test with no image (e.g., file not found)
    view_no_image = ZoomableView("nonexistent.png", "test")
    qtbot.addWidget(view_no_image)

    assert view_no_image.hasHeightForWidth() is False, "Should not have height for width without an image"
    # It should fall back to the superclass implementation which returns -1
    assert view_no_image.heightForWidth(300) == -1


def test_view_get_color_at(tmp_path: Path, qtbot):
    """Tests the get_color_at method for coordinates inside and outside the image."""
    img_path = tmp_path / "specific.png"
    image = QImage(2, 2, QImage.Format_ARGB32)
    # Fill the image with a known background color to avoid uninitialized data issues.
    image.fill(Qt.transparent)
    # Use a specific, known color for easy assertion
    red = QColor("red")
    image.setPixelColor(0, 0, red)
    image.save(str(img_path))

    view = ZoomableView(str(img_path), "test")
    qtbot.addWidget(view)
    view.show()
    # Wait for the view to be shown and for the automatic fitInView to complete.
    qtbot.waitActive(view)
    # Reset the transform to identity. The automatic fitInView can cause extreme
    # scaling for a tiny test image, leading to floating-point inaccuracies when
    # mapping coordinates. By resetting, scene coords become equivalent to item coords.
    view.resetTransform()

    # We test a coordinate within the pixel we colored at (0, 0). 
    # Note (0.5,0.5) somehow fails. It might be due to rounding up to (1, 1)
    color = view.get_color_at(QPointF(.499, .499))
    assert color is not None
    assert color.red() == red.red()
    assert color.green() == red.green()
    assert color.blue() == red.blue()

    # Test a point outside the image bounds
    assert view.get_color_at(QPointF(10, 10)) is None, "Should return None for out-of-bounds coordinate"
    assert view.get_color_at(QPointF(-1, -1)) is None, "Should return None for negative coordinate"


def test_view_panning_emits_signal(tmp_path: Path, qtbot):
    """Tests that panning the view via mouse drag emits the viewRectChanged signal."""
    # Create an image larger than the default view size to ensure scrollbars are active
    img_path = create_dummy_image(tmp_path, width=400, height=400)
    view = ZoomableView(str(img_path), "test_label")
    qtbot.addWidget(view)
    view.resize(200, 200)  # Set a small view size
    view.show()
    qtbot.waitActive(view)  # Ensure it's fully loaded and shown

    # The showEvent automatically fits the image. We must zoom in
    # to make the image larger than the view, which enables panning.
    view.scale(2.0, 2.0)
    qtbot.wait(50)  # Give a moment for the UI to process the scaling

    # Pan the view by dragging from center to top-left
    with qtbot.waitSignal(view.viewRectChanged, timeout=1000) as blocker:
        start_pos = view.viewport().rect().center()
        end_pos = QPoint(10, 10)
        qtbot.mousePress(view.viewport(), Qt.LeftButton, pos=start_pos)
        qtbot.mouseMove(view.viewport(), pos=end_pos)
        qtbot.mouseRelease(view.viewport(), Qt.LeftButton, pos=end_pos)

    assert blocker.signal_triggered, "viewRectChanged signal should be emitted on pan"
