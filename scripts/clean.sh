#!/bin/bash

# This script cleans the project directory of temporary files, build artifacts,
# and the virtual environment, allowing for a fresh start.
# Run this script from the project root directory.

set -e # Exit immediately if a command exits with a non-zero status.

echo "--- Cleaning Project Directory ---"

# --- Configuration ---
# Define items to remove
VENV_DIR="venv"
PYTEST_CACHE=".pytest_cache"
BUILD_DIR="build"
DIST_DIR="dist"
EGG_INFO_DIR="src/imagegridviewer.egg-info"

# --- Main Logic ---

# Function to safely remove a path (file or directory)
# Usage: safe_remove "path/to/remove" "description"
safe_remove() {
    if [ -e "$1" ]; then
        echo "Removing $2 ($1)..."
        rm -rf "$1"
    else
        echo "$2 ($1) not found, skipping."
    fi
}

# Remove individual files and directories
safe_remove "$VENV_DIR" "Virtual environment"
safe_remove "$PYTEST_CACHE" "pytest cache"
safe_remove "$BUILD_DIR" "PyInstaller build directory"
safe_remove "$DIST_DIR" "PyInstaller dist directory"
safe_remove "$EGG_INFO_DIR" "Editable install metadata"

# Remove glob patterns (e.g., *.spec)
echo "Removing PyInstaller spec files (*.spec)..."
rm -f ./*.spec

echo "Removing __pycache__ directories..."
find . -type d -name "__pycache__" -exec rm -rf {} +

echo "--- Cleanup finished successfully. ---"