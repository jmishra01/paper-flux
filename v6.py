import sys
import os
import sqlite3
import shutil
import requests
import xml.etree.ElementTree as ET
import fitz  # PyMuPDF

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QListWidget, QTextEdit,
    QMessageBox, QTreeWidget, QTreeWidgetItem,
    QSplitter, QInputDialog, QMenu,
    QLabel, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage


# ==============================
# DATABASE
# ==============================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("database.db")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            parent_id INTEGER,
            FOREIGN KEY(parent_id) REFERENCES folders(id) ON DELETE CASCADE
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

    def backup(self):
        if os.path.exists("database.db"):
            shutil.copy("database.db", "backup_database.db")

    def add_folder(self, name, parent_id=None):
        self.conn.execute(
            "INSERT INTO folders (name, parent_id) VALUES (?, ?)",
            (name, parent_id))
        self.conn.commit()

    def delete_folder(self, folder_id):
        self.conn.execute("DELETE FROM folders WHERE id=?", (folder_id,))
        self.conn.commit()

    def get_folders(self):
        return self.conn.execute(
            "SELECT id, name, parent_id FROM folders").fetchall()

    def get_paper_count(self, folder_id):
        return self.conn.execute(
            "SELECT COUNT(*) FROM papers WHERE folder_id=?",
            (folder_id,)).fetchone()[0]

    def insert_paper(self, arxiv_id, title, authors,
                     abstract, file_path, folder_id):
        self.conn.execute("""
        INSERT INTO papers (arxiv_id, title, authors,
                            abstract, file_path, notes, folder_id)
        VALUES (?, ?, ?, ?, ?, "", ?)
        """, (arxiv_id, title, authors,
              abstract, file_path, folder_id))
        self.conn.commit()

    def get_papers(self, folder_id, search=""):
        return self.conn.execute("""
        SELECT * FROM papers
        WHERE folder_id=? AND title LIKE ?
        """, (folder_id, f"%{search}%")).fetchall()

    def update_notes(self, paper_id, notes):
        self.conn.execute(
            "UPDATE papers SET notes=? WHERE id=?",
            (notes, paper_id))
        self.conn.commit()


# ==============================
# ARXIV
# ==============================
def fetch_arxiv(arxiv_id):
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    r = requests.get(url)
    root = ET.fromstring(r.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    entry = root.find('atom:entry', ns)

    title = entry.find('atom:title', ns).text.strip()
    abstract = entry.find('atom:summary', ns).text.strip()
    authors = ", ".join(
        a.find('atom:name', ns).text
        for a in entry.findall('atom:author', ns)
    )
    return title, authors, abstract


# ==============================
# DOWNLOAD THREAD
# ==============================
class DownloadThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url, folder_id):
        super().__init__()
        self.url = url
        self.folder_id = folder_id

    def run(self):
        try:
            arxiv_id = self.url.split("/")[-1]
            title, authors, abstract = fetch_arxiv(arxiv_id)

            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            r = requests.get(pdf_url)
            r.raise_for_status()

            os.makedirs("downloads", exist_ok=True)
            path = f"downloads/{arxiv_id}.pdf"

            with open(path, "wb") as f:
                f.write(r.content)

            self.finished.emit({
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "file_path": path,
                "folder_id": self.folder_id
            })
        except Exception as e:
            self.error.emit(str(e))


# ==============================
# MAIN WINDOW
# ==============================
class ResearchManager(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Research Manager (PyMuPDF)")
        self.setGeometry(100, 100, 1300, 800)

        self.db = Database()
        self.current_folder_id = None

        self.pdf_doc = None
        self.current_page = 0
        self.zoom = 1.5

        self.init_ui()
        self.apply_dark_theme()
        self.load_folders()

    # ---------------- UI ----------------
    def init_ui(self):
        splitter = QSplitter()

        # Folder Tree
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.itemClicked.connect(self.folder_selected)
        splitter.addWidget(self.folder_tree)

        # Right Panel
        right = QWidget()

        left_layout = QHBoxLayout()


        paper_layout = QVBoxLayout()



        self.paper_list = QListWidget()
        self.paper_list.itemClicked.connect(self.show_details)
        paper_layout.addWidget(self.paper_list)

        self.abstract_view = QTextEdit()
        self.abstract_view.setReadOnly(True)
        paper_layout.addWidget(self.abstract_view)

        self.notes = QTextEdit()
        paper_layout.addWidget(self.notes)

        left_layout.addLayout(paper_layout)


        pdf_layout = QVBoxLayout()

        # PDF Viewer
        self.pdf_label = QLabel()
        self.pdf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.pdf_label)
        pdf_layout.addWidget(self.scroll)

        # PDF Controls
        controls = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Prev")
        self.next_btn = QPushButton("Next ▶")
        self.zoom_in_btn = QPushButton("Zoom +")
        self.zoom_out_btn = QPushButton("Zoom -")

        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_out_btn.clicked.connect(self.zoom_out)

        controls.addWidget(self.prev_btn)
        controls.addWidget(self.next_btn)
        controls.addWidget(self.zoom_in_btn)
        controls.addWidget(self.zoom_out_btn)

        pdf_layout.addLayout(controls)

        left_layout.addLayout(pdf_layout)

        right.setLayout(left_layout)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 3)

        self.setCentralWidget(splitter)

    # ---------------- Theme ----------------
    def apply_dark_theme(self):
        self.setStyleSheet("""
        QMainWindow { background-color: #1e1e1e; }
        QWidget { background-color: #1e1e1e; color: white; }
        QListWidget, QTextEdit {
            background-color: #252526;
            border: 1px solid #333;
        }
        QPushButton {
            background-color: #3c3c3c;
            border: 1px solid #555;
            padding: 5px;
        }
        QPushButton:hover { background-color: #505050; }
        """)

    # ---------------- PDF Rendering ----------------
    def load_pdf(self, path):
        self.pdf_doc = fitz.open(path)
        self.current_page = 0
        self.render_page()

    def render_page(self):
        if not self.pdf_doc:
            return

        page = self.pdf_doc[self.current_page]
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat)

        img = QImage(pix.samples, pix.width,
                     pix.height, pix.stride,
                     QImage.Format.Format_RGB888)

        self.pdf_label.setPixmap(QPixmap.fromImage(img))

    def next_page(self):
        if self.pdf_doc and self.current_page < len(self.pdf_doc) - 1:
            self.current_page += 1
            self.render_page()

    def prev_page(self):
        if self.pdf_doc and self.current_page > 0:
            self.current_page -= 1
            self.render_page()

    def zoom_in(self):
        self.zoom += 0.2
        self.render_page()

    def zoom_out(self):
        if self.zoom > 0.5:
            self.zoom -= 0.2
            self.render_page()

    # ---------------- Folder & Paper ----------------
    def load_folders(self):
        self.folder_tree.clear()
        folders = self.db.get_folders()
        for fid, name, parent_id in folders:
            item = QTreeWidgetItem([name])
            item.setData(0, Qt.ItemDataRole.UserRole, fid)
            self.folder_tree.addTopLevelItem(item)

    def folder_selected(self, item):
        self.current_folder_id = item.data(0, Qt.ItemDataRole.UserRole)
        self.load_papers()

    def load_papers(self):
        if not self.current_folder_id:
            return
        self.papers = self.db.get_papers(self.current_folder_id)
        self.paper_list.clear()
        for p in self.papers:
            self.paper_list.addItem(p[2])

    def show_details(self):
        index = self.paper_list.currentRow()
        self.current_paper = self.papers[index]
        self.abstract_view.setText(self.current_paper[4])
        self.notes.setText(self.current_paper[6])
        self.load_pdf(self.current_paper[5])


# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ResearchManager()
    window.show()
    sys.exit(app.exec())
