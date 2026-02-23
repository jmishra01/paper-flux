from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QComboBox,
                             QPushButton, QHBoxLayout, QLabel)

from database import Folder


class CategoryDialog(QDialog):
    selected_category = pyqtSignal(str)
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Select Category")
        self.setFixedWidth(300)
        self.setFixedHeight(200)
        self.setContentsMargins(10, 10, 10, 10)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.combo = QComboBox()
        folders = [i[0] for i in Folder.get_all_folders()]
        self.combo.addItems(folders)
        layout.addWidget(self.combo)

        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(10, 10, 10, 10)

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.close_with_save)
        h_layout.addWidget(btn_save)

        layout.addLayout(h_layout)
        self.setLayout(layout)

    def close_with_save(self):
        self.selected_category.emit(self.combo.currentText())
        self.close()


class WarningDialog(QDialog):
    def __init__(self, message: str):
        super().__init__()
        self.setWindowTitle("Warning")

        label = QLabel(message)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(label)
        self.setLayout(layout)

