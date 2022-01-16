from copy import copy
import imp
from typing import Any, TYPE_CHECKING
from PyQt5.QtWidgets import QUndoCommand
from PyQt5.QtCore import Qt, QModelIndex
from nales_alpha.nales_cq_impl import Part

from nales_alpha.NDS.interfaces import NPart

if TYPE_CHECKING:
    from nales_alpha.NDS.model import NModel


class BaseCommand(QUndoCommand):
    def __init__(self):
        super().__init__()
        self.setText(self.__class__.__name__)


class DeleteTreeItem(BaseCommand):
    def __init__(self, model: "NModel", index: QModelIndex):
        super().__init__()
        self.model = model        
        self.node = index.internalPointer()
        if isinstance(self.node, NPart):
            self.part_obj = self.node.part 
        else: 
            self.part_obj = self.node.parent.part


class DeletePart(DeleteTreeItem):
    def __init__(self, model: "NModel", index: QModelIndex):
        super().__init__(model, index)
        self.noperations = self.node.childs
        self.part_name = self.node.name
        self.row = self.node.row
        self.vars = self.model.console.get_part_varnames(self.part_obj)

    def redo(self):
        parent_idx = self.model.index(self.row, 0)
        self.model.remove_part(self.model.index(self.row, 0, parent_idx))

    def undo(self):
        self.node = self.model.add_part(self.part_name, self.node.part)

        for nop in self.noperations:
            self.model.add_operation(nop.parent.name, self.part_obj, nop.operations)

        # If we recreate the part we need to update it in the Part names
        if self.part_name not in Part._names:
            Part._names.append(self.part_name)
        
        # Recreate the vars in the console
        vars_dict = {var: self.part_obj for var in self.vars}
        
        self.model.console.push_vars(vars_dict)

class DeleteOperation(DeleteTreeItem):
    def __init__(self, model, index: QModelIndex):
        super().__init__(model, index)
        self.part_name = self.node.parent.name
        self.row = self.node.row

    def redo(self):
        parent_idx = self.model.get_part_index(self.part_name)
        node_idx = self.model.index(self.row, 0, parent_idx)
        self.model.remove_operation(node_idx)

    def undo(self):
        self.model.add_operation(self.node.parent.name, self.part_obj, self.node.operations)
        


class AddPart(BaseCommand):
    def __init__(self, model: "NModel", part_name: str, part_obj: Part ):
        super().__init__()
        self.model = model
        self.part_name = part_name
        self.part_obj = part_obj

    def redo(self):
        self.model.add_part(self.part_name, self.part_obj)
    
    def undo(self):
        node_idx = self.model.get_part_index(self.part_name)
        self.model.remove_part(node_idx)

class AddOperation(BaseCommand):
    def __init__(self, model: "NModel", part_name: str, part_obj: Part,  operation: dict ):
        super().__init__()
        self.model = model
        self.part_name = part_name
        self.part_obj = part_obj
        self.operation = operation

    def redo(self):
        node = self.model.add_operation(self.part_name, self.part_obj, self.operation)
        self.row = node.row 


    def undo(self):
        parent_idx = self.model.get_part_index(self.part_name)
        node_idx = self.model.index(self.row, 0, parent_idx)
        self.model.remove_operation(node_idx)






class EditArgument(BaseCommand):
    def __init__(self, model: "NModel", value: Any, index: QModelIndex ) -> None:
        super().__init__()
        self.model = model
        self.arg_node = model.data(index, Qt.EditRole)
        self.old_value = self.arg_node.value
        self.edit_value = value
        self.idx = index

    def redo(self) -> None:
        # arg_index = self.model.index_from_node(self.arg_node)
        arg_index = self.idx
        self.arg_node.value = self.edit_value
        self.model.dataChanged.emit(arg_index,arg_index)
        


    def undo(self) -> None:
        # arg_index = self.model.index_from_node(self.arg_node)
        arg_index = self.idx
        self.arg_node.value = self.old_value
        self.model.dataChanged.emit(arg_index,arg_index)
