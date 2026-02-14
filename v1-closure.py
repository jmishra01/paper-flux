import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, Qt, QSize


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Animated Sidebar")
        self.resize(800, 500)

        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Sidebar Setup
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(200)  # Initial width
        self.sidebar.setStyleSheet("background-color: #2c3e50; color: white;")

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.addWidget(QLabel("SIDEBAR MENU"))
        sidebar_layout.addWidget(QPushButton("Dashboard"))
        sidebar_layout.addWidget(QPushButton("Messages"))
        sidebar_layout.addStretch()

        # 2. Main Content Area
        self.content_area = QWidget()
        self.content_area.setStyleSheet("background-color: #ecf0f1;")
        content_layout = QVBoxLayout(self.content_area)

        # Toggle Button (the "Collapse" trigger)
        self.toggle_btn = QPushButton("☰ Toggle Sidebar")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)

        content_layout.addWidget(self.toggle_btn)
        content_layout.addWidget(QLabel("Main Content Area"), alignment=Qt.AlignmentFlag.AlignCenter)

        # Add widgets to main layout
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_area)

    def toggle_sidebar(self):
        # Determine target width
        min_w, max_w = 40, 200
        width = self.sidebar.width()
        new_width = min_w if width >= max_w else max_w

        # Create the animation
        self.animation = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.animation.setDuration(300)  # milliseconds
        self.animation.setStartValue(width)
        self.animation.setEndValue(new_width)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuart)  # Smooth ease

        # Also sync maximumWidth so the layout doesn't fight the animation
        self.animation.valueChanged.connect(lambda val: self.sidebar.setMaximumWidth(val))

        self.animation.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

