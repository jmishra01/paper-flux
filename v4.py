import sys
import os
import sqlite3
import requests
import xml.etree.ElementTree as ET
import webbrowser

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLineEdit, QListWidget,
    QTextEdit, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QSplitter, QLabel, QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


# ==========================
# DATABASE
# ==========================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("database.db")
        self.create_tables()

    def create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arxiv_id TEXT,
            title TEXT,
            authors TEXT,
            abstract TEXT,
            file_path TEXT,
            notes TEXT,
            folder_id INTEGER,
            FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE
        );
        """)
        self.conn.commit()

    # Folder Methods
    def add_folder(self, name):
        self.conn.execute("INSERT OR IGNORE INTO folders (name) VALUES (?)", (name,))
        self.conn.commit()

    def delete_folder(self, folder_id):
        self.conn.execute("DELETE FROM papers WHERE folder_id=?", (folder_id,))
        self.conn.execute("DELETE FROM folders WHERE id=?", (folder_id,))
        self.conn.commit()

    def get_folders(self):
        return self.conn.execute("SELECT * FROM folders").fetchall()

    # Paper Methods
    def insert_paper(self, arxiv_id, title, authors, abstract, file_path, folder_id):
        self.conn.execute("""
        INSERT INTO papers (arxiv_id, title, authors, abstract, file_path, notes, folder_id)
        VALUES (?, ?, ?, ?, ?, "", ?)
        """, (arxiv_id, title, authors, abstract, file_path, folder_id))
        self.conn.commit()

    def get_papers(self, folder_id, search=""):
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT * FROM papers
        WHERE folder_id=? AND title LIKE ?
        """, (folder_id, f"%{search}%"))
        return cursor.fetchall()

    def move_paper(self, paper_id, new_folder_id):
        self.conn.execute("UPDATE papers SET folder_id=? WHERE id=?",
                          (new_folder_id, paper_id))
        self.conn.commit()

    def update_notes(self, paper_id, notes):
        self.conn.execute("UPDATE papers SET notes=? WHERE id=?",
                          (notes, paper_id))
        self.conn.commit()


# ==========================
# ARXIV API
# ==========================
def fetch_arxiv_metadata(arxiv_id):
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    response = requests.get(url)

    root = ET.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    entry = root.find('atom:entry', ns)

    title = entry.find('atom:title', ns).text.strip()
    abstract = entry.find('atom:summary', ns).text.strip()
    authors = ", ".join(
        author.find('atom:name', ns).text
        for author in entry.findall('atom:author', ns)
    )

    return title, authors, abstract


# ==========================
# DOWNLOAD THREAD
# ==========================
class DownloadThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url, folder_id):
        super().__init__()
        self.url = url
        self.folder_id = folder_id

    def extract_arxiv_id(self):
        return self.url.split("/")[-1]

    def run(self):
        try:
            arxiv_id = self.extract_arxiv_id()
            title, authors, abstract = fetch_arxiv_metadata(arxiv_id)

            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            response = requests.get(pdf_url)
            response.raise_for_status()

            os.makedirs("downloads", exist_ok=True)
            filepath = f"downloads/{arxiv_id}.pdf"

            with open(filepath, "wb") as f:
                f.write(response.content)

            self.finished.emit({
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "file_path": filepath,
                "folder_id": self.folder_id
            })

        except Exception as e:
            self.error.emit(str(e))


# ==========================
# MAIN WINDOW
# ==========================
class ResearchManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Professional Research Manager")
        self.setGeometry(100, 100, 1200, 700)

        self.db = Database()
        self.current_folder_id = None

        self.init_ui()
        self.load_folders()

    def init_ui(self):
        splitter = QSplitter()

        # LEFT SIDEBAR (Folders)
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.itemClicked.connect(self.folder_selected)
        splitter.addWidget(self.folder_tree)

        # RIGHT PANEL
        right_widget = QWidget()
        right_layout = QVBoxLayout()

        # Top bar
        top_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste arXiv URL")

        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.download_paper)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search inside folder")
        self.search_input.textChanged.connect(self.load_papers)

        top_layout.addWidget(self.url_input)
        top_layout.addWidget(self.download_btn)
        top_layout.addWidget(self.search_input)

        right_layout.addLayout(top_layout)

        # Paper list
        self.paper_list = QListWidget()
        self.paper_list.itemClicked.connect(self.show_details)
        right_layout.addWidget(self.paper_list)

        # Abstract
        self.abstract_view = QTextEdit()
        self.abstract_view.setReadOnly(True)
        right_layout.addWidget(self.abstract_view)

        # Notes
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Write notes...")
        right_layout.addWidget(self.notes)

        # Bottom buttons
        bottom_layout = QHBoxLayout()

        self.save_btn = QPushButton("Save Notes")
        self.save_btn.clicked.connect(self.save_notes)

        self.open_btn = QPushButton("Open PDF")
        self.open_btn.clicked.connect(self.open_pdf)

        self.move_btn = QPushButton("Move Paper")
        self.move_btn.clicked.connect(self.move_paper)

        bottom_layout.addWidget(self.save_btn)
        bottom_layout.addWidget(self.open_btn)
        bottom_layout.addWidget(self.move_btn)

        right_layout.addLayout(bottom_layout)

        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(1, 3)
        self.setCentralWidget(splitter)

    # ======================
    # Folder Logic
    # ======================
    def load_folders(self):
        self.folder_tree.clear()
        folders = self.db.get_folders()

        for folder in folders:
            item = QTreeWidgetItem([folder[1]])
            item.setData(0, Qt.ItemDataRole.UserRole, folder[0])
            self.folder_tree.addTopLevelItem(item)

        # Add "Add Folder" item
        add_item = QTreeWidgetItem(["➕ Add Folder"])
        add_item.setData(0, Qt.ItemDataRole.UserRole, -1)
        self.folder_tree.addTopLevelItem(add_item)

    def folder_selected(self, item):
        folder_id = item.data(0, Qt.ItemDataRole.UserRole)

        if folder_id == -1:
            name, ok = QInputDialog.getText(self, "New Folder", "Folder Name:")
            if ok and name:
                self.db.add_folder(name)
                self.load_folders()
            return

        self.current_folder_id = folder_id
        self.load_papers()

    # ======================
    # Paper Logic
    # ======================
    def load_papers(self):
        if not self.current_folder_id:
            return

        search = self.search_input.text()
        self.papers = self.db.get_papers(self.current_folder_id, search)

        self.paper_list.clear()
        for paper in self.papers:
            self.paper_list.addItem(paper[2])

    def show_details(self):
        index = self.paper_list.currentRow()
        self.current_paper = self.papers[index]
        self.abstract_view.setText(self.current_paper[4])
        self.notes.setText(self.current_paper[6])

    def download_paper(self):
        if not self.current_folder_id:
            QMessageBox.warning(self, "Error", "Select a folder")
            return

        url = self.url_input.text().strip()
        self.thread = DownloadThread(url, self.current_folder_id)
        self.thread.finished.connect(self.download_complete)
        self.thread.error.connect(self.download_error)
        self.thread.start()

    def download_complete(self, data):
        self.db.insert_paper(
            data["arxiv_id"],
            data["title"],
            data["authors"],
            data["abstract"],
            data["file_path"],
            data["folder_id"]
        )
        self.load_papers()

    def download_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

    def save_notes(self):
        if hasattr(self, "current_paper"):
            self.db.update_notes(self.current_paper[0],
                                 self.notes.toPlainText())
            QMessageBox.information(self, "Saved", "Notes updated")

    def open_pdf(self):
        if hasattr(self, "current_paper"):
            webbrowser.open("file:///" + os.getcwd() + "/" + self.current_paper[5])

    def move_paper(self):
        if not hasattr(self, "current_paper"):
            return

        folders = self.db.get_folders()
        folder_names = [f[1] for f in folders]

        new_folder, ok = QInputDialog.getItem(
            self, "Move Paper", "Select Folder:",
            folder_names, editable=False
        )

        if ok:
            for f in folders:
                if f[1] == new_folder:
                    self.db.move_paper(self.current_paper[0], f[0])
                    self.load_papers()
                    break


# ==========================
# RUN
# ==========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ResearchManager()
    window.show()
    sys.exit(app.exec())
