from typing import Any
from PyQt5.QtWidgets import QUndoCommand
from PyQt5.QtCore import Qt, QModelIndex


class AddOperation(QUndoCommand):
    def __init__(self, model, parent: QUndoCommand = None ):
        pass


class EditArgument(QUndoCommand):
    def __init__(self, model, value: Any, index: QModelIndex, parent: QUndoCommand = None ) -> None:
        super().__init__(parent)
        self.setText = self.__name__
        self.model = model
        self.arg_node = model.data(index, Qt.EditRole)
        self.old_value = self.arg_node.value
        self.edit_value = value

    def redo(self) -> None:
        arg_index = self.model.index_from_node(self.arg_node)
        self.model.setData(index = arg_index, value = self.edit_value, role= Qt.EditRole)


    def undo(self) -> None:
        arg_index = self.model.index_from_node(self.arg_node)
        self.model.setData(index = arg_index, value = self.edit_value, role= Qt.EditRole)
