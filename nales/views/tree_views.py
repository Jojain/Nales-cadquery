from PyQt5.QtCore import QModelIndex, QObject, QPersistentModelIndex, QPoint, Qt
from PyQt5.QtGui import QPalette
from nales.NDS.model import NModel, ParamTableModel
from nales.NDS.interfaces import NArgument
from PyQt5.QtWidgets import (
    QMenu,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QTreeView,
    QWidget,
)
from typing import List, Optional


class MyDelegate(QStyledItemDelegate):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent=parent)

    def paint(self, painter, option: QStyleOptionViewItem, index: QModelIndex):
        if option.state and QStyle.State_Selected:
            optCopy = option
            optCopy.palette.setColor(QPalette.Foreground, Qt.red)

        super().paint(painter, optCopy, index)


class ModelingOpsView(QTreeView):
    def __init__(self, parent: Optional[QWidget] = ...) -> None:
        super().__init__(parent=parent)

        # self.dl = MyDelegate()
        # self.setItemDelegateForRow(0,self.dl)
        # self.actions = []

