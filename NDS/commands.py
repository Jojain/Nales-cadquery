from typing import Any, List
from PyQt5.QtWidgets import QUndoCommand
from PyQt5.QtCore import Qt, QModelIndex
from nales_alpha.exceptions import CannotDelete
from nales_alpha.NDS.interfaces import NArgument, NOperation

class BaseCommand(QUndoCommand):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.setText(self.__class__.__name__)

class DeleteCommand(BaseCommand):
    # Abstract class to implement deletion
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class DeleteTreeItem(DeleteCommand):
    def __init__(self, model, index: QModelIndex):
        super().__init__()
        self.model = model        
        self.index = index[0] if len(index) != 0 else QModelIndex()
        self.node = model.data(self.index, Qt.EditRole)

    def redo(self) -> None:
        if self.node and self.node.name in ("Parts", "Shapes", "Others") or isinstance(self.node, NArgument):
            raise CannotDelete
        
        if isinstance(self.node, NOperation) and self.node is self.node.parent.childs[-1]: #only last op can be deleted   
            idx = self.model.index_from_node(self.node)
            parent_idx = idx.parent()
            self.model.removeRows(self.index, parent_idx)


    def undo(self) -> None:
        print("Okaygebusiness")

class AddOperation(BaseCommand):
    def __init__(self, model, parent: QUndoCommand = None ):
        pass


class EditArgument(BaseCommand):
    def __init__(self, model, value: Any, index: QModelIndex, parent: QUndoCommand = None ) -> None:
        super().__init__(parent)
        self.model = model
        self.arg_node = model.data(index, Qt.EditRole)
        self.old_value = self.arg_node.value
        self.edit_value = value

    def redo(self) -> None:
        arg_index = self.model.index_from_node(self.arg_node)
        self.arg_node.value = self.edit_value
        self.model.dataChanged.emit(arg_index,arg_index)
        # self.model.setData(index = arg_index, value = self.edit_value, role= Qt.EditRole)


    def undo(self) -> None:
        arg_index = self.model.index_from_node(self.arg_node)
        self.arg_node.value = self.old_value
        self.model.dataChanged.emit(arg_index,arg_index)
        # self.model.setData(index = arg_index, value = self.edit_value, role= Qt.EditRole)
