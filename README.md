# Image Grid Viewer

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight, Python-based desktop tool for displaying a grid of images. It is designed to help researchers and developers quickly visualize and compare multiple images—such as different modalities of a scene or outputs of an algorithm—in a single, synchronized window.

![Image Grid Viewer Screenshot](assets/app_screenshot.png)
*(A screenshot of the application in action.)*

---

## Key Features

-   **Synchronized Grid:** Display multiple images in a scrollable grid. Zooming and panning are synchronized across all images for precise, pixel-level comparison.
-   **Synchronized Pixel Inspector:** Move your cursor over any image to see the pixel coordinates and RGB/RGBA values for that location across *all* images in the grid. For pixels outside an image's bounds, "-1" is displayed.
-   **Channel Viewing:** Isolate and view individual Red, Green, Blue, or Alpha channels of an image for detailed analysis.
-   **Persistent Labels:** Each image view is overlaid with a clear, non-zooming label derived from its filename, ensuring easy identification.
-   **Customizable Layout:** Adjust the number of grid columns via the `--columns` argument.
-   **Robust Error Handling:** Gracefully handles common issues (missing files, permission errors, unsupported formats) by displaying informative messages directly in the grid cell.
-   **Simple CLI:** Launch the viewer directly from your terminal.

---

## Requirements

Dependencies are managed in `pyproject.toml` and handled automatically by installation commands.
-   **Runtime:** Python 3.8+, PySide6.
-   **Development:** pytest, pytest-qt (for testing).

---

## Installation

### Clone the Repository

   ```bash
   git clone https://github.com/Dav0ud/imagegridviewer.git
   cd imagegridviewer
   ```

### Setup

#### Automated Setup (Recommended)

Use the provided shell script for quick setup, virtual environment creation, dependency installation, and application launch.

**Note:** `.sh` scripts are for macOS/Linux. Windows users, see Manual Setup.

```bash
# Handles entire setup and run process:
bash scripts/setup_and_run.sh
```

Recommended for quick starts. For more control, see Manual Setup.

#### Manual Setup
1. Create and activate a virtual environment (recommended):
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    venv\Scripts\activate
    ```

2. Upgrade `pip` to the latest version within the virtual environment. This helps prevent potential installation issues.
   ```bash
   python -m pip install --upgrade pip
   ```

3. Install the project. For development, install it in "editable" mode (`-e`), which allows your code changes to be reflected immediately without reinstalling. The `[dev]` part includes testing dependencies like `pytest`.
```bash
# Install for development
pip install -e ".[dev]"
```
    
For regular use, you can install it normally:

```bash
pip install .
```

---

## Usage

After installation, run `igridvu` from your terminal.

### Starting with a Dataset

To load images directly:

```bash
igridvu <image_prefix> [suffix_file] [--columns N]
```

### Arguments:
*   `image_prefix`: Common prefix for image files (e.g., `image_` or `path/to/my_data/run_1_`).
*   `suffix_file`: (Optional) Text file with image suffixes, one per line. Defaults to `igridvu_suffix.txt` in the `image_prefix` directory (or current directory if no path).
*   `--columns N`, `-c N`: (Optional) Sets grid columns (default: 4).

### Example:
Imagine images like `testscene/scene1_diffuse.png`, `testscene/scene1_specular.png`.

1.  Create `igridvu_suffix.txt` in `testscene`:
    ```text
    diffuse.png
    specular.png
    shadow.png
    ...
    ```
2.  Run:
    ```bash
    igridvu testscene/scene1_
    ```
    For 3 columns:
    ```bash
    igridvu testscene/scene1_ --columns 3
    ```

### Starting Without Arguments (GUI First)

Running `igridvu` without arguments opens a welcome screen. From here, you can:
-   **Create Example Dataset...**: (Also in "Help" menu) Choose a directory to create a `testscene` folder with sample images. Recommended for seeing features in action.
-   **Open Suffix Editor...**: Create or edit a suffix file.
-   **Open Dataset...**: (Also in "File" menu) Open an image from an existing dataset.



### Interaction

-   **Zoom:** Mouse wheel zooms towards cursor.
-   **Pan:** Left-click and drag.
-   **Inspect Pixels:** Mouse over an image. Status bar shows:
    -   Full path of image under cursor.
    -   Scene coordinates `(x, y)`.
    -   RGB/RGBA values at that coordinate for **every image** in the grid, identified by its label.

---

## Architecture

The software architecture for this project is documented using the [C4 model](https://c4model.com/). The diagrams are defined as code using the Structurizr DSL, which allows them to be version-controlled alongside the source code.

-   **Source File:** `docs/c4_model.dsl`

### Viewing the Diagrams

The diagrams can be rendered by copying the contents of the `.dsl` file into the official, free **[Structurizr DSL online editor](https://structurizr.com/dsl)**.

---

## Building a Standalone Application (macOS)

Package as a standalone macOS `.app` bundle using PyInstaller for distribution without a separate Python install.

**Prerequisites:** Activated virtual environment with development dependencies (`pip install -e ".[dev]"`).

**Build Process:**

1.  **First build/regenerate config:**
    ```bash
    pyinstaller run_app.py --name igridvu --windowed --noconfirm
    ```

2.  **(Recommended) Subsequent builds (optimized):**
    ```bash
    pyinstaller igridvu.spec --noconfirm
    ```

3.  Find `dist/igridvu.app`. Drag to Applications folder.

---

## Testing

Uses `pytest`. Install in editable mode with `[dev]` extra, then run:

```bash
pytest
```

---

## Cleaning the Environment

Helper script removes generated files (`venv`, `build`, `dist`, caches, metadata).

To run:

```bash
chmod +x scripts/clean.sh
./scripts/clean.sh
```

---

## File Structure
- `pyproject.toml`: Project metadata, dependencies, entry points.
- `src/igridvu/`: Main application source code.
- `docs/`: Contains architecture diagrams and documentation.
- `pytest.ini`: `pytest` configuration.
  - `cli.py`: Command-line entry point.
  - `main_window.py`: Main `QMainWindow`, grid layout, view synchronization, status bar updates.
  - `zoomable_view.py`: Custom `QGraphicsView` for single image interaction (zoom, pan, pixel inspection).
- `scripts/`: Development helper scripts.
- `tests/`: Unit and integration tests.
- `LICENSE`: MIT License.
- `README.md`: This documentation.

Uses PySide6's `QPixmap` for common image formats (PNG, JPEG, BMP, GIF, etc.).

---

## Future Vision

Designed for **comparative analysis**. Future features:

*   **Image Difference Mode:** Overlay images or view computed "visual diffs" highlighting changes.
*   **Metadata Integration:** Display key info from filenames (e.g., timestep, parameters) or EXIF data.

---

## Troubleshooting

### Installation Issues

-   **`SyntaxError` during `pip install`:** Due to `PySide6` packaging issue. Use `--no-compile`:
    ```bash
    pip install --no-compile -e ".[dev]"
    ```

### Runtime Image Loading

Error messages display in grid cell if image fails to load:

-   `Not found`: File path does not exist.
-   `Permission denied`: Insufficient read permissions.
-   `File too large` / `Dimensions too large`: Exceeds internal safety limits.
-   `Unrecognized format` / `Cannot load`: Invalid/corrupted image format.

Check status bar by hovering over cell for expected file path.

---

## Author
Dav0ud

This project was created to help evaluate algorithm outputs and as a learning exercise in Python and PyQt (now switched to PySide6). Feedback and contributions are welcome!