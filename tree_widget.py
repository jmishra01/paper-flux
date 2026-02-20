from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QApplication

from database import Folder


class TreeWidget(QTreeWidget):

    ItemChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super(TreeWidget, self).__init__(parent)
        self.parent = parent
        self._init()

    def _init(self):
        self.setHeaderHidden(True)
        self.setColumnCount(1)
        self.setIndentation(15)

        self.itemClicked.connect(self.on_clicked_handler)

        for (folder, ) in Folder.get_all_folders():
            _ = self.get_category(folder)

    def on_clicked_handler(self, item):
        if paper_id := item.data(0, Qt.ItemDataRole.UserRole):
            self.ItemChanged.emit(paper_id)

    def get_category(self, title, expand: bool = False) -> QTreeWidgetItem:
        style = QApplication.style()
        category = QTreeWidgetItem(self, [title])
        category.setIcon(0, style.standardIcon(style.StandardPixmap.SP_DirIcon))
        category.setExpanded(expand)
        return category