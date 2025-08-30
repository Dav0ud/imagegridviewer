# -*- coding: utf-8 -*-
"""
A simple script to generate the placeholder images used in the README.md example.
This helps make the project runnable out-of-the-box.

Run this script from your terminal:
  python3 create_example_images.py
"""
import os
import sys

# Define the prefix and suffixes from the README
SUBDIR = "testscene"
PREFIX = os.path.join(SUBDIR, "scene1_")
# This order is chosen to represent a logical rendering or decomposition pipeline.
SUFFIXES = ["geometry.png", "texture.png", "diffuse.png", "specular.png", "fresnel.png", "shadow.png"]
WIDTH, HEIGHT = 256, 256
SUFFIX_FILENAME = os.path.join(SUBDIR, "igridvu_suffix.txt")

# Define some distinct colors for each image type
COLORS = {
    "geometry.png": (150, 220, 150),  # A soft green
    "texture.png": (128, 128, 128),   # A neutral gray
    "diffuse.png": (210, 200, 190),   # A beige/tan color
    "specular.png": (245, 245, 255),  # A bright, slightly cool white
    "fresnel.png": (200, 255, 255),   # A light cyan
    "shadow.png": (40, 40, 60)        # A dark, cool gray
}

def create_images():
    """Generates the dummy images."""
    from PySide6.QtGui import QImage, qRgb, QPainter, QFont, QColor
    from PySide6.QtCore import Qt

    # Create subdirectory if it doesn't exist
    os.makedirs(SUBDIR, exist_ok=True)
    print(f"Ensured subdirectory '{SUBDIR}' exists.")
    print("Creating dummy image files for the README example...")
    for suffix in SUFFIXES:
        filename = f"{PREFIX}{suffix}"
        image = QImage(WIDTH, HEIGHT, QImage.Format_RGB32)

        # Fill the image with a solid color
        r, g, b = COLORS.get(suffix, (0, 0, 0))  # Default to black
        image.fill(qRgb(r, g, b))

        # Add a watermark to make zoom/pan more obvious
        painter = QPainter(image)
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))  # Black color
        painter.drawText(image.rect(), Qt.AlignCenter, "Test Scene")
        painter.end()

        if image.save(filename):
            print(f"  -> Created '{filename}'")
        else:
            print(f"  -> Failed to create '{filename}'")

def create_suffix_file():
    """Creates the igridvu_suffix.txt file from the SUFFIXES list."""
    print(f"\nCreating suffix file '{SUFFIX_FILENAME}'...")
    try:
        with open(SUFFIX_FILENAME, 'w', encoding='utf-8') as f:
            # Write each suffix followed by a newline
            f.write("\n".join(SUFFIXES) + "\n")
        print(f"  -> Successfully created '{SUFFIX_FILENAME}'")
    except IOError as e:
        print(f"  -> ERROR: Failed to create '{SUFFIX_FILENAME}': {e}")

if __name__ == "__main__":
    # A QApplication instance is required to use GUI classes like QImage and QPainter,
    # even in a command-line script. This prevents "quit unexpectedly" errors on some OSes.
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)

    create_images()
    create_suffix_file()
    print(f"\nSetup complete. Example images are in '{SUBDIR}/'.")
    print(f"You can now run the example from the README: python3 src/igridvu.py {PREFIX}")