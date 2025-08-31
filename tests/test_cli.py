# -*- coding: utf-8 -*-
"""
Unit tests for the command-line interface (cli.py) of the Image Grid Viewer.

These tests verify:
- Correct parsing of command-line arguments.
- Proper handling of the suffix file, including default path logic.
- Graceful error handling for missing or empty suffix files.
- Enforcement of the MAX_IMAGES limit.
- Correct initialization of the main application window with parsed arguments.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from igridvu import cli


@patch('igridvu.cli.QApplication')
@patch('igridvu.cli.ImageGrid')
@patch('igridvu.cli.sys.exit')
def test_cli_successful_run(mock_exit, mock_image_grid, mock_qapp, tmp_path, monkeypatch):
    """Tests a standard successful run with explicit arguments."""
    # Arrange
    suffix_file = tmp_path / "suffixes.txt"
    suffix_file.write_text("a.png\nb.png\n")
    expected_suffixes = ["a.png", "b.png"]

    prefix = "test_prefix_"
    monkeypatch.setattr(sys, 'argv', ['igridvu', prefix, str(suffix_file)])
    
    mock_app_instance = MagicMock()
    mock_app_instance.exec.return_value = 0
    mock_qapp.return_value = mock_app_instance

    # Act
    cli.main()

    # Assert
    mock_qapp.assert_called_once()
    mock_image_grid.assert_called_once_with(
        pre_path=prefix,
        list_of_suffix=expected_suffixes,
        suffix_file_path=str(suffix_file),
        columns=4,  # Default value
        app_name=cli.APP_NAME
    )
    mock_app_instance.exec.assert_called_once()
    mock_exit.assert_called_once_with(0)


@patch('igridvu.cli.QApplication')
@patch('igridvu.cli.ImageGrid')
@patch('igridvu.cli.sys.exit')
def test_cli_default_suffix_file(mock_exit, mock_image_grid, mock_qapp, tmp_path, monkeypatch):
    """Tests that the CLI correctly finds the default suffix file."""
    # Arrange
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    prefix = image_dir / "test_prefix_"

    default_suffix_file = image_dir / cli.DEFAULT_SUFFIX_FILE
    default_suffix_file.write_text("default1.png\n\ndefault2.png\n")
    expected_suffixes = ["default1.png", "default2.png"]
    
    monkeypatch.setattr(sys, 'argv', ['igridvu', str(prefix)])

    mock_app_instance = MagicMock()
    mock_qapp.return_value = mock_app_instance

    # Act
    cli.main()

    # Assert
    mock_image_grid.assert_called_once_with(
        pre_path=str(prefix),
        list_of_suffix=expected_suffixes,
        suffix_file_path=str(default_suffix_file),
        columns=4,
        app_name=cli.APP_NAME
    )


@patch('igridvu.cli.QApplication')
@patch('igridvu.cli.ImageGrid')
@patch('igridvu.cli.sys.exit')
def test_cli_suffix_file_not_found(mock_exit, mock_image_grid, mock_qapp, tmp_path, monkeypatch):
    """Tests that the CLI starts with an empty grid if the suffix file is not found."""
    # Arrange
    prefix = tmp_path / "prefix_"
    # Suffix file does not exist, so the path is just for the argument
    suffix_file_path = tmp_path / cli.DEFAULT_SUFFIX_FILE
    monkeypatch.setattr(sys, 'argv', ['igridvu', str(prefix)])
    mock_app_instance = MagicMock()
    mock_qapp.return_value = mock_app_instance

    # Act
    cli.main()

    # Assert
    mock_image_grid.assert_called_once_with(
        pre_path=str(prefix),
        list_of_suffix=[],
        suffix_file_path=str(suffix_file_path),
        columns=4,
        app_name=cli.APP_NAME
    )
    mock_exit.assert_called_once()


@patch('igridvu.cli.QApplication')
@patch('igridvu.cli.ImageGrid')
@patch('igridvu.cli.sys.exit')
def test_cli_empty_suffix_file(mock_exit, mock_image_grid, mock_qapp, tmp_path, monkeypatch):
    """Tests that the CLI starts with an empty grid if the suffix file is empty."""
    # Arrange
    empty_file = tmp_path / "empty.txt"
    empty_file.touch()
    prefix = "prefix_"
    monkeypatch.setattr(sys, 'argv', ['igridvu', prefix, str(empty_file)])
    mock_app_instance = MagicMock()
    mock_qapp.return_value = mock_app_instance

    # Act
    cli.main()

    # Assert
    mock_image_grid.assert_called_once_with(
        pre_path=prefix,
        list_of_suffix=[],
        suffix_file_path=str(empty_file),
        columns=4,
        app_name=cli.APP_NAME
    )
    mock_exit.assert_called_once()


@patch('igridvu.cli.QApplication')
@patch('igridvu.cli.ImageGrid')
@patch('igridvu.cli.sys.exit')
def test_cli_max_images_limit(mock_exit, mock_image_grid, mock_qapp, tmp_path, monkeypatch, capsys):
    """Tests that the number of images is limited and a warning is printed."""
    # Arrange
    long_suffix_file = tmp_path / "long.txt"
    num_lines = cli.MAX_IMAGES + 5
    long_suffix_file.write_text("\n".join([f"{i}.png" for i in range(num_lines)]))
    expected_suffixes = [f"{i}.png" for i in range(cli.MAX_IMAGES)]

    monkeypatch.setattr(sys, 'argv', ['igridvu', 'prefix', str(long_suffix_file)])

    mock_app_instance = MagicMock()
    mock_app_instance.exec.return_value = 0
    mock_qapp.return_value = mock_app_instance

    # Act
    cli.main()

    # Assert
    captured = capsys.readouterr()
    assert f"Warning: Suffix file has more than {cli.MAX_IMAGES} lines." in captured.err

    mock_image_grid.assert_called_once_with(
        pre_path='prefix',
        list_of_suffix=expected_suffixes,
        suffix_file_path=str(long_suffix_file),
        columns=4,
        app_name=cli.APP_NAME
    )


@patch('igridvu.cli.QApplication')
@patch('igridvu.cli.ImageGrid')
@patch('igridvu.cli.sys.exit')
def test_cli_custom_columns(mock_exit, mock_image_grid, mock_qapp, tmp_path, monkeypatch):
    """Tests that the --columns argument is correctly passed to ImageGrid."""
    # Arrange
    suffix_file = tmp_path / "suffixes.txt"
    suffix_file.write_text("a.png\n")

    mock_app_instance = MagicMock()
    mock_app_instance.exec.return_value = 0
    mock_qapp.return_value = mock_app_instance

    # Test with short form '-c'
    monkeypatch.setattr(sys, 'argv', ['igridvu', 'prefix', str(suffix_file), '-c', '2'])
    cli.main()
    mock_image_grid.assert_called_with(
        pre_path='prefix',
        list_of_suffix=['a.png'],
        suffix_file_path=str(suffix_file),
        columns=2,
        app_name=cli.APP_NAME
    )

    # Reset mock for the next assertion
    mock_image_grid.reset_mock()

    # Test with long form '--columns'
    monkeypatch.setattr(sys, 'argv', ['igridvu', 'prefix', str(suffix_file), '--columns', '8'])
    cli.main()
    mock_image_grid.assert_called_with(
        pre_path='prefix',
        list_of_suffix=['a.png'],
        suffix_file_path=str(suffix_file),
        columns=8,
        app_name=cli.APP_NAME
    )


@patch('igridvu.cli.QApplication')
@patch('igridvu.cli.ImageGrid')
@patch('igridvu.cli.sys.exit')
def test_cli_no_arguments(mock_exit, mock_image_grid, mock_qapp, monkeypatch):
    """Tests that the CLI starts in welcome mode with no arguments."""
    # Arrange
    monkeypatch.setattr(sys, 'argv', ['igridvu'])
    mock_app_instance = MagicMock()
    mock_qapp.return_value = mock_app_instance

    # Act
    cli.main()

    # Assert
    mock_image_grid.assert_called_once_with(
        pre_path="",
        list_of_suffix=[],
        suffix_file_path=str(Path.cwd() / cli.DEFAULT_SUFFIX_FILE),
        columns=4,
        app_name=cli.APP_NAME
    )