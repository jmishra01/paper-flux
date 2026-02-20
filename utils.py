import os
import urllib.request

from bs4 import BeautifulSoup

FILE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "downloads")

if not os.path.exists(FILE_PATH):
    os.makedirs(FILE_PATH)

os.environ["QT_QUICK_BACKEND"] = "software"
os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"


def get_storage_path():
    storage_path = os.path.join(os.getcwd(), "web_profile")
    if not os.path.exists(storage_path):
        os.makedirs(storage_path)

    return storage_path


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

