# -*- coding: utf-8 -*-
"""
A script to generate a FOSS Bill of Materials (BOM) in Markdown format.

This script reads package names from requirement files, fetches their metadata
using 'pip show', and compiles the information into a FOSS-BOM.md file.

Run from the project root directory:
  python3 scripts/generate_bom.py
"""

import subprocess
import re
import os
from typing import List, Dict, Optional, Set

# Define file paths relative to the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOM_OUTPUT_FILE = os.path.join(PROJECT_ROOT, "FOSS-BOM.md")
REQUIREMENT_FILES = [
    os.path.join(PROJECT_ROOT, "requirements.txt"),
    os.path.join(PROJECT_ROOT, "requirements-dev.txt"),
]

def get_packages_from_files(file_paths: List[str]) -> List[str]:
    """Reads unique package names from a list of requirements files."""
    packages: Set[str] = set()
    for file_path in file_paths:
        if not os.path.exists(file_path):
            print(f"Warning: Requirement file not found at '{file_path}'")
            continue
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Ignore comments, empty lines, and editable installs
                if line and not line.startswith(('#', '-e')):
                    # Strip version specifiers (e.g., '==', '>=') and extras
                    package_name = re.split(r'[=<>~\[]', line)[0].strip()
                    if package_name:
                        packages.add(package_name)
    return sorted(packages)

def get_package_info(package_name: str) -> Optional[Dict[str, str]]:
    """Fetches package details using 'pip show --verbose'."""
    try:
        # Running pip as a module is generally safer
        result = subprocess.run(
            ["python3", "-m", "pip", "show", "--verbose", package_name],
            capture_output=True, text=True, check=True, encoding='utf-8'
        )
        output = result.stdout

        # Use regex to find the required fields
        name = (re.search(r"^Name: (.*)$", output, re.MULTILINE) or [None, package_name])[1].strip()
        version = (re.search(r"^Version: (.*)$", output, re.MULTILINE) or [None, "N/A"])[1].strip()
        license_info = (re.search(r"^License: (.*)$", output, re.MULTILINE) or [None, "N/A"])[1].strip()

        return {"name": name, "version": version, "license": license_info}

    except subprocess.CalledProcessError:
        print(f"Warning: Could not find package '{package_name}' with pip.")
        return None

def generate_bom_markdown(bom_data: List[Dict[str, str]]) -> str:
    """Generates the FOSS BOM in Markdown format."""
    md_content = [
        "# FOSS Bill of Materials (BOM) for imagegridviewer",
        "",
        "This document lists the open-source software (FOSS) packages used in this project, along with their versions and licenses.",
        "",
        "| Package | Version | License |",
        "|---|---|---|",
    ]

    for item in bom_data:
        md_content.append(f"| {item['name']} | {item['version']} | {item['license']} |")

    return "\n".join(md_content)

def main():
    """Main function to generate the FOSS BOM."""
    print("Generating FOSS Bill of Materials...")
    packages = get_packages_from_files(REQUIREMENT_FILES)
    print(f"Found packages: {', '.join(packages)}")

    bom_data = [info for pkg in packages if (info := get_package_info(pkg))]

    markdown_output = generate_bom_markdown(bom_data)
    with open(BOM_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(markdown_output)
    print(f"\nSuccessfully generated FOSS BOM at: '{BOM_OUTPUT_FILE}'")

if __name__ == "__main__":
    main()