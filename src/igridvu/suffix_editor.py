# -*- coding: utf-8 -*-
"""
A dialog for editing the list of image suffixes.
"""
from itertools import islice
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QListWidget, QListWidgetItem,
                             QPushButton, QHBoxLayout, QDialogButtonBox,
                             QAbstractItemView, QMessageBox)
from PySide6.QtCore import Qt


class SuffixEditorDialog(QDialog):
    """A dialog for editing a list of suffixes from a file."""

    def __init__(self, suffix_file_path: str, max_suffixes: int, parent=None):
        super().__init__(parent)
        self.suffix_file_path = suffix_file_path
        self.max_suffixes = max_suffixes
        self.setWindowTitle("Edit Suffixes")
        self.setMinimumSize(400, 500)

        # Main layout
        layout = QVBoxLayout(self)

        # List widget for suffixes
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.itemChanged.connect(self._on_item_changed)
        self.list_widget.model().rowsMoved.connect(self._update_button_states)
        self.list_widget.model().rowsRemoved.connect(self._update_button_states)
        layout.addWidget(self.list_widget)

        # Button layout
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Suffix")
        self.remove_button = QPushButton("Remove Selected")
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Dialog buttons (Save/Cancel)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout.addWidget(self.button_box)

        # Connections
        self.add_button.clicked.connect(self._add_suffix)
        self.remove_button.clicked.connect(self._remove_suffix)
        self.button_box.accepted.connect(self._save_and_accept)
        self.button_box.rejected.connect(self.reject)

        self._load_suffixes()
        self._update_button_states()

    def _load_suffixes(self):
        """Loads suffixes from the file into the list widget."""
        try:
            with open(self.suffix_file_path, 'r', encoding='utf-8') as f:
                # Security: Use islice to prevent reading a massive file into memory.
                suffixes = [line.strip() for line in islice(f, self.max_suffixes) if line.strip()]
                # Check if there are more lines in the file beyond the max limit
                if f.readline():
                    QMessageBox.information(
                        self,
                        "Suffix Limit Reached",
                        f"The suffix file contains more than {self.max_suffixes} entries.\n"
                        f"Only the first {self.max_suffixes} have been loaded into the editor."
                    )

                for suffix in suffixes:
                    item = QListWidgetItem(suffix, self.list_widget)
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
        except FileNotFoundError:
            pass  # It's okay if the file doesn't exist yet.
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Suffixes",
                                 f"Could not load from {self.suffix_file_path}:\n{e}")

    def _add_suffix(self):
        """Adds a new, empty suffix to the list for editing."""
        if self.list_widget.count() >= self.max_suffixes:
            QMessageBox.warning(self, "Limit Reached",
                                f"The maximum number of suffixes ({self.max_suffixes}) has been reached.")
            return

        new_item = QListWidgetItem("new_suffix", self.list_widget)
        new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)
        self.list_widget.setCurrentItem(new_item)
        self.list_widget.editItem(new_item)
        self._update_button_states()

    def _remove_suffix(self):
        """Removes the currently selected suffix from the list."""
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))

    def _on_item_changed(self, item: QListWidgetItem):
        """Ensure item text is stripped of whitespace and not empty."""
        stripped_text = item.text().strip()
        if not stripped_text:
            self.list_widget.takeItem(self.list_widget.row(item))
        elif stripped_text != item.text():
            item.setText(stripped_text)
        self._update_button_states()

    def _update_button_states(self):
        """Enables/disables buttons based on list state."""
        self.add_button.setEnabled(self.list_widget.count() < self.max_suffixes)

    def _save_and_accept(self):
        """Saves the suffixes and, if successful, accepts the dialog."""
        suffixes = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]

        try:
            with open(self.suffix_file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(suffixes))
                if suffixes:
                    f.write('\n')  # Add trailing newline for POSIX compatibility
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error Saving Suffixes",
                                 f"Could not save to {self.suffix_file_path}:\n{e}")