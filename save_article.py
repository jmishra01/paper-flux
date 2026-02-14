import os
import re
import urllib.request as request
from uuid import uuid4

from custom_widget import CategoryDialog
from database import DATABASE
from utils import arxiv_scrapper, FILE_PATH


def save_open_page(url: str, folder_id=None):
    category_dialog = CategoryDialog()
    if category_dialog.exec():
        category_title = category_dialog.combo.currentText()
        folder_id = DATABASE.get_folder_id(category_title)[0]

    if re.search(r"^https?://medium.com", url):
        save_medium_webpage(url, folder_id=folder_id)
    elif re.search(r"^https?://arxiv.org", url):
        save_arxiv_research_paper(url, folder_id=folder_id)
    elif re.search(r"^https?://towardsdatascience.com", url):
        save_medium_webpage(url, folder_id=folder_id)


def save_medium_webpage(url: str, folder_id=None):
    url = url.rstrip("/")
    title = url.split("/")[-1].replace('-', ' ').title()

    article_id = str(uuid4())
    DATABASE.insert_paper(arxiv_id=article_id, title=title, authors=None, abstract=None, file_path=url,
                          folder_id=folder_id)


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
        DATABASE.insert_paper(arxiv_id=arxiv_id, title=title, authors=authors, abstract=abstract,
                              file_path=save_path, folder_id=folder_id)

    except Exception as e:
        print(f"Error: {e}")
