from PyQt5.QtWidgets import (
    QWidget,
    QSpacerItem,
    QSizePolicy,
    QHBoxLayout,
    QVBoxLayout,
    QToolButton,
    QPushButton,
    QToolBar,
    QTabWidget,
    QLabel,
    QAction,
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPainter


class RibbonPane(QWidget):
    def __init__(self, parent, name):
        super().__init__(parent)
        # self.setStyleSheet(get_stylesheet("ribbonPane"))
        horizontal_layout = QHBoxLayout()
        horizontal_layout.setSpacing(0)
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(horizontal_layout)
        vertical_widget = QWidget(self)
        horizontal_layout.addWidget(vertical_widget)
        horizontal_layout.addWidget(RibbonSeparator(self))
        vertical_layout = QVBoxLayout()
        vertical_layout.setSpacing(0)
        vertical_layout.setContentsMargins(0, 0, 0, 0)
        vertical_widget.setLayout(vertical_layout)
        label = QLabel(name)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color:#666;")
        content_widget = QWidget(self)
        vertical_layout.addWidget(content_widget)
        vertical_layout.addWidget(label)
        content_layout = QHBoxLayout()
        content_layout.setAlignment(Qt.AlignLeft)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)
        self.contentLayout = content_layout
        content_widget.setLayout(content_layout)

    def add_ribbon_widget(self, widget):
        self.contentLayout.addWidget(widget, 0, Qt.AlignTop)


class RibbonSeparator(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.setMaximumHeight(80)
        self.setMinimumWidth(1)
        self.setMaximumWidth(1)
        self.setLayout(QHBoxLayout())

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        qp.fillRect(event.rect(), Qt.lightGray)
        qp.end()


class RibbonButton(QToolButton):
    def __init__(self, parent, action: QAction):
        super().__init__(parent)
        sc = 1
        # sc = gui_scale()
        self._actionOwner = action
        self.update_button_status_from_action()
        self.clicked.connect(self._actionOwner.trigger)
        self._actionOwner.changed.connect(self.update_button_status_from_action)

        self.setMaximumWidth(80 * sc)
        self.setMinimumWidth(50 * sc)
        self.setMinimumHeight(75 * sc)
        self.setMaximumHeight(80 * sc)
        # self.setStyleSheet(get_stylesheet("ribbonButton"))
        self.setToolButtonStyle(3)
        self.setIconSize(QSize(32 * sc, 32 * sc))

    def update_button_status_from_action(self):
        self.setText(self._actionOwner.text())
        self.setStatusTip(self._actionOwner.statusTip())
        self.setToolTip(self._actionOwner.toolTip())
        self.setIcon(self._actionOwner.icon())
        self.setEnabled(self._actionOwner.isEnabled())
        self.setCheckable(self._actionOwner.isCheckable())
        self.setChecked(self._actionOwner.isChecked())


class RibbonTab(QWidget):
    def __init__(self, parent, name):
        super().__init__(parent)
        layout = QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignLeft)

    def add_ribbon_pane(self, name):
        ribbon_pane = RibbonPane(self, name)
        self.layout().addWidget(ribbon_pane)
        return ribbon_pane

    def add_spacer(self):
        self.layout().addSpacerItem(QSpacerItem(1, 1, QSizePolicy.MinimumExpanding))
        self.layout().setStretch(self.layout().count() - 1, 1)


class RibbonWidget(QToolBar):
    def __init__(self, parent):
        super().__init__(parent)
        # self.setStyleSheet(get_stylesheet("ribbon"))
        self.setObjectName("ribbonWidget")
        self.setWindowTitle("Ribbon")
        self._ribbon_widget = QTabWidget(self)
        self._ribbon_widget.setMaximumHeight(120)
        self._ribbon_widget.setMinimumHeight(110)
        self.setMovable(False)
        self.addWidget(self._ribbon_widget)

    def add_ribbon_tab(self, name):
        ribbon_tab = RibbonTab(self, name)
        ribbon_tab.setObjectName("tab_" + name)
        self._ribbon_widget.addTab(ribbon_tab, name)
        return ribbon_tab

    def set_active(self, name):
        self.setCurrentWidget(self.findChild("tab_" + name))
