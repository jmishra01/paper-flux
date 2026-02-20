import os
import re
import sqlite3
import urllib.request as request
from uuid import uuid4

import requests
from requests.exceptions import HTTPError

from custom_widget import CategoryDialog
from database import Paper, Folder
from utils import arxiv_scrapper, FILE_PATH


def save_open_page(url: str, folder_id=None):
    category_dialog = CategoryDialog()

    if category_dialog.exec():
        if not category_dialog.close_with_selected_category:
            return
        category_title = category_dialog.combo.currentText()
        folder_id = Folder.get_folder_id_for_title(category_title)[0]

    if re.search(r"^https?://medium.com", url):
        save_medium_webpage(url, folder_id=folder_id)
    elif re.search(r"^https?://arxiv.org", url):
        save_arxiv_research_paper(url, folder_id=folder_id)
    elif re.search(r"^https?://towardsdatascience.com", url):
        save_medium_webpage(url, folder_id=folder_id)
    else:
        save_document_webpage(url, folder_id=folder_id)

def save_document_webpage(url: str, folder_id=None):
    try:
        response = requests.get(url, stream=True, timeout=30,
                                headers={
                                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Safari/605.1.15",
                                    "Accept-Language": "en-US,en;q=0.5",
                                    "Cache-Control": "no-cache",
                                    "Connection": "keep-alive",
                                    "Accept-Encoding": "gzip,deflate,br,zstd",
                                    "Accept": "*/*",
                                })
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()

        if "application/pdf" in content_type:
            filename = url.split("/")[-1]
            if not filename.endswith(".pdf"):
                filename = filename + ".pdf"
            save_path = os.path.join(FILE_PATH,  filename)
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size= 8192):
                    if chunk:
                        f.write(chunk)

            Paper.insert_row(
                arxiv_id=str(uuid4()),
                title=filename,
                authors=None,
                abstract=None,
                file_path=save_path,
                website_url=url,
                folder_id=folder_id
            )
    except HTTPError as e:
        print(f"Error: {e}")
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")


def save_medium_webpage(url: str, folder_id=None):
    url = url.rstrip("/")
    title = url.split("/")[-1].replace('-', ' ').title()

    article_id = str(uuid4())

    Paper.insert_row(
        arxiv_id=article_id,
        title=title,
        authors=None,
        abstract=None,
        file_path=url,
        website_url=url,
        folder_id=folder_id
    )


def save_arxiv_research_paper(url: str, folder_id=None):
    if not re.match(r"^https?://arxiv.org/(abs|pdf)/\d{4}.\d{4,5}", url):
        print("Please provide a direct PDF link.")
        return

    url = re.sub(r"abs", "pdf", url)
    arxiv_id = url.split("/")[-1]

    title, authors, abstract = arxiv_scrapper(arxiv_id)
    save_path = os.path.join(FILE_PATH, arxiv_id + ".pdf")

    try:
        request.urlretrieve(url, save_path)

        Paper.insert_row(
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
            abstract=abstract,
            file_path=save_path,
            website_url=url,
            folder_id=folder_id
        )
    except Exception as e:
        print(f"Error: {e}")
