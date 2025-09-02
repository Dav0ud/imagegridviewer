# -*- coding: utf-8 -*-
"""
Unit tests for the SuffixEditorDialog.
"""
from pathlib import Path

from unittest.mock import Mock
import pytest
from PySide6.QtWidgets import QMessageBox, QListWidgetItem

from igridvu.suffix_editor import SuffixEditorDialog


def test_suffix_editor_loads_suffixes(qtbot, tmp_path: Path):
    """Tests that the editor correctly loads suffixes from a file."""
    suffix_file = tmp_path / "suffixes.txt"
    suffix_file.write_text("a.png\nb.png\n")

    dialog = SuffixEditorDialog(str(suffix_file), max_suffixes=10, parent=None)
    qtbot.addWidget(dialog)

    assert dialog.list_widget.count() == 2
    assert dialog.list_widget.item(0).text() == "a.png"
    assert dialog.list_widget.item(1).text() == "b.png"


def test_suffix_editor_handles_file_not_found(qtbot, tmp_path: Path):
    """Tests that the editor starts empty if the suffix file doesn't exist."""
    non_existent_file = tmp_path / "non_existent.txt"
    dialog = SuffixEditorDialog(str(non_existent_file), max_suffixes=10, parent=None)
    qtbot.addWidget(dialog)
    assert dialog.list_widget.count() == 0


def test_suffix_editor_saves_suffixes(qtbot, tmp_path: Path):
    """Tests that the editor correctly saves changes to the suffix file."""
    suffix_file = tmp_path / "suffixes.txt"
    dialog = SuffixEditorDialog(str(suffix_file), max_suffixes=10, parent=None)
    qtbot.addWidget(dialog)

    # Add items
    dialog.list_widget.addItem(QListWidgetItem("first.png"))
    dialog.list_widget.addItem(QListWidgetItem("second.png"))

    # Simulate clicking "Save"
    dialog._save_and_accept()

    assert suffix_file.read_text() == "first.png\nsecond.png\n"


def test_suffix_editor_limit_enforced_on_load(qtbot, tmp_path: Path, monkeypatch):
    """Tests that the editor truncates the list and warns if the suffix file exceeds the max limit."""
    suffix_file = tmp_path / "suffixes.txt"
    # Create a file with more suffixes than the limit
    suffixes = [f"{i}.png" for i in range(15)]
    suffix_file.write_text("\n".join(suffixes))

    mock_msgbox = Mock()
    monkeypatch.setattr(QMessageBox, 'information', mock_msgbox)

    dialog = SuffixEditorDialog(str(suffix_file), max_suffixes=10, parent=None)
    qtbot.addWidget(dialog)

    # Assert that only max_suffixes were loaded
    assert dialog.list_widget.count() == 10
    # Assert that a warning was shown
    mock_msgbox.assert_called_once()
    # Check the content of the warning
    args, _ = mock_msgbox.call_args
    assert "Suffix Limit Reached" in args
    assert "more than 10 entries" in args[2]


def test_suffix_editor_limit_enforced_on_add(qtbot, tmp_path: Path, monkeypatch):
    """Tests that the user cannot add more suffixes than the max limit."""
    suffix_file = tmp_path / "suffixes.txt"
    # Create a file with exactly max_suffixes
    suffixes = [f"{i}.png" for i in range(10)]
    suffix_file.write_text("\n".join(suffixes))

    mock_msgbox = Mock()
    monkeypatch.setattr(QMessageBox, 'warning', mock_msgbox)

    dialog = SuffixEditorDialog(str(suffix_file), max_suffixes=10, parent=None)
    qtbot.addWidget(dialog)

    assert dialog.list_widget.count() == 10
    assert not dialog.add_button.isEnabled()

    # Try to add another one, which should fail and show a warning
    dialog._add_suffix()

    assert dialog.list_widget.count() == 10
    mock_msgbox.assert_called_once()
    args, _ = mock_msgbox.call_args
    # The QMessageBox.warning signature is (parent, title, text).
    assert args[1] == "Limit Reached"  # Check the title
    assert "maximum number of suffixes (10)" in args[2]  # Check the detailed text