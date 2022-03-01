from functools import wraps
from typing import Any, TYPE_CHECKING
from PyQt5.QtWidgets import QUndoCommand
from PyQt5.QtCore import QModelIndex

from nales.NDS.interfaces import NOperation, NPart, NShape
from nales.widgets.msg_boxs import StdErrorMsgBox

if TYPE_CHECKING:
    from nales.NDS.model import NModel


class BaseCommand(QUndoCommand):
    def __init__(self):
        super().__init__()
        self.setText(self.__class__.__name__)


class AddTreeItem(BaseCommand):
    def __init__(self, model: "NModel", item_name: str, item_obj: Any):
        super().__init__()
        self.model = model
        self.item_name = item_name
        self.item_obj = item_obj


class DeleteTreeItem(BaseCommand):
    def __init__(self, model: "NModel", index: QModelIndex):
        super().__init__()
        self.model = model
        self.node = index.internalPointer()
        if isinstance(self.node, NPart):
            self.item_obj = self.node.part
        elif isinstance(self.node, NOperation):
            self.item_obj = self.node.parent.part
        elif isinstance(self.node, NShape):
            self.item_obj = self.node.shape
