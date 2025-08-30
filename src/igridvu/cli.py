# -*- coding: utf-8 -*-
"""
Command-line interface for the Image Grid Viewer.
"""
import sys
import argparse
from pathlib import Path
from itertools import islice

from PySide6.QtWidgets import QApplication

from .main_window import ImageGrid

APP_NAME = "Image Grid Viewer"
DEFAULT_SUFFIX_FILE = "igridvu_suffix.txt"
# Limit the number of images to prevent excessive resource usage
MAX_IMAGES = 30

def main():
    """Main function to run the application."""
    # Initialize QApplication first, as it can also parse Qt-specific arguments
    app = QApplication(sys.argv)

    parser = argparse.ArgumentParser(
        description="Image Grid Viewer (igridvu). Displays a grid of images from a prefix and a list of suffixes.",
        formatter_class=argparse.RawTextHelpFormatter,  # Keep newlines in help text
        epilog="Example: python3 -m src.igridvu.cli testimage"
    )
    parser.add_argument(
        "image_prefix",
        help="The common prefix for the image files (e.g., 'testimage')."
    )
    parser.add_argument(
        "suffix_file",
        nargs="?",
        default=None,
        help=f"A text file containing image suffixes, one per line.\nDefaults to '{DEFAULT_SUFFIX_FILE}' in the image prefix directory."
    )
    parser.add_argument(
        "-c", "--columns",
        type=int,
        default=4,
        help="The number of columns in the grid. Defaults to 4."
    )
    args = parser.parse_args()

    if args.suffix_file:
        suffix_file_path = Path(args.suffix_file)
    else:
        # The default is 'igridvu_suffix.txt' in the same directory as the prefix.
        prefix_path = Path(args.image_prefix)
        # If prefix is 'foo/bar_', parent is 'foo'. If 'bar_', parent is '.'.
        suffix_file_path = prefix_path.parent / DEFAULT_SUFFIX_FILE

    try:
        # Use encoding='utf-8' for broader compatibility
        with open(suffix_file_path, 'r', encoding='utf-8') as f:
            # Efficiently read up to MAX_IMAGES lines without loading the whole file
            list_of_suffix = list(islice(f, MAX_IMAGES))
            # Check if there were more lines left in the file
            if f.readline():
                print(f"Warning: Suffix file has more than {MAX_IMAGES} lines.", file=sys.stderr)
                print(f"-> Displaying the first {MAX_IMAGES} images.")
    except FileNotFoundError:
        print(f"Error: Suffix file not found at '{suffix_file_path}'", file=sys.stderr)
        sys.exit(1)

    if not list_of_suffix:
        print(f"Info: Suffix file '{suffix_file_path}' is empty. Nothing to display.", file=sys.stderr)
        sys.exit(0)

    # The ImageGrid instance must be stored in a variable for the application to work.
    _ = ImageGrid(
        pre_path=args.image_prefix,
        list_of_suffix=list_of_suffix,
        columns=args.columns,
        app_name=APP_NAME
    )
    sys.exit(app.exec())


if __name__ == '__main__':
    main()