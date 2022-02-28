from typing import Any, TYPE_CHECKING, List
from PyQt5.QtCore import Qt, QModelIndex, QPersistentModelIndex


from nales.commands.base_commands import BaseCommand

if TYPE_CHECKING:
    from nales.NDS.model import NModel, ParamTableModel


class EditArgument(BaseCommand):
    def __init__(self, model: "NModel", value: Any, index: QModelIndex) -> None:
        super().__init__()
        self.model = model
        self.arg_node = model.data(index, Qt.EditRole)
        self.old_value = self.arg_node.value
        self.edit_value = value
        self.idx = index

    def redo(self) -> None:
        arg_index = self.idx
        self.arg_node.value = self.edit_value
        self.model.dataChanged.emit(arg_index, arg_index)

    def undo(self) -> None:
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
