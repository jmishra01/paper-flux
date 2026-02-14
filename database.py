import datetime
import os
import shutil
import sqlite3

DB_NAME = "research_library.db"

# ==============================
# DATABASE
# ==============================
def backup():
    if os.path.exists(DB_NAME):
        shutil.copy(DB_NAME, "backup_" + DB_NAME)


class Database:
    def __init__(self):
        backup()
        self.conn = sqlite3.connect(DB_NAME)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()
        self.default_folder()

    def create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arxiv_id TEXT not null unique,
            title TEXT,
            authors TEXT,
            abstract TEXT,
            file_path TEXT,
            added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_view DATETIME,
            folder_id INTEGER NOT NULL default 1,
            FOREIGN KEY (folder_id) REFERENCES folders (id)
        );

        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_name TEXT not null unique,
            parent_folder_id integer
        );
        """)
        self.conn.commit()

    def default_folder(self):
        try:
            self.insert_folder('Read-List')
        except (sqlite3.OperationalError, sqlite3.IntegrityError):
            pass

    # -------- Papers --------
    def insert_paper(self, arxiv_id, title,
                     authors, abstract,
                     file_path, folder_id):
        if title is None or len(title) == 0:
            raise Exception("Title cannot be empty")

        self.conn.execute("""
        INSERT INTO papers (arxiv_id, title, authors,
                            abstract, file_path, folder_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (arxiv_id, title, authors,
              abstract, file_path, folder_id
              ))
        self.conn.commit()

    def get_paper_id(self, title):
        return self.conn.execute("""
        SELECT id FROM papers WHERE title = ?
        """, (title,)).fetchone()

    def remove_paper_using_arxiv_id(self, paper_id):
        self.conn.execute("""
        DELETE FROM papers WHERE id = ?
        """, (paper_id,))
        self.conn.commit()

    def update_folder_in_paper(self, arxiv_id, folder_id):
        self.conn.execute("""
        UPDATE papers SET folder_id = ? WHERE arxiv_id = ?
        """, (folder_id, arxiv_id))
        self.conn.commit()

    def get_folder_id_from_title(self, title: str):
        return self.conn.execute("""
        SELECT folder_id FROM papers WHERE title = ?
        """, (title,)).fetchone()

    def update_paper_title(self, arxiv_id, title):
        self.conn.execute("""
        UPDATE papers SET title = ? WHERE arxiv_id = ?
        """, (title, arxiv_id))
        self.conn.commit()

    def update_last_view(self, arxiv_id):
        self.conn.execute(" UPDATE papers SET last_view = ? WHERE arxiv_id = ? ",
                          (datetime.datetime.now(), arxiv_id))
        self.conn.commit()

    def get_papers(self, search=""):
        return self.conn.execute("""
        SELECT p.arxiv_id, p.title, f.folder_name, p.file_path FROM papers p
        INNER JOIN folders f ON p.folder_id = f.id
        WHERE title LIKE ?
        """, (f"%{search}%",)).fetchall()

    def get_papers_using_id(self, arxiv_id):
        return self.conn.execute("""
        SELECT p.arxiv_id, p.title, f.folder_name, p.file_path FROM papers p
        INNER JOIN folders f ON p.folder_id = f.id
        WHERE arxiv_id = ?
        LIMIT 1
        """, (arxiv_id,)).fetchone()

    def get_paper_path(self, arxiv_id):
        return self.conn.execute("""
        SELECT file_path FROM papers WHERE arxiv_id = ?
        """, (arxiv_id,)).fetchone()[0]

    def get_last_view_paper(self):
        return self.conn.execute("""
        SELECT arxiv_id FROM papers
        ORDER BY last_view DESC, added_at DESC
        LIMIT 1""").fetchone()

    def change_folder_id(self, previous_id: int, folder_id: int):
        self.conn.execute("""
        UPDATE papers SET folder_id = ? WHERE folder_id = ?
        """, (folder_id, previous_id))
        self.conn.commit()


    # ===========================================================
    # Folder
    # ===========================================================

    def insert_folder(self, folder_name: str, parent_folder_id=0):
        self.conn.execute("""
        INSERT INTO folders (folder_name, parent_folder_id)
        VALUES (?, ?)
        """, (folder_name, parent_folder_id))
        self.conn.commit()

    def get_all_folder(self):
        return self.conn.execute("""select folder_name from folders""").fetchall()

    def get_folder_id(self, folder_name: str):
        return self.conn.execute("""
        SELECT id FROM folders WHERE folder_name = ?
        """, (folder_name,)).fetchone()

    def remove_folder(self, folder_id: int):
        self.conn.execute("""
        DELETE FROM folders WHERE id = ?
        """, (folder_id,))
        self.conn.commit()



DATABASE = Database()
