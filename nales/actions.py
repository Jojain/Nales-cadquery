from PyQt5.QtWidgets import QAction


class FitViewAction(QAction):
    def __init__(self, parent):
        super().__init__(parent)
        self.setShortcut("f")
