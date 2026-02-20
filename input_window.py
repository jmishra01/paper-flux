from AnyQt.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton, QDialog


class InputWebsite(QDialog):
    website_data_submitted = pyqtSignal(str, str)
    def __init__(self):
        super().__init__()
        print('website_data_submitted')
        self.setWindowTitle("Add Website")
        self.setFixedWidth(400)
        self.setFixedHeight(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10,10,10,10)
        layout.setSpacing(10)

        website_name_layout = QHBoxLayout()
        website_name_layout.setSpacing(5)
        self.website_name_label = QLabel("Website Name")
        self.website_name_label.setAlignment(Qt.AlignCenter)

        self.website_name_value = QLineEdit()
        self.website_name_value.setPlaceholderText("Enter Website Name")

        website_name_layout.addWidget(self.website_name_label)
        website_name_layout.addWidget(self.website_name_value)

        website_url_layout = QHBoxLayout()
        website_url_layout.setSpacing(5)
        self.website_name_label = QLabel("Website Name")
        self.website_url_label = QLabel("Website URL")
        self.website_url_label.setAlignment(Qt.AlignCenter)

        self.website_url_value = QLineEdit()
        self.website_url_value.setPlaceholderText("Enter Website URL")

        website_url_layout.addWidget(self.website_url_label)
        website_url_layout.addWidget(self.website_url_value)

        submit_button = QPushButton("Submit")

        layout.addLayout(website_name_layout)
        layout.addLayout(website_url_layout)
        layout.addWidget(submit_button)

        submit_button.clicked.connect(self.submit_website)

    def submit_website(self):
        self.website_data_submitted.emit(self.website_name_value.text(), self.website_url_value.text())
        self.close()









