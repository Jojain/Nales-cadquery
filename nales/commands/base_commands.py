from typing import TYPE_CHECKING, Any

from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import QUndoCommand

from nales.NDS.interfaces import NOperation, NPart, NShape

if TYPE_CHECKING:
    from nales.NDS.model import NModel


class BaseCommand(QUndoCommand):
    def __init__(self):
        super().__init__()
        self.setText(self.__class__.__name__)


class AddTreeItem(BaseCommand):
    def __init__(self, model: "NModel", item_name: str, item_obj: Any = None):
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
