from AnyQt.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QComboBox,
                             QPushButton, QWidget, QHBoxLayout)

from database import Folder


class CategoryDialog(QDialog):
    close_with_selected_category = False

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

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close_without_save)
        h_layout.addWidget(btn_close)

        layout.addLayout(h_layout)
        self.setLayout(layout)

    def close_with_save(self):
        self.close_with_selected_category = True
        self.close()

    def close_without_save(self):
        self.close()