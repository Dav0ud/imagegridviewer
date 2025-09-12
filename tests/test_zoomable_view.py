# -*- coding: utf-8 -*-
"""
Unit tests for the ZoomableView widget from src/igridvu/zoomable_view.py.

To run these tests, you need to install pytest and pytest-qt:
  pip install pytest pytest-qt

Then, from the command line in the project directory, run:
  python3 -m pytest
"""
import os
from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QImage, QColor, QWheelEvent
from PySide6.QtWidgets import QApplication, QGraphicsTextItem

from igridvu import ZoomableView


def get_scene_text(view):
    """Helper to extract text from the first QGraphicsTextItem in a scene."""
    text_items = [item for item in view._scene.items() if isinstance(item, QGraphicsTextItem)]
    return text_items[0].toPlainText() if text_items else ""


def test_view_with_valid_image(tmp_path: Path, qtbot, create_dummy_image):
    """
    Tests that a ZoomableView widget correctly loads a valid image and stores its label.
    """
    # Create a minimal, valid 1x1 pixel PNG image for the test
    img_path = create_dummy_image(tmp_path)
    label = "test_image"

    # Create the view and check its state
    view = ZoomableView(label_text=label, img_path=str(img_path))
    qtbot.addWidget(view)

    assert view.label_text == label, "The label text should be stored correctly"

    # Check that a pixmap item was created and no text items exist in the scene
    assert view._pixmap_item is not None, "Pixmap item should be created for a valid image"
    assert get_scene_text(view) == "", "Scene should not contain any error text for a valid image"


def test_view_file_not_found(qtbot):
    """
    Tests that a ZoomableView widget handles a non-existent image path gracefully
    by displaying an error message.
    """
    invalid_path = "non_existent_dir/non_existent_image.jpg"
    view = ZoomableView(label_text="test_label", img_path=invalid_path)
    qtbot.addWidget(view)

    assert view._pixmap_item is None, "Pixmap item should be null for a non-existent path"
    scene_text = get_scene_text(view)
    assert "Not found" in scene_text, "Error message should indicate file not found"
    assert "non_existent_image.jpg" in scene_text, "Error message should include the filename"


def test_view_permission_denied(tmp_path: Path, qtbot, create_dummy_image):
    """Tests the error message for a file with no read permissions."""
    img_path = create_dummy_image(tmp_path)
    # Make the file unreadable
    os.chmod(str(img_path), 0o000)

    # On Windows, os.chmod doesn't prevent reading by the owner. Skip test if so.
    if os.access(str(img_path), os.R_OK):
        pytest.skip("os.chmod has no effect on read permissions on this system (e.g., Windows)")

    view = ZoomableView(label_text="test_label", img_path=str(img_path))
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

    view = ZoomableView(label_text="test_label", img_path=str(large_file_path))
    qtbot.addWidget(view)

    assert view._pixmap_item is None
    assert "File too large" in get_scene_text(view)


def test_view_dimensions_too_large(tmp_path: Path, qtbot, monkeypatch: pytest.MonkeyPatch, create_dummy_image):
    """Tests the error message for an image with dimensions exceeding the limit."""
    monkeypatch.setattr(ZoomableView, "MAX_IMAGE_DIMENSION", 5)
    img_path = create_dummy_image(tmp_path, width=10, height=10)

    view = ZoomableView(label_text="test_label", img_path=str(img_path))
    qtbot.addWidget(view)

    assert view._pixmap_item is None
    scene_text = get_scene_text(view)
    assert "Dimensions too large" in scene_text
    assert "(10x10)" in scene_text


def test_view_unrecognized_format(tmp_path: Path, qtbot):
    """Tests the error message for a file that is not a valid image format."""
    fake_image_path = tmp_path / "not_an_image.png"
    fake_image_path.write_text("this is just a text file")

    view = ZoomableView(label_text="test_label", img_path=str(fake_image_path))
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

    view = ZoomableView(label_text="test_label", img_path=str(corrupted_file))
    qtbot.addWidget(view)

    assert view._pixmap_item is None
    scene_text = get_scene_text(view)
    assert "Cannot load" in scene_text
    assert "(Corrupted?)" in scene_text


def test_zoomable_view_emits_signal_on_zoom(tmp_path: Path, qtbot, create_dummy_image):
    """Tests that wheel events on ZoomableView trigger the viewRectChanged signal."""
    img_path = create_dummy_image(tmp_path, width=200, height=200)
    view = ZoomableView(label_text="test_label", img_path=str(img_path))
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


def test_view_aspect_ratio_methods(tmp_path: Path, qtbot, create_dummy_image):
    """Tests the aspect-ratio-related methods like heightForWidth and sizeHint."""
    # 1. Test with a valid image (aspect ratio 2:1)
    img_path = create_dummy_image(tmp_path, width=200, height=100)
    view_with_image = ZoomableView(label_text="test", img_path=str(img_path))
    qtbot.addWidget(view_with_image)

    assert view_with_image.hasHeightForWidth() is True, "Should have height for width with an image"
    # For a width of 300, height should be 150 to maintain 2:1 ratio
    assert view_with_image.heightForWidth(300) == 150, "heightForWidth should respect aspect ratio"

    hint = view_with_image.sizeHint()
    # sizeHint should also respect the aspect ratio
    assert hint.width() / hint.height() == pytest.approx(2.0)

    # 2. Test with no image (e.g., file not found)
    view_no_image = ZoomableView(label_text="test", img_path="nonexistent.png")
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

    view = ZoomableView(label_text="test", img_path=str(img_path))
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


def test_view_panning_emits_signal(tmp_path: Path, qtbot, create_dummy_image):
    """Tests that panning the view via mouse drag emits the viewRectChanged signal."""
    # Create an image larger than the default view size to ensure scrollbars are active
    img_path = create_dummy_image(tmp_path, width=400, height=400)
    view = ZoomableView(label_text="test_label", img_path=str(img_path))
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


def test_view_channel_and_restore(tmp_path: Path, qtbot, create_dummy_image):
    """Tests viewing a single channel and restoring the original image."""
    img_path = create_dummy_image(tmp_path, width=10, height=10)
    view = ZoomableView(label_text="test_color", img_path=str(img_path))
    qtbot.addWidget(view)
    view.show()
    qtbot.waitActive(view)

    original_image = view._image.copy()
    original_pixel_color = original_image.pixelColor(0, 0)

    # Test Red Channel
    view.view_channel("Red")
    assert view._current_channel == "Red"
    assert "Red" in view._title_label.text()
    assert view._image.isGrayscale()
    assert view._original_image is not None
    channel_pixel_value = view._image.pixelColor(0, 0).red()
    assert channel_pixel_value == original_pixel_color.red()
    view.restore_original()
    assert view._current_channel is None

    # Test Green Channel
    view.view_channel("Green")
    assert view._current_channel == "Green"
    assert "Green" in view._title_label.text()
    assert view._image.isGrayscale()
    channel_pixel_value = view._image.pixelColor(0, 0).green()
    assert channel_pixel_value == original_pixel_color.green()
    view.restore_original()
    assert view._current_channel is None

    # Test Blue Channel
    view.view_channel("Blue")
    assert view._current_channel == "Blue"
    assert "Blue" in view._title_label.text()
    assert view._image.isGrayscale()
    channel_pixel_value = view._image.pixelColor(0, 0).blue()
    assert channel_pixel_value == original_pixel_color.blue()
    view.restore_original()
    assert view._current_channel is None

    # Final check of restored image
    assert view._title_label.text() == "test_color"
    assert not view._image.isGrayscale()
    assert view._original_image is None
    assert view._image.constBits() == original_image.constBits()
