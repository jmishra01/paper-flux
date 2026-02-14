from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QComboBox,
                             QPushButton)

from database import DATABASE


class CategoryDialog(QDialog):
    def __init__(self, parent=None):
        super(CategoryDialog, self).__init__(parent)

        self.setWindowTitle("Select Category")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.combo = QComboBox()
        folders = [i[0] for i in DATABASE.get_all_folder()]
        self.combo.addItems(folders)
        layout.addWidget(self.combo)

        btn = QPushButton("Save & Close")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

        self.setLayout(layout)
