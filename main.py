import sys
import uuid

from PyQt6.QtCore import Qt, QUrl, QFileInfo
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QInputDialog, QSplitter, QTreeWidgetItem,
                             QFileIconProvider, QFrame, QVBoxLayout)

from database import DATABASE
from details import Details
from save_article import save_open_page
from tree_widget import TreeWidget
from utils import *
from viewer import Viewer


class PaperFlux(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PaperFlux")
        self.resize(1200, 800)

        # UI Styling (Dark Theme)
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1f22; }
            QWidget { color: #d1d1d1; font-family: sans-serif; }
            QFrame#Sidebar { background-color: #2b2d31; border-right: 1px solid #3f4147; }
            QLineEdit { background-color: #383a40; border: 1px solid #4f545c; border-radius: 4px; padding: 8px; color: white; }
            QPushButton { background-color: #5865f2; color: white; border-radius: 4px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #4752c4; }
            QTreeWidget { background: #232428; border: none; border-radius: 8px; margin: 10px; }
            QTreeWidget::item { padding: 4px; border-bottom: 1px solid #2f3136; }
            QTreeWidget::item:selected { background: #393c43; border-left: 4px solid #5865f2; }
        """)

        # Main Layout using Splitter for Resizing
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)


        self.left_container = QFrame()
        frame_layout = QVBoxLayout()
        self.left_container.setLayout(frame_layout)

        # Web View
        self.viewer = Viewer()

        self.tree_widget = TreeWidget()
        frame_layout.addWidget(self.tree_widget)

        self.right_container = Details()
        self.right_container.on_title_changed.connect(lambda _: self.load_library())
        self.right_container.on_category_changed.connect(lambda _: self.load_library())

        self.tree_widget.ItemChanged.connect(self.render_item)
        self.tree_widget.ItemChanged.connect(self.right_container.update_display)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.left_container)
        self.splitter.addWidget(self.viewer)
        self.splitter.setStretchFactor(1, 2)  # Make preview wider

        self.splitter_right = QSplitter(Qt.Orientation.Horizontal)
        self.splitter_right.addWidget(self.splitter)
        self.splitter_right.addWidget(self.right_container)
        # self.splitter_right.setStretchFactor(1, 2)

        layout.addWidget(self.splitter_right)

        self.init_menu_bar()

        self.load_library()
        self.load_last_paper()

    def render_item(self, paper_id):
        file_path = DATABASE.get_paper_path(paper_id)
        DATABASE.update_last_view(paper_id)

        if file_path.startswith(("https://", "http://")):
            self.viewer.setUrl(QUrl(file_path))
        else:
            self.viewer.setUrl(QUrl.fromLocalFile(file_path))

    def init_menu_bar(self):
        menu_bar = self.menuBar()

        # -- File
        file_menu = menu_bar.addMenu("File")

        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # -- Add
        edit_menu = menu_bar.addMenu("Edit")
        # ## -- New Category
        new_category_action = edit_menu.addAction("Add Category")
        new_category_action.triggered.connect(self.dialog_to_add_category)

        # ## -- Add arXiv pdf
        arxiv_add_action = edit_menu.addAction("Add ArXiv PDF")
        arxiv_add_action.triggered.connect(self.add_arxiv_pdf)

        # ## -- Add local pdf
        local_dir_action = edit_menu.addAction("Add PDF Files")
        local_dir_action.triggered.connect(self.add_local_dir)

        # ## -- Save Page
        save_page_action = edit_menu.addAction("Save Page")
        save_page_action.triggered.connect(self.save_open_page)

        remove_page_action = edit_menu.addAction("Remove Page")
        remove_page_action.triggered.connect(self.remove_page_selected_item)

        # -- View
        view_menu = menu_bar.addMenu("View")

        # ## -- Toggle Library
        toggle_library_action = view_menu.addAction("Toggle Library")
        toggle_library_action.triggered.connect(self.toggle_library_action)

        # -- Open webpage
        open_menu = menu_bar.addMenu("Open")

        # ## -- Open ArXiv
        arxiv_action = open_menu.addAction("Open ArXiv")
        arxiv_action.triggered.connect(self.open_webpage("https://arxiv.org"))

        # ## -- Open Medium
        medium_action = open_menu.addAction("Open Medium")
        medium_action.triggered.connect(self.open_webpage("https://medium.com"))

        # ## -- Open TowardDataScience
        medium_action = open_menu.addAction("Open TowardDataScience")
        medium_action.triggered.connect(self.open_webpage("https://towardsdatascience.com"))

    def toggle_library_action(self):
        self.left_container.setVisible(not self.left_container.isVisible())

    def remove_page_selected_item(self):
        selected_item: QTreeWidgetItem = self.tree_widget.selectedItems()[0]
        text = selected_item.text(0)
        if paper_id := DATABASE.get_paper_id(text):
            DATABASE.remove_paper_using_arxiv_id(paper_id[0])

            if last_viewed_arxiv_id := DATABASE.get_last_view_paper():
                self.render_item(last_viewed_arxiv_id[0])

        elif (folder_id := DATABASE.get_folder_id(text)) and folder_id[0] != 1:
            DATABASE.change_folder_id(folder_id[0], 1)
            DATABASE.remove_folder(folder_id[0])

        self.load_library()

    def save_open_page(self):
        url = self.viewer.url().toString()
        save_open_page(url, folder_id=self.tree_widget.get_selected_category())
        self.load_library()

    def open_webpage(self, url):
        return lambda : self.viewer.setUrl(QUrl(url))

    def add_local_dir(self):
        text, ok = QInputDialog.getText(self, "Add Local directory path", "Write local directory path ....")
        if ok and text != "":
            folder_name = text.split("/")[-1]
            folder_id = DATABASE.get_folder_id(folder_name)
            if folder_id is None:
                DATABASE.insert_folder(folder_name, 0)
                folder_id = DATABASE.get_folder_id(folder_name)

            folder_id = folder_id[0]

            for (parent_directory, _, files) in os.walk(text):
                for file in (i for i in files if i.endswith(".pdf")):
                    if DATABASE.get_paper_id(file.rstrip(".pdf")):
                        continue
                    DATABASE.insert_paper(
                        str(uuid.uuid4()),
                        file.rstrip(".pdf"),
                        None,
                        None,
                        os.path.join(parent_directory, file),
                        folder_id
                    )
            self.load_library()


    def add_arxiv_pdf(self):
        text, ok = QInputDialog.getText(self, "Add Article URL", "Paste arXiv or medium or any other article URL here:")
        if ok and text != "":
            save_open_page(text, folder_id=self.tree_widget.get_selected_category())
            self.load_library()

    def dialog_to_add_category(self):
        text, ok = QInputDialog.getText(self, "Add New Category",
                                        "Please enter a new category.")
        if ok and text != "":
            self.tree_widget.get_category(text)
            DATABASE.insert_folder(text)

    def load_last_paper(self):
        arxiv_id = DATABASE.get_last_view_paper()
        if arxiv_id is None:
            return
        arxiv_id = arxiv_id[0]
        self.right_container.update_display(arxiv_id)
        self.render_item(arxiv_id)

    def load_library(self):
        results = DATABASE.get_papers()
        if not results:
            return

        self.tree_widget.clear()
        categories = {}

        last_viewed_arxiv_id = DATABASE.get_last_view_paper()

        style = QApplication.style()
        icon_provider = QFileIconProvider()

        for arxiv_id, title, folder_name, file_path in results:
            if folder_name not in categories:
                categories[folder_name] = self.tree_widget.get_category(folder_name)

            category: QTreeWidgetItem = categories[folder_name]

            item = QTreeWidgetItem(category)
            if file_path.endswith(".pdf"):
                file_icon = QFileInfo(file_path)
                item.setIcon(0, icon_provider.icon(file_icon))
            else:
                item.setIcon(0, style.standardIcon(style.StandardPixmap.SP_FileIcon))
            item.setText(0, title)
            item.setData(0, Qt.ItemDataRole.UserRole, arxiv_id)

            if last_viewed_arxiv_id and arxiv_id == last_viewed_arxiv_id[0]:
                self.tree_widget.setCurrentItem(item)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PaperFlux()
    window.show()
    sys.exit(app.exec())