# Image Grid Viewer

[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight, Python-based desktop tool for displaying a grid of images. It is designed to help researchers and developers quickly visualize and compare multiple images—such as different modalities of a scene or outputs of an algorithm—in a single, synchronized window.

![Image Grid Viewer Screenshot](https://via.placeholder.com/800x450.png?text=App+Screenshot+or+GIF+Here)
*(A screenshot or GIF of the application in action would be great here!)*

---

## Key Features

-   **Synchronized Grid:** Display multiple images in a scrollable grid. Zooming and panning are synchronized across all images for precise, pixel-level comparison.
-   **Synchronized Pixel Inspector:** Move your cursor over any image to see the pixel coordinates and RGB values for that location across *all* images in the grid, displayed live in the status bar.
-   **Persistent Labels:** Each image view is overlaid with a clear, non-zooming label derived from its filename, so you always know which modality you're looking at.
-   **Customizable Layout:** Easily adjust the number of grid columns via a command-line argument.
-   **Robust Error Handling:** Gracefully handles common issues like missing files, permission errors, and unsupported formats by displaying an informative message in the respective grid cell without crashing.
-   **Simple CLI:** Launch the viewer directly from your terminal with a straightforward command-line interface.

---

## Requirements

- Python 3.6 or higher
- PySide6

For development and running tests, you will also need:
- `pytest`
- `pytest-qt`

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Dav0ud/imagegridviewer.git
   cd imagegridviewer
   ```

2. Create and activate a virtual environment (recommended):
    ```bash
    # For Unix/macOS
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    venv\Scripts\activate
    ```

3. Install the required dependencies:
    ```bash
    # Install runtime dependencies (PySide6)
    pip install -r requirements.txt
    ```

4. For development or running tests, install the development dependencies:
    ```bash
    # Install development dependencies (pytest, pytest-qt)
    pip install -r requirements-dev.txt
    ```

---

## Usage

Run the application from the root of the project directory. Provide a prefix for the image files and, optionally, a file containing the suffixes.

    ```bash
    python3 -m src.igridvu.cli <image_prefix> [suffix_file] [--columns N]
    ```

### Arguments:
*   `image_prefix`: The common prefix for the image files. This can be just a name prefix (e.g., `image_`) or include a path (e.g., `path/to/my_data/run_1_`).
*   `suffix_file`: (Optional) A text file containing image suffixes, one per line. Defaults to `igridvu_suffix.txt` located in the same directory as the `image_prefix`. If `image_prefix` has no path, it looks in the current directory.
*   `--columns N`, `-c N`: (Optional) Sets the number of columns in the grid. Defaults to 4.

### Example:

Imagine you have images representing different illumination components of a scene, all located in a `testscene` directory: `testscene/scene1_diffuse.png`, `testscene/scene1_specular.png`, etc.

1.  Your suffix file (`igridvu_suffix.txt`) lists the component names:
    ```text
    diffuse.png
    specular.png
    shadow.png
    ...
    ```

2.  Run the viewer, providing the path and common prefix:
    ```bash
    # The prefix now includes the directory path
    python3 -m src.igridvu.cli testscene/scene1_

    # Display in a 3-column grid
    python3 -m src.igridvu.cli testscene/scene1_ --columns 3
    ```

### Interaction

-   **Zoom:** Use the mouse wheel to zoom in and out. The view zooms towards your cursor.
-   **Pan:** Left-click and drag to pan the images.
-   **Inspect Pixels:** Move the mouse over an image. The status bar will display:
    -   The full path of the image under the cursor.
    -   The scene coordinates `(x, y)`.
    -   The RGB values at that coordinate for **every image** in the grid, identified by its label.

---

## Testing

This project uses `pytest`. To run the test suite, first install the development dependencies and then run pytest.

    ```bash
    # Make sure you have installed development dependencies (see Installation)
    python3 -m pytest
    ```

---

## File Structure
- `src/igridvu/`: The main application package.
  - `cli.py`: The command-line entry point.
  - `main_window.py`: Defines the main `QMainWindow`, orchestrates the grid layout, and handles view synchronization and status bar updates.
  - `zoomable_view.py`: Defines the custom `QGraphicsView` widget responsible for loading, displaying, and interacting with a single image (zoom, pan, pixel inspection).
- `scripts/`: Helper scripts for development.
- `requirements.txt`: Runtime dependencies for the application.
- `requirements-dev.txt`: Development and testing dependencies.
- `tests/`: Unit and integration tests.
- `README.md`: This documentation file.

The viewer uses PySide6's `QPixmap` to load images, which supports most common image formats (PNG, JPEG, BMP, GIF, etc.).

---

## Future Vision

This tool is designed for **comparative analysis**. Future development could include powerful features for these workflows:

*   **Image Difference Mode:** Select two images to overlay them with transparency or view a computed "visual diff" that highlights changes.
*   **Metadata Integration:** Display key information from filenames (e.g., timestep, parameters) or EXIF data directly in the UI.

---

## Troubleshooting
The application will attempt to display an error message directly within the grid cell if an image cannot be loaded. Common messages include:

-   `Not found`: The file path constructed from the prefix and suffix does not exist.
-   `Permission denied`: The application does not have the necessary rights to read the image file.
-   `File too large` / `Dimensions too large`: The image exceeds internal safety limits to prevent excessive memory usage.
-   `Unrecognized format` / `Cannot load`: The file is not a valid or supported image format, or it may be corrupted.

If images are not displaying correctly, first check the status bar by hovering over the cell to confirm the expected file path is correct.

---

## Author
Davoud Shahlaei

This project was created to help evaluate algorithm outputs and as a learning exercise in Python and PyQt (now switched to PySide6). Feedback and contributions are welcome!
