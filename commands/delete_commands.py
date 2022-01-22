from typing import Any, TYPE_CHECKING, Dict, List
from PyQt5.QtCore import QModelIndex
from nales_alpha.nales_cq_impl import Part


from nales_alpha.commands.base_commands import BaseCommand, DeleteTreeItem

if TYPE_CHECKING:
    from nales_alpha.NDS.model import NModel, ParamTableModel


class DeletePart(DeleteTreeItem):
    def __init__(self, model: "NModel", index: QModelIndex):
        super().__init__(model, index)
        self.noperations = self.node.childs
        self.part_name = self.node.name
        self.row = self.node.row
        self.vars = self.model.console.get_obj_varnames(self.item_obj)

    def redo(self):
        parent_idx = self.model.index(self.row, 0)
        self.model.remove_part(self.model.index(self.row, 0, parent_idx))

    def undo(self):
        self.node = self.model.add_part(self.part_name, self.node.part)

        for nop in self.noperations:
            self.model.add_operation(nop.parent.name, self.item_obj, nop.operations)

        # If we recreate the part we need to update it in the Part names
        if self.part_name not in Part._names:
            Part._names.append(self.part_name)

        # Recreate the vars in the console
        vars_dict = {var: self.item_obj for var in self.vars}
        self.model.console.push_vars(vars_dict)


class DeleteShape(DeleteTreeItem):
    def __init__(self, model: "NModel", index: QModelIndex):
        super().__init__(model, index)
        self.noperations = self.node.childs
        self.part_name = self.node.name
        self.row = self.node.row
        self.vars = self.model.console.get_obj_varnames(self.shape_obj)

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
        self.model.add_operation(
            self.node.parent.name, self.part_obj, self.node.operations
        )


class DeleteParameter(BaseCommand):
    def __init__(self, model: "ParamTableModel", indexes: List[QModelIndex]):
        super().__init__()
        self.model = model
        self.idxs = indexes
        self.removed_params = [
            (self.model._data[idx.row()], idx.row()) for idx in indexes
        ]

    def redo(self) -> None:
        self.model.remove_parameter(self.idxs)

    def undo(self) -> None:
        for param, row in self.removed_params:
            self.model.insertRows(row)
            self.model._data.insert(row, param)
