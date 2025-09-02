# -*- coding: utf-8 -*-
"""
Unit tests for the example dataset creation utility.
"""
import os
from pathlib import Path

import pytest
from PySide6.QtGui import QImage

from igridvu.create_examples import (
    WIDTH,
    HEIGHT,
    SUBDIR,
    SUFFIXES,
    create_example_dataset,
)


def test_create_example_dataset_success(tmp_path: Path, qtbot):
    """
    Tests that create_example_dataset successfully creates the directory,
    images, and suffix file.
    """
    # 1. Action
    success, message, prefix_path_str = create_example_dataset(tmp_path)

    # 2. Assertions
    assert success is True
    assert "Successfully created" in message

    scene_dir = tmp_path / SUBDIR
    expected_prefix_path = scene_dir / "scene1_"
    assert prefix_path_str == str(expected_prefix_path)

    assert scene_dir.is_dir()

    # Check for suffix file
    suffix_file = scene_dir / "igridvu_suffix.txt"
    assert suffix_file.is_file()
    with open(suffix_file, "r", encoding="utf-8") as f:
        content = f.read()
        expected_content = "\n".join(SUFFIXES) + "\n"
        assert content == expected_content

    # Check for images
    for suffix in SUFFIXES:
        img_path_str = f"{prefix_path_str}{suffix}"
        img_path = Path(img_path_str)
        assert img_path.is_file(), f"Image file {img_path} was not created."

        # Verify image properties
        image = QImage(img_path_str)
        assert not image.isNull(), f"Image {img_path} is not a valid image."
        assert image.width() == WIDTH
        assert image.height() == HEIGHT


def test_create_example_dataset_io_error_on_save(tmp_path: Path, qtbot, monkeypatch):
    """
    Tests that create_example_dataset handles I/O errors during image save.
    """
    # 1. Setup: Mock QImage.save to always fail
    monkeypatch.setattr(QImage, "save", lambda *args, **kwargs: False)

    # 2. Action
    success, message, prefix_path = create_example_dataset(tmp_path)

    # 3. Assertions
    assert success is False
    assert "Error creating example dataset" in message
    assert "Failed to save image" in message
    assert prefix_path == ""


def test_create_example_dataset_permission_error_on_folder(tmp_path: Path, qtbot, monkeypatch):
    """
    Tests that create_example_dataset handles OSError during folder creation.
    """
    # 1. Setup: Mock Path.mkdir to raise an error
    def mock_mkdir(*args, **kwargs):
        raise OSError("Permission denied")
    monkeypatch.setattr(Path, "mkdir", mock_mkdir)
    # 2. Action
    success, message, prefix_path = create_example_dataset(tmp_path)
    # 3. Assertions
    assert success is False
    assert "Error creating example dataset: Permission denied" in message
    assert prefix_path == ""