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
#FOSS-BOM shall be published in repository so we don't remove it
#BOM_FILE="FOSS-BOM.md"
EGG_INFO_DIR="src/igridvu.egg-info"

# --- Main Logic ---

# Function to safely remove a path (file or directory)
# Usage: safe_remove "path/to/remove" "description"
safe_remove() {
    if [ -e "$1" ]; then
        echo "Removing $2 ($1)..."
        # Add a retry loop to handle potential file locks, especially on macOS
        # where the OS may hold onto a .app bundle for a moment after it closes.
        for i in {1..3}; do
            rm -rf "$1" && break # Exit loop if successful
            if [ ! -e "$1" ]; then break; fi # Also exit if it's gone
            echo "Could not remove '$1' on attempt $i. Retrying in 1 second..."
            sleep 1
        done

        if [ -e "$1" ]; then
            echo "Error: Failed to remove '$1' after multiple attempts." >&2
            exit 1
        fi
    else
        echo "$2 ($1) not found, skipping."
    fi
}

# Remove individual files and directories
safe_remove "$VENV_DIR" "Virtual environment"
safe_remove "$PYTEST_CACHE" "pytest cache"
safe_remove "$BUILD_DIR" "PyInstaller build directory"
safe_remove "$DIST_DIR" "PyInstaller dist directory"
#safe_remove "$BOM_FILE" "Generated FOSS BOM file"
safe_remove "$EGG_INFO_DIR" "Editable install metadata"

# Remove glob patterns (e.g., *.spec)
echo "Removing PyInstaller spec files (*.spec)..."
rm -f ./*.spec

echo "Removing __pycache__ directories..."
find . -type d -name "__pycache__" -exec rm -rf {} +

echo "--- Cleanup finished successfully. ---"