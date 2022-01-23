from typing import Any, TYPE_CHECKING, Callable, Dict, List
from nales_alpha.nales_cq_impl import NalesShape, Part

if TYPE_CHECKING:
    from nales_alpha.NDS.model import NModel, ParamTableModel

from nales_alpha.commands.base_commands import AddTreeItem, BaseCommand


class AddPart(AddTreeItem):
    def __init__(self, model: "NModel", part_name: str, part_obj: Part):
        super().__init__(model, part_name, part_obj)
        self.has_been_undone = False

    def redo(self):
        if self.has_been_undone:
            Part._names.append(self.item_name)
            self.has_been_undone = False

        self.model.add_part(self.item_name, self.item_obj)

    def undo(self):
        self.has_been_undone = True
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


class AddShape(AddTreeItem):
    def __init__(
        self,
        model: "NModel",
        shape_name: str,
        shape_class,
        shape_obj: NalesShape,
        maker_method: Callable,
        args: Dict,
    ):
        super().__init__(model, shape_name, shape_obj)
        self.maker_method = maker_method
        self.args = args
        self.shape_class = shape_class
        self.has_been_undone = False

    def redo(self) -> None:
        if self.has_been_undone:
            NalesShape._names.append(self.item_name)
            self.has_been_undone = False
        self.shape = self.model.add_shape(
            self.item_name,
            self.shape_class,
            self.item_obj,
            self.maker_method,
            self.args,
        )

    def undo(self) -> None:
        self.has_been_undone = True
        node_idx = self.model.get_shape_index(self.item_name)
        self.model.remove_shape(node_idx)
