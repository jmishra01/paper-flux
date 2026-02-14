import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QListWidget, QListWidgetItem, QLabel,
                             QLineEdit, QPushButton, QFrame, QScrollArea)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon


class SideFrame(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""""")

        self.setObjectName("Sidebar")
        self.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(self)

        logo = QLabel("RESEARCH HUB")
        logo.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 20px;")
        sidebar_layout.addWidget(logo)

        nav_items = ["All Papers", "Recently Read", "Favorites", "Neuroscience", "Robotics"]
        for item in nav_items:
            btn = QPushButton(item)
            btn.setStyleSheet("text-align: left; background: transparent; padding: 10px; border: none;")
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

class CentralWidget(QWidget):
    def __init__(self):
        super().__init__()
        center_layout = QVBoxLayout(self)

        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Cmd + K to search...")
        center_layout.addWidget(search_bar)

        self.paper_list = QListWidget()
        self.add_paper_item("Attention is All You Need", "Vaswani et al. (2017)", "Read")
        self.add_paper_item("Deep Learning for Robotics", "LeCun et al. (2020)", "In Progress")
        self.add_paper_item("The Neural Lace Project", "Olloni et al. (2023)", "To Read")
        center_layout.addWidget(self.paper_list)

        drop_zone = QLabel("Drag & Drop PDFs Here to Import")
        drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_zone.setStyleSheet("border: 2px dashed #3f4147; border-radius: 10px; padding: 20px; color: #888;")
        center_layout.addWidget(drop_zone)

    def add_paper_item(self, title, author, status):
        item = QListWidgetItem()
        widget = QWidget()
        layout = QVBoxLayout(widget)

        t_label = QLabel(title)
        t_label.setStyleSheet("font-weight: bold; font-size: 12px; color: white;")
        a_label = QLabel(author)
        a_label.setStyleSheet("color: #888;")

        layout.addWidget(t_label)
        layout.addWidget(a_label)

        # item.setSizeHint(widget.sizeHint())
        item.setSizeHint(QSize(200, 100))
        self.paper_list.addItem(item)
        self.paper_list.setItemWidget(item, widget)


class ResearchHub(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Research Hub - Paper Manager")
        self.resize(1100, 700)
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1f22; }
            QWidget { color: #d1d1d1; font-family: 'Segoe UI', sans-serif; }
            QFrame#Sidebar { background-color: #2b2d31; border-right: 1px solid #3f4147; }
            QFrame#Inspector { background-color: #2b2d31; border-left: 1px solid #3f4147; padding: 15px; }
            QLineEdit { background-color: #383a40; border: none; border-radius: 5px; padding: 8px; color: white; }
            QPushButton#PrimaryBtn { background-color: #5865f2; border-radius: 4px; padding: 8px; font-weight: bold; }
            QLabel#TitleLabel { font-size: 18px; font-weight: bold; color: white; }
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item { background: #2f3136; margin-bottom: 10px; border-radius: 8px; padding: 15px; }
            QListWidget::item:selected { border: 2px solid #5865f2; color: white; }
        """)

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 1. SIDEBAR ---
        sidebar = SideFrame()
        main_layout.addWidget(sidebar)

        # --- 2. CENTER CONTENT ---

        center_widget = CentralWidget()

        main_layout.addWidget(center_widget, stretch=2)

        # --- 3. INSPECTOR (RIGHT PANEL) ---
        inspector = QFrame()
        inspector.setObjectName("Inspector")
        inspector.setFixedWidth(300)
        ins_layout = QVBoxLayout(inspector)

        ins_layout.addWidget(QLabel("METADATA"))
        self.meta_title = QLabel("Attention is All You Need")
        self.meta_title.setObjectName("TitleLabel")
        self.meta_title.setWordWrap(True)
        ins_layout.addWidget(self.meta_title)

        ins_layout.addWidget(QLabel("\nAbstract"))
        abstract = QLabel(
            "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...")
        abstract.setWordWrap(True)
        abstract.setStyleSheet("color: #a1a1a1; font-size: 12px;")
        ins_layout.addWidget(abstract)

        ins_layout.addStretch()

        dl_btn = QPushButton("Download PDF")
        dl_btn.setObjectName("PrimaryBtn")
        ins_layout.addWidget(dl_btn)

        main_layout.addWidget(inspector)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ResearchHub()
    window.show()
    sys.exit(app.exec())