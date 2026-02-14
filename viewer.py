from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

from utils import get_storage_path


class Viewer(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.init()

    def init(self):
        web_engine_page = QWebEnginePage(self.get_profile(), self)

        # Settings
        settings = web_engine_page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        self.setPage(web_engine_page)

    def get_profile(self):
        storage_path = get_storage_path()

        profile = QWebEngineProfile("MediumProfile", self)
        profile.setPersistentStoragePath(storage_path)
        profile.setCachePath(storage_path)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)

        return profile

