from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget, QTextEdit, QComboBox, QSizePolicy, \
    QPushButton, QHBoxLayout, QStackedWidget

from database import Paper, Folder


class Details(QFrame):
    on_title_changed = pyqtSignal(str)
    on_category_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()

        self.website_address_widget: QWidget = None
        self.category_combo = None
        self.website_url = None
        self.website_address_value = None
        self.setStyleSheet("""
        Details { 
            background-color: #383a40;
            border: 1px solid #4f545c;
            border-radius: 12px;
        }
        """)

        self.fix_height_of_title_label = 40

        self.title_value_label = None
        self.title_value_stack = None
        self.btn_stack = None
        self.title_value_text_edit = None

        self.paper_id = None
        self.file_path_value = None
        self.arxiv_id = None
        self.title = None
        self.folder_name = None
        self.file_path = None
        self.updated_title = ""
        self.updated_category = ""

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.categories = [i[0] for i in Folder.get_all_folders()]

        self.layout.addWidget(self.add_title(), alignment=Qt.AlignmentFlag.AlignTop)
        self.layout.addWidget(self.add_category(), alignment=Qt.AlignmentFlag.AlignTop)
        self.layout.addWidget(self.add_file_path(), alignment=Qt.AlignmentFlag.AlignTop)
        self.layout.addWidget(self.add_website_address(), alignment=Qt.AlignmentFlag.AlignTop)

        self.layout.addStretch(1)

    def _add_title_header(self):
        title_label = QLabel("Title")
        title_label.setFixedHeight(40)
        title_label.setStyleSheet("""
        padding: 0px;
        font: 24px sans-serif;
        font-weight: bold;
        """)

        # Edit button


        title_edit_btn = QPushButton()
        title_edit_btn.setIcon(QIcon("icons/pencil.svg"))
        title_edit_btn.setFixedHeight(30)
        title_edit_btn.setFixedWidth(30)
        title_edit_btn.setIconSize(QSize(18, 18))
        title_edit_btn.clicked.connect(self.change_to_edit_mode)


        title_done_btn = QPushButton()
        title_done_btn.setIcon(QIcon("icons/done.png"))
        title_done_btn.setFixedHeight(30)
        title_done_btn.setFixedWidth(30)
        title_done_btn.setIconSize(QSize(18, 18))
        title_done_btn.clicked.connect(self.update_title_callback)


        self.btn_stack = QStackedWidget()
        self.btn_stack.addWidget(title_edit_btn)
        self.btn_stack.addWidget(title_done_btn)

        title_label_layout = QHBoxLayout()

        title_label_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignTop)
        title_label_layout.addWidget(self.btn_stack, alignment=Qt.AlignmentFlag.AlignRight |  Qt.AlignmentFlag.AlignVCenter)

        return title_label_layout

    def _add_title_edit_part(self):
        self.title_value_stack = QStackedWidget()
        self.title_value_stack.setStyleSheet("""
            border: 1px solid #434742
        """)
        self.title_value_label = QLabel()
        self.title_value_label.setStyleSheet("""
            background-color: #232328;
            padding: 2px;
            border: 1px solid #555;
            border-radius: 6px;
        """)
        self.title_value_label.setWordWrap(True)
        self.title_value_label.scroll(0, 0)

        self.title_value_text_edit = QTextEdit()

        self.title_value_stack.addWidget(self.title_value_label)
        self.title_value_stack.addWidget(self.title_value_text_edit)
        self.title_value_stack.setCurrentIndex(0)

        self.set_fix_height_of_title_label(60)

    def add_title(self):
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)

        title_widget.setContentsMargins(0, 0, 0, 0)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        title_layout.addLayout(self._add_title_header())
        title_layout.addStretch(1)

        self._add_title_edit_part()

        title_layout.addWidget(self.title_value_stack)
        return title_widget

    def update_title_callback(self):
        value = self.title_value_text_edit.toPlainText()
        self.title_value_label.setText(value)
        self.title = value

        Paper.update_paper_title(self.paper_id, value)

        self.on_title_changed.emit(value)

        self.btn_stack.setCurrentIndex(0)
        self.title_value_stack.setCurrentIndex(0)
        self.set_fix_height_of_title_label(len(self.title))

    def change_to_edit_mode(self):
        self.title_value_text_edit.setPlainText(self.title_value_label.text())
        self.btn_stack.setCurrentIndex(1)
        self.title_value_stack.setCurrentIndex(1)
        self.set_fix_height_of_title_label(len(self.title_value_label.text()))

    def add_category(self):
        category_widget = QWidget()
        category_layout = QVBoxLayout(category_widget)

        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(0)

        category_label = QLabel("Category")

        category_label.setStyleSheet("""
        padding: 0px;
        font: 24px sans-serif;
        font-weight: bold;
        """)
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
        self.updated_category = category

        self.category_combo.setCurrentIndex(self.categories.index(self.updated_category))

        folder_id = Folder.get_folder_id_for_title(self.updated_category)[0]
        Paper.update_folder_id(self.paper_id, folder_id)
        self.folder_name = self.updated_category
        self.on_category_changed.emit(True)

    def update_categories(self):
        current_text = self.category_combo.currentText()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.categories = [i[0] for i in Folder.get_all_folders()]
        self.category_combo.addItems(self.categories)
        self.category_combo.setCurrentIndex(self.categories.index(current_text))

        self.category_combo.blockSignals(False)

    def add_file_path(self):
        file_path_widget = QWidget()
        file_path_layout = QVBoxLayout(file_path_widget)
        file_path_layout.setContentsMargins(0, 0, 0, 0)
        file_path_layout.setSpacing(0)

        file_path_label = QLabel("Path")
        file_path_label.setStyleSheet("""
        padding: 0px;
        font: 24px sans-serif;
        font-weight: bold;
        """)
        file_path_label.setFixedHeight(40)
        file_path_layout.addWidget(file_path_label)

        self.file_path_value = QLabel()
        self.file_path_value.setStyleSheet("""
            background-color: #232328;
            padding: 2px;
            border: 1px solid #555;
            border-radius: 6px;
        """)
        self.file_path_value.setWordWrap(True)
        self.file_path_value.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.file_path_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        file_path_layout.addWidget(self.file_path_value)
        return file_path_widget


    def add_website_address(self):
        self.website_address_widget: QWidget = QWidget()
        website_address_layout = QVBoxLayout(self.website_address_widget)
        website_address_layout.setContentsMargins(0, 0, 0, 0)
        website_address_layout.setSpacing(0)

        website_address_label = QLabel("Address")
        website_address_label.setStyleSheet("""
            padding: 0px;
            font: 24px sans-serif;
            font-weight: bold;
        """)
        website_address_label.setFixedHeight(40)
        website_address_layout.addWidget(website_address_label)

        self.website_address_value = QLabel()
        self.website_address_value.setStyleSheet("""
            background-color: #232328;
            padding: 2px;
            border: 1px solid #555;
            border-radius: 6px;
        """)
        self.website_address_value.setWordWrap(True)
        self.website_address_value.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.website_address_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        website_address_layout.addWidget(self.website_address_value)
        return self.website_address_widget

    def update_title_fixed_height(self, n: int):
        self.title_value_stack.setFixedHeight(n)
        self.title_value_text_edit.setFixedHeight(n)

    def set_fix_height_of_title_label(self, n: int):
        if n < 60:
            self.update_title_fixed_height(60)
        elif n < 100:
            self.update_title_fixed_height(100)
        elif n < 130:
            self.update_title_fixed_height(130)
        else:
            self.update_title_fixed_height(180)


    def update_display(self, paper_id: str):
        details = Paper.get_paper_using_id(paper_id)
        if details is None:
            self.setVisible(False)
            return

        self.update_categories()

        (self.paper_id, self.arxiv_id, self.title, self.folder_name, self.file_path, self.website_url) = details

        self.updated_title: str = self.title
        self.updated_category = self.folder_name

        self.title_value_label.setText(self.title)
        self.set_fix_height_of_title_label(len(self.title))

        self.category_combo.setCurrentIndex(self.categories.index(self.folder_name))
        self.file_path_value.setText(self.file_path)
        self.website_address_value.setText(self.website_url)

        if self.website_url is None or len(self.website_url) == 0:
            self.website_address_widget.hide()
        else:
            self.website_address_widget.show()
