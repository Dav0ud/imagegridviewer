# -*- coding: utf-8 -*-
"""
Configuration and fixtures for pytest.

This file makes the `create_dummy_image` helper function available to all tests
without needing to import it.
"""
import random
from pathlib import Path

import pytest
from PySide6.QtGui import QImage, qRgb


@pytest.fixture
def create_dummy_image():
    """A pytest fixture that returns a factory function for creating dummy images."""
    def _create_dummy_image(path: Path, width: int = 1, height: int = 1, filename: str = "test.png") -> Path:
        """Creates a minimal, valid PNG image with random pixel data for tests."""
        img_path = path / filename
        image = QImage(width, height, QImage.Format_ARGB32)
        for x in range(width):
            for y in range(height):
                image.setPixel(x, y, qRgb(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        image.save(str(img_path))
        return img_path

    return _create_dummy_image