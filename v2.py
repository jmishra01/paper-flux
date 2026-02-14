import sys
import os
import sqlite3
import requests
import xml.etree.ElementTree as ET
import webbrowser
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QListWidget, QLabel,
    QTextEdit, QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyPDF2 import PdfReader


# ==========================
# DATABASE
# ==========================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("database.db")
        self.create_tables()

    def create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arxiv_id TEXT,
            title TEXT,
            authors TEXT,
            abstract TEXT,
            file_path TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS paper_tags (
            paper_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (paper_id, tag_id)
        );
        """)
        self.conn.commit()

    def insert_paper(self, arxiv_id, title, authors, abstract, file_path):
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO papers (arxiv_id, title, authors, abstract, file_path, notes)
        VALUES (?, ?, ?, ?, ?, "")
        """, (arxiv_id, title, authors, abstract, file_path))
        self.conn.commit()
        return cursor.lastrowid

    def add_tags(self, paper_id, tag_list):
        for tag in tag_list:
            tag = tag.strip().lower()
            if not tag:
                continue
            self.conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
            tag_id = self.conn.execute("SELECT id FROM tags WHERE name=?", (tag,)).fetchone()[0]
            self.conn.execute("INSERT OR IGNORE INTO paper_tags VALUES (?, ?)", (paper_id, tag_id))
        self.conn.commit()

    def get_papers(self, search=""):
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT DISTINCT papers.*
        FROM papers
        LEFT JOIN paper_tags ON papers.id = paper_tags.paper_id
        LEFT JOIN tags ON tags.id = paper_tags.tag_id
        WHERE papers.title LIKE ? OR tags.name LIKE ?
        ORDER BY papers.id DESC
        """, (f"%{search}%", f"%{search}%"))
        return cursor.fetchall()

    def update_notes(self, paper_id, notes):
        self.conn.execute("UPDATE papers SET notes=? WHERE id=?", (notes, paper_id))
        self.conn.commit()


# ==========================
# ARXIV API HELPER
# ==========================
def fetch_arxiv_metadata(arxiv_id):
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    response = requests.get(url)
    root = ET.fromstring(response.content)

    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    entry = root.find('atom:entry', ns)
    if entry is None:
        raise Exception("Invalid arXiv ID")

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

    def __init__(self, url, download_dir):
        super().__init__()
        self.url = url
        self.download_dir = download_dir

    def extract_arxiv_id(self, url):
        return url.split("/")[-1]

    def run(self):
        try:
            arxiv_id = self.extract_arxiv_id(self.url)
            title, authors, abstract = fetch_arxiv_metadata(arxiv_id)

            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            response = requests.get(pdf_url)
            response.raise_for_status()

            filepath = os.path.join(self.download_dir, f"{arxiv_id}.pdf")
            with open(filepath, "wb") as f:
                f.write(response.content)

            self.finished.emit({
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "file_path": filepath
            })

        except Exception as e:
            self.error.emit(str(e))


# ==========================
# UI
# ==========================
class ResearchManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Research Paper Manager Pro")
        self.setGeometry(100, 100, 900, 650)

        self.db = Database()
        self.download_dir = "downloads"
        os.makedirs(self.download_dir, exist_ok=True)

        self.init_ui()
        self.load_papers()

    def init_ui(self):
        layout = QVBoxLayout()

        # URL
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste arXiv URL...")
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.download_paper)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.download_btn)
        layout.addLayout(url_layout)

        # Tags
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Enter tags (comma separated)")
        layout.addWidget(self.tag_input)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title or tag...")
        self.search_input.textChanged.connect(self.load_papers)
        layout.addWidget(self.search_input)

        # List
        self.paper_list = QListWidget()
        self.paper_list.itemClicked.connect(self.show_details)
        layout.addWidget(self.paper_list)

        # Abstract
        self.abstract_view = QTextEdit()
        self.abstract_view.setReadOnly(True)
        layout.addWidget(self.abstract_view)

        # Notes
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Write notes...")
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

    def load_papers(self):
        self.paper_list.clear()
        search = self.search_input.text()
        self.papers = self.db.get_papers(search)
        for paper in self.papers:
            self.paper_list.addItem(paper[2])

    def show_details(self):
        index = self.paper_list.currentRow()
        self.current_paper = self.papers[index]
        self.abstract_view.setText(self.current_paper[4])
        self.notes.setText(self.current_paper[6])

    def download_paper(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Enter arXiv URL")
            return

        self.thread = DownloadThread(url, self.download_dir)
        self.thread.finished.connect(self.download_complete)
        self.thread.error.connect(self.download_error)
        self.thread.start()

    def download_complete(self, data):
        paper_id = self.db.insert_paper(
            data["arxiv_id"],
            data["title"],
            data["authors"],
            data["abstract"],
            data["file_path"]
        )

        tags = self.tag_input.text().split(",")
        self.db.add_tags(paper_id, tags)

        QMessageBox.information(self, "Success", "Paper added!")
        self.load_papers()

    def download_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

    def save_notes(self):
        if hasattr(self, "current_paper"):
            self.db.update_notes(self.current_paper[0], self.notes.toPlainText())
            QMessageBox.information(self, "Saved", "Notes saved")

    def open_pdf(self):
        if hasattr(self, "current_paper"):
            webbrowser.open(self.current_paper[5])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ResearchManager()
    window.show()
    sys.exit(app.exec())
