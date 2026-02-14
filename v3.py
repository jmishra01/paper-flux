import sys
import os
import sqlite3
import requests
import xml.etree.ElementTree as ET
import webbrowser

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QListWidget, QLabel,
    QTextEdit, QMessageBox, QComboBox, QInputDialog
)
from PyQt6.QtCore import QThread, pyqtSignal


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
            FOREIGN KEY(folder_id) REFERENCES folders(id)
        );
        """)
        self.conn.commit()

    # ---------- Folder ----------
    def add_folder(self, name):
        self.conn.execute("INSERT OR IGNORE INTO folders (name) VALUES (?)", (name,))
        self.conn.commit()

    def get_folders(self):
        return self.conn.execute("SELECT * FROM folders").fetchall()

    # ---------- Papers ----------
    def insert_paper(self, arxiv_id, title, authors, abstract, file_path, folder_id):
        self.conn.execute("""
        INSERT INTO papers (arxiv_id, title, authors, abstract, file_path, notes, folder_id)
        VALUES (?, ?, ?, ?, ?, "", ?)
        """, (arxiv_id, title, authors, abstract, file_path, folder_id))
        self.conn.commit()

    def get_papers(self, folder_id=None):
        cursor = self.conn.cursor()
        if folder_id:
            cursor.execute("SELECT * FROM papers WHERE folder_id=?", (folder_id,))
        else:
            cursor.execute("SELECT * FROM papers")
        return cursor.fetchall()

    def update_notes(self, paper_id, notes):
        self.conn.execute("UPDATE papers SET notes=? WHERE id=?", (notes, paper_id))
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

    def extract_arxiv_id(self, url):
        return url.split("/")[-1]

    def run(self):
        try:
            arxiv_id = self.extract_arxiv_id(self.url)
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
# UI
# ==========================
class ResearchManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Research Manager with Folders")
        self.setGeometry(100, 100, 1000, 650)

        self.db = Database()
        self.init_ui()
        self.load_folders()

    def init_ui(self):
        layout = QVBoxLayout()

        # Folder Section
        folder_layout = QHBoxLayout()

        self.folder_combo = QComboBox()
        self.folder_combo.currentIndexChanged.connect(self.load_papers)

        self.new_folder_btn = QPushButton("New Folder")
        self.new_folder_btn.clicked.connect(self.create_folder)

        folder_layout.addWidget(QLabel("Folder:"))
        folder_layout.addWidget(self.folder_combo)
        folder_layout.addWidget(self.new_folder_btn)

        layout.addLayout(folder_layout)

        # URL Input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste arXiv URL")
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.download_paper)

        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.download_btn)
        layout.addLayout(url_layout)

        # Paper List
        self.paper_list = QListWidget()
        self.paper_list.itemClicked.connect(self.show_details)
        layout.addWidget(self.paper_list)

        # Abstract
        self.abstract_view = QTextEdit()
        self.abstract_view.setReadOnly(True)
        layout.addWidget(self.abstract_view)

        # Notes
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Notes...")
        layout.addWidget(self.notes)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Notes")
        self.save_btn.clicked.connect(self.save_notes)
        self.open_btn = QPushButton("Open PDF")
        self.open_btn.clicked.connect(self.open_pdf)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.open_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    # ======================
    # Folder Logic
    # ======================
    def create_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder Name:")
        if ok and name:
            self.db.add_folder(name)
            self.load_folders()

    def load_folders(self):
        self.folder_combo.clear()
        self.folders = self.db.get_folders()
        for folder in self.folders:
            self.folder_combo.addItem(folder[1], folder[0])

        if self.folders:
            self.load_papers()

    # ======================
    # Paper Logic
    # ======================
    def load_papers(self):
        if not self.folders:
            return
        folder_id = self.folder_combo.currentData()
        self.papers = self.db.get_papers(folder_id)
        self.paper_list.clear()
        for paper in self.papers:
            self.paper_list.addItem(paper[2])

    def show_details(self):
        index = self.paper_list.currentRow()
        self.current_paper = self.papers[index]
        self.abstract_view.setText(self.current_paper[4])
        self.notes.setText(self.current_paper[6])

    def download_paper(self):
        if not self.folders:
            QMessageBox.warning(self, "Error", "Create a folder first")
            return

        url = self.url_input.text().strip()
        folder_id = self.folder_combo.currentData()

        self.thread = DownloadThread(url, folder_id)
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
        QMessageBox.information(self, "Success", "Paper added!")
        self.load_papers()

    def download_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

    def save_notes(self):
        if hasattr(self, "current_paper"):
            self.db.update_notes(self.current_paper[0], self.notes.toPlainText())
            QMessageBox.information(self, "Saved", "Notes updated")

    def open_pdf(self):
        if hasattr(self, "current_paper"):
            webbrowser.open("file:///" + os.getcwd() + "/" + self.current_paper[5])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ResearchManager()
    window.show()
    sys.exit(app.exec())
