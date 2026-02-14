import sys
import shutil
import datetime
import sqlite3
import urllib.request
import os
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QListWidget, QListWidgetItem, QLabel,
                             QLineEdit, QPushButton, QFrame, QSplitter, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from bs4 import BeautifulSoup



FILE_PATH = os.path.dirname(os.path.realpath(__file__)) + "/downloads"


# ==============================
# DATABASE
# ==============================
class Database:
    def __init__(self):
        self.db_name = "research_library.db"
        self.backup()
        self.conn = sqlite3.connect(self.db_name)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arxiv_id TEXT NOT NULL unique,
            title TEXT,
            authors TEXT,
            abstract TEXT,
            file_path TEXT,
            added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_view DATETIME
        );
        """)
        self.conn.commit()

    def backup(self):
        if os.path.exists(self.db_name):
            shutil.copy(self.db_name, "backup_" + self.db_name)

    # -------- Papers --------
    def insert_paper(self, arxiv_id, title,
                     authors, abstract,
                     file_path):
        self.conn.execute("""
        INSERT INTO papers (arxiv_id, title, authors,
                            abstract, file_path)
        VALUES (?, ?, ?, ?, ?)
        """, (arxiv_id, title, authors,
              abstract, file_path
              ))
        self.conn.commit()

    def update_last_view(self, arxiv_id):
        self.conn.execute(" UPDATE papers SET last_view = ? WHERE arxiv_id = ? ",
                          (datetime.datetime.now(), arxiv_id))
        self.conn.commit()

    def get_papers(self, search=""):
        return self.conn.execute("""
        SELECT arxiv_id, title FROM papers
        WHERE title LIKE ?
        """, (f"%{search}%", )).fetchall()

    def get_paper_path(self, arxiv_id):
        return self.conn.execute("""
        SELECT file_path FROM papers WHERE arxiv_id = ?
        """, (arxiv_id,)).fetchone()[0]

    def get_last_view(self):
        return self.conn.execute("""
        SELECT avxiv_id FROM papers
        ORDER BY last_view DESC, created_at DESC
        LIMIT 1""").fetchone()


def arxiv_scrapper(arxiv_id):
    url = f"https://arxiv.org/abs/{arxiv_id}"
    response = urllib.request.urlopen(url)
    html = response.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")

    abstract_details = soup.find("div", {"id": "abs"})
    if not abstract_details:
        raise Exception("No abstract found")
    title = abstract_details.find("h1", {"class": "title"}).text.lstrip("Title:")

    authors = ", ".join(author.text
                           for author in abstract_details.find("div", {"class": "authors"}).find_all("a"))

    abstract = abstract_details.find("blockquote", {"class": "abstract"}).text

    return title, authors, abstract


class ResearchHub(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.setWindowTitle("Research Hub v2.0")
        self.resize(1200, 800)

        # UI Styling (Dark Theme)
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1f22; }
            QWidget { color: #d1d1d1; font-family: 'Inter', sans-serif; }
            QFrame#Sidebar { background-color: #2b2d31; border-right: 1px solid #3f4147; }
            QLineEdit { background-color: #383a40; border: 1px solid #4f545c; border-radius: 4px; padding: 8px; color: white; }
            QPushButton { background-color: #5865f2; color: white; border-radius: 4px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #4752c4; }
            QListWidget { background: #232428; border: none; border-radius: 8px; margin: 10px; }
            QListWidget::item { padding: 15px; border-bottom: 1px solid #2f3136; }
            QListWidget::item:selected { background: #393c43; border-left: 4px solid #5865f2; }
        """)

        # Main Layout using Splitter for Resizing
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- 1. LEFT PANEL: Library & Tools ---
        left_container = QFrame()
        left_layout = QVBoxLayout(left_container)

        self.close_left_btn = QPushButton("")

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste arXiv PDF URL here...")
        left_layout.addWidget(self.url_input)

        self.download_btn = QPushButton("Download & Add to Library")
        self.download_btn.clicked.connect(self.handle_download)
        left_layout.addWidget(self.download_btn)

        self.paper_list = QListWidget()
        self.paper_list.itemClicked.connect(self.load_paper_preview)
        left_layout.addWidget(self.paper_list)

        self.splitter.addWidget(left_container)

        # --- 2. RIGHT PANEL: PDF Preview ---
        self.preview_panel = QWebEngineView()
        self.preview_panel.settings().setAttribute(self.preview_panel.settings().WebAttribute.PluginsEnabled, True)
        self.preview_panel.settings().setAttribute(self.preview_panel.settings().WebAttribute.PdfViewerEnabled, True)

        self.splitter.addWidget(self.preview_panel)
        self.splitter.setStretchFactor(1, 2)  # Make preview wider

        layout.addWidget(self.splitter)
        self.load_papers_from_db()

    def load_last_paper(self):
        arxiv_id = self.db.get_last_view()
        print("load_last_paper: ", arxiv_id)
        if arxiv_id is None:
            return
        self._load_paper_preview_arxiv_id(arxiv_id)


    # --- LOGIC ---
    def handle_download(self):
        url = self.url_input.text().strip()
        if not re.match(r"^https?://arxiv.org/(abs|pdf)/\d{4}.\d{4,5}", url):
            print("Please provide a direct PDF link.")
            return

        url = re.sub(r"abs", "pdf", url)

        arxiv_id = url.split("/")[-1]

        title, authors, abstract = arxiv_scrapper(arxiv_id)
        save_path = os.path.join(FILE_PATH, arxiv_id + ".pdf")

        try:
            # Download file
            self.url_input.clear()
            urllib.request.urlretrieve(url, save_path)

            # Save to DB
            self.db.insert_paper(arxiv_id=arxiv_id,
                                 title=title,
                                 authors=authors,
                                 abstract=abstract,
                                 file_path=save_path)

            self.load_papers_from_db()
        except Exception as e:
            print(f"Error: {e}")

    def load_papers_from_db(self):
        self.paper_list.clear()
        for arxiv_id, title in self.db.get_papers():
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, arxiv_id)
            self.paper_list.addItem(item)

    def load_paper_preview(self, item):
        arxiv_id = item.data(Qt.ItemDataRole.UserRole)
        self._load_paper_preview_arxiv_id(arxiv_id)

    def _load_paper_preview_arxiv_id(self, arxiv_id):
        file_path = self.db.get_paper_path(arxiv_id)
        self.db.update_last_view(arxiv_id)
        file_url = QUrl.fromLocalFile(file_path)
        self.preview_panel.setUrl(file_url)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ResearchHub()
    window.show()
    sys.exit(app.exec())