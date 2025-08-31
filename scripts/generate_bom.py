# -*- coding: utf-8 -*-
"""
A script to generate a FOSS Bill of Materials (BOM) in Markdown format.

This script reads package names from pyproject.toml, fetches their metadata
using 'pip show', and compiles the information into a FOSS-BOM.md file. It
requires 'tomli' to be installed on Python versions older than 3.11.

Run from the project root directory:
  python3 scripts/generate_bom.py
"""

import subprocess
import re
import os
import sys
from typing import List, Dict, Optional, Set

# Use tomllib if available (Python 3.11+), otherwise fall back to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: 'tomli' is required to run this script on Python < 3.11.", file=sys.stderr)
        print("Please run: pip install tomli", file=sys.stderr)
        sys.exit(1)

# A ranked list of license families from most permissive to weak copyleft.
# We will pick the first one that matches from this list.
LICENSE_PERMISSIVENESS_ORDER = [
    'Unlicense',
    'MIT',
    'BSD',
    'ISC',
    'Apache',
    'MPL',  # Mozilla Public License
    'LGPL', # Lesser General Public License
    'GPL',  # General Public License (as a fallback if nothing else matches)
]

# Define file paths relative to the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOM_OUTPUT_FILE = os.path.join(PROJECT_ROOT, "FOSS-BOM.md")
PYPROJECT_FILE = os.path.join(PROJECT_ROOT, "pyproject.toml")

def get_packages_from_pyproject(file_path: str) -> List[str]:
    """Reads unique package names from pyproject.toml."""
    packages: Set[str] = set()
    if not os.path.exists(file_path):
        print(f"Error: pyproject.toml not found at '{file_path}'", file=sys.stderr)
        return []

    with open(file_path, 'rb') as f:
        data = tomllib.load(f)

    # Get main dependencies
    for dep in data.get('project', {}).get('dependencies', []):
        package_name = re.split(r'[=<>~\[]', dep)[0].strip()
        if package_name:
            packages.add(package_name)

    # Get optional (dev) dependencies
    for dep in data.get('project', {}).get('optional-dependencies', {}).get('dev', []):
        package_name = re.split(r'[=<>~\[]', dep)[0].strip()
        if package_name:
            packages.add(package_name)

    return sorted(packages)

def select_permissive_license(license_string: str) -> str:
    """
    Selects the most permissive license from a string containing multiple licenses
    (e.g., "LGPL-3.0-only OR GPL-2.0-only").
    """
    # If it's not a multi-license string, just clean it up and return.
    if ' OR ' not in license_string:
        return license_string.replace('-only', '')

    licenses = [lic.strip() for lic in license_string.split(' OR ')]

    for permissive_type in LICENSE_PERMISSIVENESS_ORDER:
        for license_option in licenses:
            if permissive_type.lower() in license_option.lower():
                # Clean up common suffixes like '-only' and return the match.
                return license_option.replace('-only', '')

    # Fallback to the first license in the list if no match from our order.
    return licenses[0].replace('-only', '')

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

        # Select the most permissive license if multiple are listed
        final_license = select_permissive_license(license_info)

        return {"name": name, "version": version, "license": final_license}

    except subprocess.CalledProcessError:
        print(f"Warning: Could not find package '{package_name}' with pip.", file=sys.stderr)
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
    print("Generating FOSS Bill of Materials from pyproject.toml...")
    packages = get_packages_from_pyproject(PYPROJECT_FILE)
    if not packages:
        print("No packages found in pyproject.toml. Exiting.")
        return

    print(f"Found packages: {', '.join(packages)}")

    bom_data = [info for pkg in packages if (info := get_package_info(pkg))]

    markdown_output = generate_bom_markdown(bom_data)
    with open(BOM_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(markdown_output)
    print(f"\nSuccessfully generated FOSS BOM at: '{BOM_OUTPUT_FILE}'")

if __name__ == "__main__":
    main()