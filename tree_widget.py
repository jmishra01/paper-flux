from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QApplication

from database import Paper, Folder


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
        self.load_categories()

    def on_clicked_handler(self, item):
        if paper_id := item.data(0, Qt.ItemDataRole.UserRole):
            self.ItemChanged.emit(paper_id)

    def get_category(self, title) -> QTreeWidgetItem:
        style = QApplication.style()
        category = QTreeWidgetItem(self, [title])
        category.setIcon(0, style.standardIcon(style.StandardPixmap.SP_DirIcon))
        category.setExpanded(True)
        return category

    def load_categories(self):
        for (folder, ) in Folder.get_all_folders():
            _ = self.get_category(folder)

    def get_selected_category(self):
        if ((items := self.selectedItems())
                and (item := items[0])
                and (item_text := item.text(0))):
            folder_id = Folder.get_folder_id_for_title(item_text)
            if folder_id is None:
                folder_id = Paper.get_folder_id_for_title(item_text)
                if folder_id is None:
                    return 1
            return folder_id[0]
        return 1