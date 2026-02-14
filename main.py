import sys
import os
import sqlite3
import requests
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QListWidget, QLabel,
    QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyPDF2 import PdfReader
import webbrowser


# ==============================
# DATABASE LAYER
# ==============================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("database.db")
        self.create_table()

    def create_table(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            authors TEXT,
            abstract TEXT,
            file_path TEXT,
            notes TEXT
        )
        """)
        self.conn.commit()

    def insert_paper(self, title, authors, abstract, file_path):
        self.conn.execute("""
        INSERT INTO papers (title, authors, abstract, file_path, notes)
        VALUES (?, ?, ?, ?, "")
        """, (title, authors, abstract, file_path))
        self.conn.commit()

    def get_papers(self, search=""):
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT * FROM papers
        WHERE title LIKE ?
        ORDER BY id DESC
        """, (f"%{search}%",))
        return cursor.fetchall()

    def update_notes(self, paper_id, notes):
        self.conn.execute("""
        UPDATE papers SET notes = ? WHERE id = ?
        """, (notes, paper_id))
        self.conn.commit()


# ==============================
# DOWNLOAD THREAD
# ==============================
class DownloadThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url, download_dir):
        super().__init__()
        self.url = url
        self.download_dir = download_dir

    def convert_to_pdf_url(self, url):
        if "abs" in url:
            return url.replace("abs", "pdf") + ".pdf"
        return url

    def run(self):
        try:
            pdf_url = self.convert_to_pdf_url(self.url)
            response = requests.get(pdf_url)
            response.raise_for_status()

            filename = pdf_url.split("/")[-1]
            filepath = os.path.join(self.download_dir, filename)

            with open(filepath, "wb") as f:
                f.write(response.content)

            reader = PdfReader(filepath)
            metadata = reader.metadata

            title = metadata.title if metadata and metadata.title else filename
            authors = metadata.author if metadata and metadata.author else "Unknown"
            abstract = "Abstract extraction not implemented"

            self.finished.emit({
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "file_path": filepath
            })

        except Exception as e:
            self.error.emit(str(e))


# ==============================
# MAIN UI
# ==============================
class ResearchManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Research Paper Manager")
        self.setGeometry(100, 100, 900, 600)

        self.db = Database()
        self.download_dir = "downloads"
        os.makedirs(self.download_dir, exist_ok=True)

        self.init_ui()
        self.load_papers()

    def init_ui(self):
        layout = QVBoxLayout()

        # URL Input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste arXiv URL here...")
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.download_paper)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.download_btn)

        layout.addLayout(url_layout)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title...")
        self.search_input.textChanged.connect(self.load_papers)
        layout.addWidget(self.search_input)

        # Paper List
        self.paper_list = QListWidget()
        self.paper_list.itemClicked.connect(self.show_paper_details)
        layout.addWidget(self.paper_list)

        # Notes
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Write notes here...")
        layout.addWidget(self.notes)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_notes_btn = QPushButton("Save Notes")
        self.save_notes_btn.clicked.connect(self.save_notes)

        self.open_pdf_btn = QPushButton("Open PDF")
        self.open_pdf_btn.clicked.connect(self.open_pdf)

        btn_layout.addWidget(self.save_notes_btn)
        btn_layout.addWidget(self.open_pdf_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    # ==========================
    # Paper Loading
    # ==========================
    def load_papers(self):
        self.paper_list.clear()
        search = self.search_input.text()
        self.papers = self.db.get_papers(search)
        for paper in self.papers:
            self.paper_list.addItem(f"{paper[1]}")

    def show_paper_details(self, item):
        index = self.paper_list.currentRow()
        self.current_paper = self.papers[index]
        self.notes.setText(self.current_paper[5])

    # ==========================
    # Download Logic
    # ==========================
    def download_paper(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Enter URL")
            return

        self.thread = DownloadThread(url, self.download_dir)
        self.thread.finished.connect(self.download_complete)
        self.thread.error.connect(self.download_error)
        self.thread.start()

    def download_complete(self, data):
        self.db.insert_paper(
            data["title"],
            data["authors"],
            data["abstract"],
            data["file_path"]
        )
        QMessageBox.information(self, "Success", "Paper downloaded")
        self.load_papers()

    def download_error(self, msg):
        QMessageBox.critical(self, "Download Error", msg)

    # ==========================
    # Notes & Open PDF
    # ==========================
    def save_notes(self):
        if hasattr(self, "current_paper"):
            self.db.update_notes(self.current_paper[0], self.notes.toPlainText())
            QMessageBox.information(self, "Saved", "Notes saved")

    def open_pdf(self):
        if hasattr(self, "current_paper"):
            webbrowser.open_new("file:///" + os.getcwd() + "/" + self.current_paper[4])


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ResearchManager()
    window.show()
    sys.exit(app.exec())
