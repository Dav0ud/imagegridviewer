# -*- coding: utf-8 -*-
"""
A simple module to generate the placeholder images for the example test scene.
This helps make the project runnable out-of-the-box.
"""
import os
from pathlib import Path

# Define the prefix and suffixes from the README
SUBDIR = "testscene"
# This order is chosen to represent a logical rendering or decomposition pipeline.
SUFFIXES = [
    "geometry.png",
    "texture.png",
    "diffuse.png",
    "specular.png",
    "fresnel.png",
    "shadow.png",
]
WIDTH, HEIGHT = 256, 256

# Define some distinct colors for each image type
COLORS = {
    "geometry.png": (150, 220, 150),  # A soft green
    "texture.png": (128, 128, 128),  # A neutral gray
    "diffuse.png": (210, 200, 190),  # A beige/tan color
    "specular.png": (245, 245, 255),  # A bright, slightly cool white
    "fresnel.png": (200, 255, 255),  # A light cyan
    "shadow.png": (40, 40, 60),  # A dark, cool gray
}


def create_example_dataset(base_dir: Path) -> tuple[bool, str, str]:
    """
    Generates the dummy images and suffix file in a 'testscene' subdirectory
    of the given base directory.

    Args:
        base_dir: The directory in which to create the 'testscene' folder.

    Returns:
        A tuple containing:
        - bool: True on success, False on failure.
        - str: A message detailing the outcome.
        - str: The prefix path to use with igridvu on success, else an empty string.
    """
    # PySide6 is imported here to avoid making it a hard dependency for other parts.
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QFont, QImage, QPainter, qRgb

    scene_dir = base_dir / SUBDIR
    prefix_path = scene_dir / "scene1_"
    suffix_filename = scene_dir / "igridvu_suffix.txt"

    try:
        os.makedirs(scene_dir, exist_ok=True)

        for suffix in SUFFIXES:
            filename = f"{prefix_path}{suffix}"
            image = QImage(WIDTH, HEIGHT, QImage.Format_RGB32)
            r, g, b = COLORS.get(suffix, (0, 0, 0))
            image.fill(qRgb(r, g, b))
            painter = QPainter(image)
            font = QFont()
            font.setPointSize(24)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(image.rect(), Qt.AlignCenter, "Test Scene")
            painter.end()
            if not image.save(str(filename)):
                raise IOError(f"Failed to save image '{filename}'")

        with open(suffix_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(SUFFIXES) + "\n")

        message = f"Successfully created example dataset in:\n{scene_dir}"
        return True, message, str(prefix_path)

    except (IOError, OSError) as e:
        message = f"Error creating example dataset: {e}"
        return False, message, ""