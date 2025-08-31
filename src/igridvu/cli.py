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
from .config import MAX_IMAGES

APP_NAME = "Image Grid Viewer"
DEFAULT_SUFFIX_FILE = "igridvu_suffix.txt"

def main():
    """Main function to run the application."""
    # Initialize QApplication first, as it can also parse Qt-specific arguments
    app = QApplication(sys.argv)

    parser = argparse.ArgumentParser(
        description="Image Grid Viewer (igridvu). Displays a grid of images from a prefix and a list of suffixes.",
        formatter_class=argparse.RawTextHelpFormatter,  # Keep newlines in help text
        epilog="Example: igridvu testscene/scene1_"
    )
    parser.add_argument(
        "image_prefix",
        nargs="?",
        default=None,
        help="The common prefix for the image files (e.g., 'testimage').\nIf omitted, the application starts with a welcome screen."
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

    list_of_suffix = []
    pre_path_str = ""
    suffix_file_path_str = ""

    if args.image_prefix:
        # A prefix was provided, try to load files.
        pre_path_str = args.image_prefix
        prefix_path = Path(pre_path_str)

        if args.suffix_file:
            suffix_file_path = Path(args.suffix_file)
        else:
            # The default is 'igridvu_suffix.txt' in the same directory as the prefix.
            suffix_file_path = prefix_path.parent / DEFAULT_SUFFIX_FILE

        if suffix_file_path.is_file():
            try:
                with open(suffix_file_path, 'r', encoding='utf-8') as f:
                    list_of_suffix = [line.strip() for line in islice(f, MAX_IMAGES) if line.strip()]
                    if f.readline():
                        print(f"Warning: Suffix file has more than {MAX_IMAGES} lines.", file=sys.stderr)
                        print(f"-> Displaying the first {MAX_IMAGES} images.")
            except IOError as e:
                print(f"Warning: Could not read suffix file '{suffix_file_path}': {e}", file=sys.stderr)
        suffix_file_path_str = str(suffix_file_path)
    else:
        # No prefix provided. Start in welcome state.
        # The suffix editor will need a path to create a new file.
        suffix_file_path_str = str(Path.cwd() / DEFAULT_SUFFIX_FILE)

    # The ImageGrid instance must be stored in a variable for the application to work.
    _ = ImageGrid(
        pre_path=pre_path_str,
        list_of_suffix=list_of_suffix,
        suffix_file_path=suffix_file_path_str,
        columns=args.columns,
        app_name=APP_NAME
    )
    sys.exit(app.exec())


if __name__ == '__main__':
    main()