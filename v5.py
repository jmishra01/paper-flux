import sys
import os
import sqlite3
import shutil
import webbrowser

import requests
import xml.etree.ElementTree as ET

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QListWidget, QTextEdit,
    QMessageBox, QTreeWidget, QTreeWidgetItem,
    QSplitter, QInputDialog, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView


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
            name TEXT NOT NULL,
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

    # -------- Folder --------
    def add_folder(self, name, parent_id=None):
        self.conn.execute(
            "INSERT INTO folders (name, parent_id) VALUES (?, ?)",
            (name, parent_id)
        )
        self.conn.commit()

    def delete_folder(self, folder_id):
        self.conn.execute("DELETE FROM folders WHERE id=?", (folder_id,))
        self.conn.commit()

    def get_folders(self):
        return self.conn.execute(
            "SELECT id, name, parent_id FROM folders"
        ).fetchall()

    def get_paper_count(self, folder_id):
        return self.conn.execute(
            "SELECT COUNT(*) FROM papers WHERE folder_id=?",
            (folder_id,)
        ).fetchone()[0]

    # -------- Papers --------
    def insert_paper(self, arxiv_id, title,
                     authors, abstract,
                     file_path, folder_id):
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

    def move_paper(self, paper_id, new_folder_id):
        self.conn.execute(
            "UPDATE papers SET folder_id=? WHERE id=?",
            (new_folder_id, paper_id)
        )
        self.conn.commit()

    def update_notes(self, paper_id, notes):
        self.conn.execute(
            "UPDATE papers SET notes=? WHERE id=?",
            (notes, paper_id)
        )
        self.conn.commit()


# ==============================
# ARXIV FETCH
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
        self.setWindowTitle("Research Knowledge Manager")
        self.setGeometry(100, 100, 1300, 750)

        self.db = Database()
        self.current_folder_id = None

        self.init_ui()
        self.apply_dark_theme()
        self.load_folders()

    # ---------------- UI ----------------
    def init_ui(self):
        splitter = QSplitter()

        # LEFT: Folder Tree
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.itemClicked.connect(self.folder_selected)
        self.folder_tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(
            self.folder_menu)

        splitter.addWidget(self.folder_tree)

        # RIGHT PANEL
        right = QWidget()
        layout = QVBoxLayout()

        top = QHBoxLayout()
        self.new_folder_btn = QPushButton("New Folder")
        self.new_folder_btn.clicked.connect(self.create_top_folder)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste arXiv URL")

        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.download_paper)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search")
        self.search_input.textChanged.connect(self.load_papers)

        top.addWidget(self.new_folder_btn)
        top.addWidget(self.url_input)
        top.addWidget(self.download_btn)
        top.addWidget(self.search_input)

        layout.addLayout(top)

        self.paper_list = QListWidget()
        self.paper_list.itemClicked.connect(self.show_details)
        layout.addWidget(self.paper_list)

        self.abstract_view = QTextEdit()
        self.abstract_view.setReadOnly(True)
        layout.addWidget(self.abstract_view)

        # self.notes = QTextEdit()
        # self.notes.setPlaceholderText("Notes...")
        # layout.addWidget(self.notes)

        self.pdf_view = QWebEngineView()
        layout.addWidget(self.pdf_view)

        right.setLayout(layout)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 3)

        self.setCentralWidget(splitter)

    # ---------------- Theme ----------------
    def apply_dark_theme(self):
        self.setStyleSheet("""
        QMainWindow { background-color: #1e1e1e; }
        QWidget { background-color: #1e1e1e; color: white; }
        QTreeWidget, QListWidget, QTextEdit {
            background-color: #252526;
            border: 1px solid #333;
        }
        QPushButton {
            background-color: #3c3c3c;
            border: 1px solid #555;
            padding: 5px;
        }
        QPushButton:hover { background-color: #505050; }
        QLineEdit {
            background-color: #2d2d2d;
            border: 1px solid #444;
            padding: 4px;
        }
        """)

    # ---------------- Folder Logic ----------------
    def create_top_folder(self):
        name, ok = QInputDialog.getText(
            self, "New Folder", "Folder Name:")
        if ok and name:
            self.db.add_folder(name)
            self.load_folders()

    def folder_menu(self, position):
        item = self.folder_tree.itemAt(position)
        if not item:
            return

        menu = QMenu()
        add_sub = menu.addAction("Add Subfolder")
        delete = menu.addAction("Delete Folder")

        action = menu.exec(
            self.folder_tree.viewport().mapToGlobal(position))

        folder_id = item.data(0, Qt.ItemDataRole.UserRole)

        if action == add_sub:
            name, ok = QInputDialog.getText(
                self, "New Subfolder", "Folder Name:")
            if ok and name:
                self.db.add_folder(name, folder_id)
                self.load_folders()

        if action == delete:
            self.db.delete_folder(folder_id)
            self.load_folders()

    def load_folders(self):
        self.folder_tree.clear()
        folders = self.db.get_folders()
        folder_map = {}

        for fid, name, parent_id in folders:
            count = self.db.get_paper_count(fid)
            item = QTreeWidgetItem([f"{name} ({count})"])
            item.setData(0, Qt.ItemDataRole.UserRole, fid)
            folder_map[fid] = item

        for fid, name, parent_id in folders:
            item = folder_map[fid]
            if parent_id and parent_id in folder_map:
                folder_map[parent_id].addChild(item)
            else:
                self.folder_tree.addTopLevelItem(item)

    def folder_selected(self, item):
        self.current_folder_id = item.data(
            0, Qt.ItemDataRole.UserRole)
        self.load_papers()

    # ---------------- Paper Logic ----------------
    def load_papers(self):
        if not self.current_folder_id:
            return

        search = self.search_input.text()
        self.papers = self.db.get_papers(
            self.current_folder_id, search)

        self.paper_list.clear()
        for p in self.papers:
            self.paper_list.addItem(p[2])

    def show_details(self):
        index = self.paper_list.currentRow()
        self.current_paper = self.papers[index]
        print(self.current_paper)

        self.abstract_view.setText(self.current_paper[4])
        # self.notes.setText(self.current_paper[6])

        self.load_pdf(self.current_paper[5])


    def load_pdf(self, file_path):
        if not os.path.exists(file_path):
            return

        file_url = QUrl.fromLocalFile(os.path.abspath(file_path)).toString()

        webbrowser.open(file_url)

        # print(file_url)
        #
        # html = f"""
        # <html>
        #     <body style="margin:0; background-color:#1e1e1e;">
        #         <embed src="{file_url}" type="application/pdf"
        #                width="100%" height="100%"/>
        #     </body>
        # </html>
        # """
        #
        # self.pdf_view.setHtml(html)

    def download_paper(self):
        if not self.current_folder_id:
            QMessageBox.warning(
                self, "Error", "Select a folder")
            return

        url = self.url_input.text().strip()
        self.thread = DownloadThread(
            url, self.current_folder_id)
        self.thread.finished.connect(
            self.download_complete)
        self.thread.error.connect(
            self.download_error)
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
        self.load_folders()

    def download_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

    def closeEvent(self, event):
        self.db.backup()
        event.accept()


# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ResearchManager()
    window.show()
    sys.exit(app.exec())
