import sys
import uuid
import urllib.request as request
from PyQt6.QtCore import Qt, QUrl, QFileInfo
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QInputDialog, QTreeWidgetItem,
                             QFileIconProvider, QFrame, QVBoxLayout, QLineEdit, QLabel)

from database import Paper, Folder
from details import Details
from save_article import save_open_page
from tree_widget import TreeWidget
from utils import *
from viewer import Viewer
from input_window import InputWebsite


class PaperFlux(QMainWindow):
    def __init__(self):
        super().__init__()
        self.website_menu = None
        self.setWindowTitle("PaperFlux")
        self.resize(1200, 800)
        self.side_window_width = 250

        # UI Styling (Dark Theme)
        self.setStyleSheet("""
            QMainWindow { background-color: #2e2e2e; }
            
            QTreeWidget, QFrame#Details {
                background-color: #333438;
            }
            
        """)
        """
        
            QWidget { color: #d1d1d1; font-family: sans-serif; }
            QFrame#Sidebar { background-color: #2b2d31; border-right: 1px solid #3f4147; }
            QLineEdit { background-color: #383a40; border: 1px solid #4f545c; border-radius: 4px; padding: 8px; color: white; }
            QPushButton { background-color: #5865f2; color: white; border-radius: 4px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #4752c4; }
            QTreeWidget { background: #232428; border: none; border-radius: 8px; margin: 10px; }
            QTreeWidget::item { padding: 4px; border-bottom: 1px solid #2f3136; }
            QTreeWidget::item:selected { background: #393c43; border-left: 4px solid #5865f2; }
        """
        # Main Layout using Splitter for Resizing
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        main_layout.setContentsMargins(5, 5, 5, 5)

        # Left Widget
        self.left_container = QFrame()
        self.left_container.setFixedWidth(self.side_window_width)
        self.left_container.setContentsMargins(0, 0, 0, 0)

        frame_layout = QVBoxLayout()
        self.left_container.setLayout(frame_layout)

        frame_layout.setContentsMargins(0, 0, 0, 0)

        search = QLineEdit()
        search.setStyleSheet("""
        background-color: #383a40;
        border: 1px solid #4f545c;
        border-radius: 12px;
        padding: 8px;
        """)
        search.textChanged.connect(self.search_paper)
        search.setFixedHeight(30)
        frame_layout.addWidget(search)


        self.tree_widget = TreeWidget()
        self.tree_widget.setStyleSheet("""
        background-color: #383a40;
        border: 1px solid #4f545c;
        border-radius: 12px;
        padding: 8px;
        """)
        frame_layout.addWidget(self.tree_widget)

        # Web View
        self.viewer = Viewer()

        # Right Widget
        self.right_container = Details()

        self.right_container.setFixedWidth(self.side_window_width)
        self.right_container.setContentsMargins(0, 0, 0, 0)
        self.right_container.on_title_changed.connect(lambda _: self.load_full_library())
        self.right_container.on_category_changed.connect(lambda _: self.load_full_library())

        self.tree_widget.ItemChanged.connect(self.render_item)
        self.tree_widget.ItemChanged.connect(self.right_container.update_display)

        main_layout.addWidget(self.left_container)

        main_layout.addWidget(self.viewer)
        main_layout.addWidget(self.right_container)

        self.init_menu_bar()

        self.load_full_library()
        self.load_last_paper()

    def closeEvent(self, a0):
        self.viewer.page().deleteLater()
        self.viewer.deleteLater()
        self.viewer.get_profile().deleteLater()
        a0.accept()

    def search_paper(self, text):
        print('search_paper: ', text)
        if text == "":
            self.load_full_library()
        else:
            self.load_search_library(text)

    def render_item(self, paper_id):
        file_path = Paper.get_paper_path(paper_id)[0]
        Paper.update_paper_last_view_date(paper_id)

        if file_path.startswith(("https://", "http://")):
            self.viewer.setUrl(QUrl(file_path))
        else:
            if not os.path.exists(file_path):
                url = Paper.get_url(paper_id)[0]
                request.urlretrieve(url, file_path)
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
        arxiv_add_action = edit_menu.addAction("Add PDF URL")
        arxiv_add_action.triggered.connect(self.add_arxiv_pdf)

        # ## -- Add local pdf
        local_dir_action = edit_menu.addAction("Add Local Directory")
        local_dir_action.triggered.connect(self.add_local_dir)

        # ## -- Add Website
        website_add_action = edit_menu.addAction("Add Website")
        website_add_action.triggered.connect(self.add_website)

        # ## -- Save Page
        save_page_action = edit_menu.addAction("Save Page")
        save_page_action.triggered.connect(self.save_open_page)

        remove_page_action = edit_menu.addAction("Remove Page")
        remove_page_action.triggered.connect(self.remove_page_selected_item)

        # -- View
        view_menu = menu_bar.addMenu("View")

        # ## -- Toggle Library
        toggle_library_action = view_menu.addAction("Toggle Sidebar")
        toggle_library_action.triggered.connect(self.toggle_library_action)

    def add_website(self):
        input_window = InputWebsite()
        input_window.website_data_submitted.connect(self.add_website_in_db)
        if input_window.exec():
            pass

    def add_website_in_db(self, website_name, website_url):
        Paper.insert_row(
            arxiv_id=str(uuid.uuid4()),
            title=website_name,
            authors=None,
            abstract=None,
            file_path=website_url,
            website_url=website_url,
            folder_id=2
        )
        self.load_full_library()

    def toggle_library_action(self):
        self.left_container.setVisible(not self.left_container.isVisible())
        self.right_container.setVisible(not self.right_container.isVisible())

    def remove_page_selected_item(self):
        selected_item: QTreeWidgetItem = self.tree_widget.selectedItems()[0]
        text = selected_item.text(0)
        if paper_id := Paper.get_paper_id_of_title(text):
            Paper.hard_delete_row(paper_id[0])

            if last_viewed_paper_id := Paper.get_last_viewed_paper():
                self.render_item(last_viewed_paper_id[0])

        elif (folder_id := Paper.get_folder_id_for_title(text)) and folder_id[0] != 1:
            Paper.change_folder_id(folder_id[0], 1)
            Folder.remove_folder(folder_id[0])

        self.load_full_library()

    def save_open_page(self):
        url = self.viewer.url().toString()
        save_open_page(url, folder_id=self.tree_widget.get_selected_category())
        self.load_full_library()

    def open_webpage(self, url):
        return lambda : self.viewer.setUrl(QUrl(url))

    def add_local_dir(self):
        text, ok = QInputDialog.getText(self, "Add Local directory path", "Write local directory path ....")
        if ok and text != "":
            folder_name = text.split("/")[-1]
            folder_id = Folder.get_folder_id_for_title(folder_name)
            if folder_id is None:
                Folder.insert_row(folder_name, 0)
                folder_id = Folder.get_folder_id_for_title(folder_name)

            folder_id = folder_id[0]

            for (parent_directory, _, files) in os.walk(text):
                for file in (i for i in files if i.endswith(".pdf")):
                    if Paper.get_paper_id_of_title(file.rstrip(".pdf")):
                        continue

                    Paper.insert_row(
                        arxiv_id=str(uuid.uuid4()),
                        title=file.rstrip(".pdf"),
                        authors=None,
                        abstract=None,
                        file_path=os.path.join(parent_directory, file),
                        website_url=None,
                        folder_id=folder_id
                    )
            self.load_full_library()


    def add_arxiv_pdf(self):
        text, ok = QInputDialog.getText(self, "Add Article URL", "Paste arXiv or medium or any other article URL here:")
        if ok and text != "":
            save_open_page(text, folder_id=self.tree_widget.get_selected_category())
            self.load_full_library()

    def dialog_to_add_category(self):
        text, ok = QInputDialog.getText(self, "Add New Category",
                                        "Please enter a new category.")
        if ok and text != "":
            self.tree_widget.get_category(text)
            Folder.insert_row(text, 0)

    def load_last_paper(self):
        arxiv_id = Paper.get_last_viewed_paper()
        if arxiv_id is None:
            return
        arxiv_id = arxiv_id[0]
        self.right_container.update_display(arxiv_id)
        self.render_item(arxiv_id)

    def load_full_library(self):
        paper = Paper.get_all_papers()
        if not paper:
            return None
        return self.load_library(paper)

    def load_search_library(self, title: str):
        paper = Paper.search_paper(title)
        if not paper:
            return None
        return self.load_library(paper)

    def load_library(self, paper: list):

        self.tree_widget.clear()
        categories = {}

        last_viewed_arxiv_id = Paper.get_last_viewed_paper()

        style = QApplication.style()
        icon_provider = QFileIconProvider()

        for paper_id, title, folder_name, file_path in paper:
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
            item.setData(0, Qt.ItemDataRole.UserRole, paper_id)

            if last_viewed_arxiv_id and paper_id == last_viewed_arxiv_id[0]:
                self.tree_widget.setCurrentItem(item)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PaperFlux()
    window.show()
    sys.exit(app.exec())