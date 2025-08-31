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
    suffixes = ["a.png\n", "b.png\n"]
    suffix_file.write_text("".join(suffixes))

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
        list_of_suffix=suffixes,
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
    suffixes = ["default1.png\n", "default2.png\n"]
    default_suffix_file.write_text("".join(suffixes))

    monkeypatch.setattr(sys, 'argv', ['igridvu', str(prefix)])

    mock_app_instance = MagicMock()
    mock_qapp.return_value = mock_app_instance

    # Act
    cli.main()

    # Assert
    mock_image_grid.assert_called_once_with(
        pre_path=str(prefix),
        list_of_suffix=suffixes,
        columns=4,
        app_name=cli.APP_NAME
    )


@patch('igridvu.cli.QApplication')
@patch('igridvu.cli.ImageGrid')
def test_cli_suffix_file_not_found(mock_image_grid, mock_qapp, tmp_path, monkeypatch, capsys):
    """Tests that the CLI exits gracefully if the suffix file is not found."""
    # Arrange
    non_existent_file = tmp_path / "not_real.txt"
    monkeypatch.setattr(sys, 'argv', ['igridvu', 'some_prefix', str(non_existent_file)])

    # Act & Assert
    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    assert excinfo.value.code == 1, "Should exit with status 1 on file not found"

    captured = capsys.readouterr()
    assert "Error: Suffix file not found" in captured.err
    assert str(non_existent_file) in captured.err

    mock_image_grid.assert_not_called()


@patch('igridvu.cli.QApplication')
@patch('igridvu.cli.ImageGrid')
def test_cli_empty_suffix_file(mock_image_grid, mock_qapp, tmp_path, monkeypatch, capsys):
    """Tests that the CLI exits gracefully if the suffix file is empty."""
    # Arrange
    empty_file = tmp_path / "empty.txt"
    empty_file.touch()
    monkeypatch.setattr(sys, 'argv', ['igridvu', 'some_prefix', str(empty_file)])

    # Act & Assert
    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    assert excinfo.value.code == 0, "Should exit with status 0 for an empty file"

    captured = capsys.readouterr()
    assert "Info: Suffix file" in captured.err
    assert "is empty. Nothing to display." in captured.err

    mock_image_grid.assert_not_called()


@patch('igridvu.cli.QApplication')
@patch('igridvu.cli.ImageGrid')
@patch('igridvu.cli.sys.exit')
def test_cli_max_images_limit(mock_exit, mock_image_grid, mock_qapp, tmp_path, monkeypatch, capsys):
    """Tests that the number of images is limited and a warning is printed."""
    # Arrange
    long_suffix_file = tmp_path / "long.txt"
    num_lines = cli.MAX_IMAGES + 5
    suffixes = [f"{i}.png\n" for i in range(num_lines)]
    long_suffix_file.write_text("".join(suffixes))

    monkeypatch.setattr(sys, 'argv', ['igridvu', 'prefix', str(long_suffix_file)])

    mock_app_instance = MagicMock()
    mock_app_instance.exec.return_value = 0
    mock_qapp.return_value = mock_app_instance

    # Act
    cli.main()

    # Assert
    captured = capsys.readouterr()
    assert f"Warning: Suffix file has more than {cli.MAX_IMAGES} lines." in captured.err

    mock_image_grid.assert_called_once()
    called_kwargs = mock_image_grid.call_args.kwargs
    assert len(called_kwargs['list_of_suffix']) == cli.MAX_IMAGES
    assert called_kwargs['list_of_suffix'] == suffixes[:cli.MAX_IMAGES]


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
        pre_path='prefix', list_of_suffix=['a.png\n'], columns=2, app_name=cli.APP_NAME
    )

    # Reset mock for the next assertion
    mock_image_grid.reset_mock()

    # Test with long form '--columns'
    monkeypatch.setattr(sys, 'argv', ['igridvu', 'prefix', str(suffix_file), '--columns', '8'])
    cli.main()
    mock_image_grid.assert_called_with(
        pre_path='prefix', list_of_suffix=['a.png\n'], columns=8, app_name=cli.APP_NAME
    )