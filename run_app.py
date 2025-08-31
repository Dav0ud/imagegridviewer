import sys
from igridvu.cli import main

if __name__ == "__main__":
    # This script is a dedicated entry point for the GUI application,
    # which is a reliable way to launch it when packaged with PyInstaller.
    # The main() function is expected to start the PySide6 application event loop.
    sys.exit(main())