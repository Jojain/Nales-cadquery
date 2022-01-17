from typing import Any, TYPE_CHECKING, List
from PyQt5.QtWidgets import QUndoCommand
from PyQt5.QtCore import Qt, QModelIndex, QPersistentModelIndex
from nales_alpha.nales_cq_impl import Part, Shape

from nales_alpha.NDS.interfaces import NPart

if TYPE_CHECKING:
    from nales_alpha.NDS.model import NModel, ParamTableModel


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
        self.model.add_operation(
            self.node.parent.name, self.part_obj, self.node.operations
        )


class AddPart(AddTreeItem):
    def __init__(self, model: "NModel", part_name: str, part_obj: Part):
        super().__init__(model, part_name, part_obj)

    def redo(self):
        self.model.add_part(self.item_name, self.item_obj)

    def undo(self):
        node_idx = self.model.get_part_index(self.item_name)
        self.model.remove_part(node_idx)


class AddOperation(AddTreeItem):
    def __init__(
        self, model: "NModel", part_name: str, part_obj: Part, operation: dict
    ):
        super().__init__(model, part_name, part_obj)
        self.operation = operation

    def redo(self):
        node = self.model.add_operation(self.item_name, self.item_obj, self.operation)
        self.row = node.row

    def undo(self):
        parent_idx = self.model.get_part_index(self.item_name)
        node_idx = self.model.index(self.row, 0, parent_idx)
        self.model.remove_operation(node_idx)


class AddParameter(BaseCommand):
    def __init__(self, model: "ParamTableModel"):
        super().__init__()
        self.model = model

    def redo(self) -> None:
        self.row = self.model.add_parameter()

    def undo(self) -> None:
        self.model.remove_parameter([self.model.index(self.row, 0)])


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


class EditParameter(BaseCommand):
    def __init__(self, model: "ParamTableModel", value, index: QModelIndex):
        super().__init__()
        self.model = model
        self.value = value
        self.idx = index

    def redo(self) -> None:
        if self.idx.column() == 0:
            self.old_value = self.model._data[self.idx.row()].name
            self.model._data[self.idx.row()].name = self.value
        elif self.idx.column() == 1:
            self.old_value = self.model._data[self.idx.row()].value
            self.model._data[self.idx.row()].value = self.value
        self.model.dataChanged.emit(self.idx, self.idx)

    def undo(self) -> None:
        if self.idx.column() == 0:
            self.model._data[self.idx.row()].name = self.old_value
        elif self.idx.column() == 1:
            self.model._data[self.idx.row()].value = self.old_value
        self.model.dataChanged.emit(self.idx, self.idx)


class EditArgument(BaseCommand):
    def __init__(self, model: "NModel", value: Any, index: QModelIndex) -> None:
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
        self.model.dataChanged.emit(arg_index, arg_index)

    def undo(self) -> None:
        # arg_index = self.model.index_from_node(self.arg_node)
        arg_index = self.idx
        self.arg_node.value = self.old_value
        self.model.dataChanged.emit(arg_index, arg_index)


class LinkParameter(BaseCommand):
    def __init__(
        self,
        param_model: "ParamTableModel",
        modeling_ops_model: "NModel",
        selected_args: List[QModelIndex],
        name_idx: QModelIndex,
        value_idx: QModelIndex,
    ) -> None:

        super().__init__()
        self.param_model = param_model
        self.modeling_ops_model = modeling_ops_model
        self.name_idx = name_idx
        self.val_idx = value_idx
        self.selected_args = selected_args
        self.old_values = [arg_idx.internalPointer().value for arg_idx in selected_args]

    def redo(self) -> None:
        self.modeling_ops_model.link_parameters(
            self.selected_args,
            QPersistentModelIndex(self.name_idx),
            QPersistentModelIndex(self.val_idx),
        )

    def undo(self) -> None:
        for arg, value in zip(self.selected_args, self.old_values):
            self.modeling_ops_model.unlink_parameter(arg)
            arg.internalPointer().value = value
            self.modeling_ops_model.dataChanged.emit(arg, arg)


class UnlinkParameter(BaseCommand):
    def __init__(
        self,
        param_model: "ParamTableModel",
        modeling_ops_model: "NModel",
        selected_args: List[QModelIndex],
    ) -> None:

        super().__init__()
        self.param_model = param_model
        self.modeling_ops_model = modeling_ops_model
        self.selected_args = selected_args

    def redo(self) -> None:
        self.old_args = []
        for arg_idx in self.selected_args:
            self.old_args.append(arg_idx.internalPointer())
            self.modeling_ops_model.unlink_parameter(arg_idx)

    def undo(self) -> None:
        for arg_idx, old_arg in zip(self.selected_args, self.old_args):
            self.modeling_ops_model.link_parameters(
                [arg_idx],
                QPersistentModelIndex(old_arg._param_name_pidx),
                QPersistentModelIndex(old_arg._param_value_pidx),
            )


class AddShape(AddTreeItem):
    def __init__(self, model: "NModel", shape_name: str, shape_obj: Shape):
        super().__init__(model, shape_name, shape_obj)
