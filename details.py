from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget, QLineEdit, QComboBox, QSizePolicy, QPushButton

from database import DATABASE


class Details(QFrame):
    on_title_changed = pyqtSignal(str)
    on_category_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()

        self.setFixedWidth(200)
        self.file_path_value = None
        self.arxiv_id = None
        self.title = None
        self.folder_name = None
        self.file_path = None
        self.setStyleSheet(""" """)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.categories = [i[0] for i in DATABASE.get_all_folder()]

        self.layout.addWidget(self.add_title())
        self.layout.addWidget(self.add_category())
        self.layout.addWidget(self.add_file_path())

        self.save_changes = QPushButton("Save Changes")
        self.updated_title = ""
        self.updated_category = ""
        self.save_changes.clicked.connect(self.save_changes_callback)
        self.save_changes.setVisible(False)

        self.layout.addWidget(self.save_changes)

        self.layout.addStretch(1)

    def save_changes_callback(self):
        if self.updated_title != self.title:
            DATABASE.update_paper_title(self.arxiv_id, self.updated_title)
            self.title = self.updated_title
            self.on_title_changed.emit(self.updated_title)

        if self.updated_category != self.folder_name:
            folder_id = DATABASE.get_folder_id(self.updated_category)[0]
            DATABASE.update_folder_in_paper(self.arxiv_id, folder_id)
            self.folder_name = self.updated_category
            self.on_category_changed.emit(True)

        self.save_changes.setVisible(False)

    def add_title(self):
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)

        title_widget.setFixedHeight(80)
        title_widget.setContentsMargins(0, 0, 0, 0)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        title_label = QLabel("Title")
        title_label.setFixedHeight(40)
        title_layout.addWidget(title_label)

        self.title_value = QLineEdit()
        self.title_value.setFixedHeight(40)
        title_layout.addWidget(self.title_value)
        self.title_value.textEdited.connect(self.update_title)

        return title_widget

    def update_title(self, value):
        cursor_pos = self.title_value.cursorPosition()
        self.title_value.blockSignals(True)
        self.title_value.setText(value)
        self.title_value.blockSignals(False)
        self.title_value.setCursorPosition(cursor_pos)
        self.updated_title = value
        self.save_changes.setVisible(True)

    def add_category(self):
        category_widget = QWidget()
        category_layout = QVBoxLayout(category_widget)

        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(0)

        category_label = QLabel("Category")
        category_label.setFixedHeight(40)
        category_layout.addWidget(category_label)

        self.category_combo = QComboBox()
        self.category_combo.addItems(self.categories)
        self.category_combo.currentTextChanged.connect(self.update_category)
        category_layout.addWidget(self.category_combo)

        return category_widget

    def update_category(self, category: str):
        if category not in self.categories:
            return
        self.category_combo.setCurrentIndex(self.categories.index(category))
        self.updated_category = category
        self.save_changes.setVisible(True)

    def update_categories(self):
        current_text = self.category_combo.currentText()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.categories = [i[0] for i in DATABASE.get_all_folder()]
        self.category_combo.addItems(self.categories)
        self.category_combo.setCurrentIndex(self.categories.index(current_text))

        self.category_combo.blockSignals(False)


    def add_file_path(self):
        file_path_widget = QWidget()
        file_path_layout = QVBoxLayout(file_path_widget)
        file_path_layout.setContentsMargins(0, 0, 0, 0)
        file_path_layout.setSpacing(0)

        file_path_label = QLabel("File Path")
        file_path_label.setFixedHeight(40)
        file_path_layout.addWidget(file_path_label)

        self.file_path_value = QLabel()
        self.file_path_value.setStyleSheet("""
        background-color: #444;
        padding: 2px;
        border: 1px solid #555;
        border-radius: 6px;
        """)
        self.file_path_value.setWordWrap(True)
        self.file_path_value.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        file_path_layout.addWidget(self.file_path_value)
        return file_path_widget

    def update_display(self, paper_id: str):
        details = DATABASE.get_papers_using_id(paper_id)
        if details is None:
            self.setVisible(False)
            return

        self.save_changes.setVisible(False)
        self.update_categories()

        (self.arxiv_id, self.title, self.folder_name, self.file_path) = details

        self.updated_title = self.title
        self.updated_category = self.folder_name



        self.title_value.setText(self.title)
        self.category_combo.setCurrentIndex(self.categories.index(self.folder_name))
        self.file_path_value.setText(self.file_path)
