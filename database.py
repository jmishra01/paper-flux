import datetime
import os
import shutil
import sqlite3
from typing import Optional

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

    def create_tables(self):
        self.conn.executescript("""
        
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arxiv_id TEXT not null unique,
            title TEXT not null unique,
            authors TEXT,
            abstract TEXT,
            file_path TEXT not null unique,
            website_url TEXT,
            added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_view DATETIME,
            folder_id INTEGER NOT NULL default 1,
            is_active BOOLEAN NOT NULL default 1,
            FOREIGN KEY (folder_id) REFERENCES folders (id)
        );
        
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_name TEXT not null unique,
            parent_folder_id integer
        );
        
        
        CREATE TABLE IF NOT EXISTS website (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            website_name TEXT not null unique,
            website_url TEXT not null,
            added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        
        """)
        self.conn.commit()

    def execute_with_args(self, query, /, *args):
        self.conn.execute(query, *args)
        self.conn.commit()


DATABASE = Database()

class Paper:

    @staticmethod
    def default_entries():
        for (website_name, website_url) in (
                ('Medium', 'https://medium.com'),
                ('TowardsDataScience', 'https://towardsdatascience.com'),
                ('ArXiv', 'https://arxiv.org'),
                ('Machine Learning Mastery', 'https://machinelearningmastery.com'),
        ):
            try:
                Paper.insert_row(
                    arxiv_id=website_url,
                    title=website_name,
                    authors=None,
                    abstract=None,
                    file_path=website_url,
                    website_url=website_url,
                    folder_id=2
                )
            except Exception as e:
                pass

    @staticmethod
    def insert_row(arxiv_id: str,
                   title: str,
                   authors: Optional[str],
                   abstract: Optional[str],
                   file_path: str,
                   website_url: Optional[str],
                   folder_id: int):
        query = """
        INSERT INTO papers (arxiv_id, title, authors, abstract, file_path, website_url, folder_id)
        values ( ?, ?, ?, ?, ?, ?, ?);
        """
        DATABASE.execute_with_args(query, (arxiv_id, title, authors, abstract, file_path, website_url, folder_id))

    @staticmethod
    def get_all_papers():
        query = """
        SELECT p.id, p.title, f.folder_name, p.file_path
        FROM papers p
        INNER JOIN folders f ON p.folder_id = f.id
        ORDER BY p.last_view DESC, p.added_at DESC;
        """
        return DATABASE.conn.execute(query).fetchall()


    @staticmethod
    def search_paper(title: str):
        query = """
        SELECT p.id, p.title, f.folder_name, p.file_path
        FROM papers p
        INNER JOIN folders f ON p.folder_id = f.id
        WHERE p.title LIKE ?
        ORDER BY p.last_view DESC, p.added_at DESC;
        """
        return DATABASE.conn.execute(query, (f'%{title}%', )).fetchall()

    @staticmethod
    def get_url(paper_id: str):
        query = """
        SELECT website_url FROM papers WHERE id = ? LIMIT 1;
        """
        return DATABASE.conn.execute(query, (paper_id,)).fetchone()


    @staticmethod
    def soft_delete_row(paper_id: str):
        query = """
        DELETE FROM papers WHERE id = ?
        """
        DATABASE.execute_with_args(query, (paper_id,))

    @staticmethod
    def hard_delete_row(paper_id: str):
        query = """
        UPDATE papers SET is_active = FALSE WHERE id = ?
        """
        DATABASE.execute_with_args(query, (paper_id,))

    @staticmethod
    def update_is_active(arxiv_id: str, is_active: bool):
        query = """
        UPDATE papers SET is_active = ? WHERE arxiv_id = ?
        """
        DATABASE.execute_with_args(query, (is_active, arxiv_id))

    @staticmethod
    def get_paper_id_of_title(title: str):
        query = """
        SELECT id FROM papers WHERE title = ? LIMIT 1
        """
        return DATABASE.conn.execute(query, (title,)).fetchone()

    @staticmethod
    def change_category(paper_id: str, folder_id: int):
        query = """
        UPDATE papers SET folder_id = ? WHERE id = ?
        """
        DATABASE.execute_with_args(query, (folder_id, paper_id))

    @staticmethod
    def get_last_viewed_paper():
        query = """
        SELECT id from papers ORDER BY last_view DESC, added_at DESC LIMIT 1
        """
        return DATABASE.conn.execute(query).fetchone()

    @staticmethod
    def get_paper_path(paper_id):
        query = """
        SELECT file_path FROM papers WHERE id = ?
        """
        return DATABASE.conn.execute(query, (paper_id,)).fetchone()

    @staticmethod
    def update_paper_last_view_date(paper_id: str):
        query = """
        UPDATE papers SET last_view = ? WHERE id = ?
        """
        DATABASE.execute_with_args(query, (datetime.datetime.now(), paper_id))

    @staticmethod
    def get_paper_using_id(paper_id):
        query = """
        SELECT p.id, p.arxiv_id, p.title, f.folder_name, p.file_path 
        FROM papers p
        INNER JOIN folders f
        ON p.folder_id = f.id
        WHERE p.id = ?
        LIMIT 1
        """
        return DATABASE.conn.execute(query, (paper_id,)).fetchone()

    @staticmethod
    def get_folder_id_for_title(title: str):
        query = """
        SELECT folder_id FROM papers WHERE title = ?
        """
        return DATABASE.conn.execute(query, (title,)).fetchone()

    @staticmethod
    def change_folder_id(folder_id: int, new_folder_id: int):
        query = """
        UPDATE papers SET folder_id = ? WHERE folder_id = ?
        """
        DATABASE.execute_with_args(query, (new_folder_id, folder_id))

    @staticmethod
    def update_folder_id(paper_id, folder_id: int):
        query = """
        UPDATE papers SET folder_id = ? WHERE id = ?
        """
        DATABASE.execute_with_args(query, (folder_id, paper_id))


    @staticmethod
    def update_paper_title(paper_id: str, title: str):
        query = """
        UPDATE papers SET title = ? WHERE id = ?
        """
        DATABASE.execute_with_args(query, (title, paper_id ))



class Folder:

    @staticmethod
    def default_entries():
        for folder_name in ('Read-List', 'Website'):
            try:
                Folder.insert_row(folder_name, 0)
            except (sqlite3.OperationalError, sqlite3.IntegrityError):
                pass

    @staticmethod
    def insert_row(folder_name: str, parent_folder_id: int):
        query = """
        INSERT INTO folders (folder_name, parent_folder_id)
        VALUES (?, ?);
        """
        DATABASE.execute_with_args(query, (folder_name, parent_folder_id))

    @staticmethod
    def get_all_folders():
        query = """
        SELECT folder_name FROM folders
        """
        return DATABASE.conn.execute(query).fetchall()

    @staticmethod
    def get_folder_id_for_title(title: str):
        query = """
        SELECT id FROM folders WHERE folder_name = ? LIMIT 1
        """
        return DATABASE.conn.execute(query, (title,)).fetchone()

    @staticmethod
    def remove_folder(folder_id: int):
        query = """
        DELETE FROM folders WHERE id = ?
        """
        DATABASE.execute_with_args(query, (folder_id,))

Folder.default_entries()
Paper.default_entries()