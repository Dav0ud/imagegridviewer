#!/bin/bash

# This script automates the setup of a development environment and runs the application.
# It follows the instructions outlined in the README.md.
# Run this script from the project root directory.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
VENV_DIR="venv"
PYTHON_CMD="python3"

# --- Main Logic ---

echo "--- Image Grid Viewer Development Setup & Run ---"

# 1. Create and activate a virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Step 1: Creating virtual environment in '$VENV_DIR'..."
    $PYTHON_CMD -m venv $VENV_DIR
else
    echo "Step 1: Virtual environment '$VENV_DIR' already exists. Skipping creation."
fi

echo "Step 2: Activating virtual environment and running subsequent steps..."

# Run the rest of the commands in a subshell with the venv activated
(
    # Activate the virtual environment
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"

    # 3. Upgrade pip
    echo "Step 3: Upgrading pip..."
    python -m pip install --upgrade pip

    # 4. Install the project for development
    echo "Step 4: Installing project in editable mode with dev dependencies..."
    # Add --no-compile to work around a packaging issue in PySide6 where a template file causes a SyntaxError.
    pip install --no-compile -e ".[dev]"

    # 5. Run the application without input parameters
    echo "Step 5: Launching the application..."
    # Using run_app.py is reliable for development before the package is on the system PATH
    python run_app.py
)

echo "" # Add a newline for spacing
read -p "Do you want to clean the project (remove venv and all build artifacts)? (y/N) " -n 1 -r
echo "" # Move to a new line after input

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Running cleanup script..."
    # Call the script directly with the bash interpreter.
    # This is more robust as it doesn't rely on the executable bit being set.
    bash ./scripts/clean.sh
fi

echo "--- Script finished. ---"
