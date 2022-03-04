"""
Reworked code based on
http://trevorius.com/scrapbook/uncategorized/pyqt-custom-abstractitemmodel/
Adapted to Qt5 and fixed column/row bug.
TODO: handle changing data.

Taken from : https://gist.github.com/nbassler/342fc56c42df27239fa5276b79fca8e6
"""


import sys
from typing import Any, Callable, Dict, List, Union

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import (
    QAbstractItemModel,
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QUndoCommand

from nales.commands.edit_commands import EditArgument, EditParameter
from nales.nales_cq_impl import NALES_TYPES, CQMethodCall, NalesShape, Part
from nales.NDS.interfaces import (
    NArgument,
    NNode,
    NOperation,
    NPart,
    NShape,
    NShapeOperation,
)
from nales.NDS.NOCAF import Application
from nales.utils import determine_type_from_str

NALES_PARAMS_TYPES = {
    "int": int,
    "str": str,
    "tuple": tuple,
    "list": list,
    "float": float,
}


class NalesParam:
    def __init__(self, name: str, value: object) -> None:
        self.name = name
        self._value = value
        type_ = None if value is None else type(value).__name__

        if type_ not in NALES_PARAMS_TYPES and type_ is not None:
            raise ValueError(
                f"Type {type_} not allowed. Allowed types are : {', '.join(NALES_PARAMS_TYPES.keys())}"
            )
        else:
            self.type = type_

    @classmethod
    def cast(cls, type_: str, value: str):
        if type_ == "None":
            return None
        else:
            return NALES_PARAMS_TYPES[type_](value)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self.type = determine_type_from_str(val).__name__ if val else type(None)
        self._value = val


class ParamTableModel(QAbstractTableModel):

    run_cmd = pyqtSignal(QUndoCommand)

    def __init__(self, param_table: List[NalesParam]):
        super().__init__()
        self._data = param_table

    def add_parameter(
        self, name: str = None, value: object = None, insert_row: int = None
    ) -> int:
        """
        Add a default parameter in the param table
        :return: the row at which the param has been added
        """
        automatic_param_name_indices = [
            int(param.name[5:])
            for param in self._data
            if (param.name.startswith("param") and param.name[5:].isnumeric())
        ]
        automatic_param_name_indices.sort()
        if len(automatic_param_name_indices) != 0:
            idx = automatic_param_name_indices[-1] + 1
        else:
            idx = 1
        if name:
            self._data.append(NalesParam(name, value))
        else:
            self._data.append(NalesParam(f"param{idx}", None))

        if not insert_row:
            insert_row = len(self._data) - 1

        self.insertRows(insert_row)

        return insert_row

    def is_null(self):
        if len(self._data) == 0:
            return True
        else:
            return False

    @property
    def parameters(self) -> List[NalesParam]:
        return self._data

    def remove_parameter(self, rmv_idxs: List[QModelIndex]):
        # if self.selectionModel().hasSelection():
        #     selected_param_idx = self.selectionModel().selectedRows()

        self.removeRows(rmv_idxs)

    def insertRows(self, row: int) -> bool:
        self.beginInsertRows(QModelIndex(), row, row)
        self.endInsertRows()
        self.layoutChanged.emit()
        return True

    def removeRows(self, rmv_idxs: List[QModelIndex]) -> bool:
        """
        Removes parameter from the table
        """
        # we filter the list of indexes to count only 1 row even if param name and value is selected
        if len(rmv_idxs) == 0:
            return False

        idx_to_remove = []
        for idx in rmv_idxs:
            if idx.isValid():
                if idx.row() not in [idx.row() for idx in idx_to_remove]:
                    idx_to_remove.append(idx)
            else:
                return False

        param_kept = [
            param
            for param in self._data
            if not param in [self._data[idx.row()] for idx in idx_to_remove]
        ]

        # self.beginRemoveRows(QModelIndex(), idx_to_remove[0].row(), idx_to_remove[-1].row()) # may need to add -1
        self.beginRemoveRows(
            QModelIndex(), idx_to_remove[0].row(), idx_to_remove[-1].row()
        )
        self._data = param_kept
        self.endRemoveRows()
        self.layoutChanged.emit()

        return True

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col == 0:
                return self._data[row].name
            elif col == 1:
                return self._data[row].value

    def flags(self, index):
        # parameter name and value can always be edited so this is always true

        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex) -> int:
        # there is only two columns in the param table
        return 2

    def index(self, row, column, parent: QModelIndex = QModelIndex()):
        # print("--------------")
        # print("row ", row, "col ", column)
        # print("--------------")
        if column == 0:
            return self.createIndex(row, column, self._data[row].name)
        elif column == 1:
            return self.createIndex(row, column, self._data[row].value)
        else:
            raise ValueError("`column` must be either 0 or 1")

    def setData(self, index, value, role):
        """
        setData of TableModel
        """
        if role == Qt.EditRole:
            self.run_cmd.emit(EditParameter(self, value, index))
            return True


class NModel(QAbstractItemModel):

    on_arg_error = pyqtSignal(object, object)
    run_cmd = pyqtSignal(QUndoCommand)

    def __init__(self, ctx, nodes=None, console=None):
        """
        ctx: occt viewer context
        """
        super().__init__()
        self.app = Application()
        self.app.init_viewer_presentation(ctx)
        self._console = console
        self._root = NNode(None)
        self._root._viewer = (
            self.app._pres_viewer
        )  # attach the viewer to the root node so child interfaces can Update the viewer without the need to send a signal
        self._root._label = self.app.doc.GetData().Root()
        self._root.console_namespace = console.namespace

        self._setup_top_level_nodes()

        # Slots connection
        self.dataChanged.connect(lambda idx: self.update_model(idx))

    def _setup_top_level_nodes(self):
        NNode("Parts", self._root)
        NNode("Shapes", self._root)
        NNode("Others", self._root)
        self.insertRows(0, 3)

    def add_part(self, name: str, part: Part) -> NPart:
        """
        Add a Part to the data model

        """
        # ce genre de truc devra être géré par le model
        # actuellement le code reconstruirait toutes les parts meme si elles n'ont pas été modifiées
        parts_idx = self.index(0, 0)

        # We check if the part is already defined
        if part_node := self._root.find(name):
            part_idx = self.index(part_node._row - 1, 0, parts_idx)
            self.removeRows([part_idx], part_idx.parent())

        node = NPart(name, part, self._root.child(0))
        self.insertRows(self.rowCount(parts_idx), parent=parts_idx)

        node.display()
        return node

    def get_part_index(self, part_name: str) -> Union[QModelIndex, None]:
        for idx in self.walk():
            try:
                if idx.internalPointer().name == part_name:
                    return idx
            except AttributeError:
                continue

    def get_shape_index(self, shape_name: str) -> Union[QModelIndex, None]:
        for idx in self.walk():
            try:
                if idx.internalPointer().name == shape_name:
                    return idx
            except AttributeError:
                continue

    def add_operation(
        self, part_name: str, part_obj: Part, operation: CQMethodCall
    ) -> NOperation:
        """
        Add an operation to the operation tree

        :return: the node of 
        """
        nparts = self._root.child(0).childs
        parts_idx = self.index(0, 0)  # the Parts container index

        for npart in nparts:
            if npart.name == part_name:
                row = npart.row
                parent_part = npart
                break

        part_idx = self.index(row, 0, parts_idx)

        method_name = operation.name
        noperation = NOperation(method_name, part_obj, parent_part, operation)
        self.insertRows(self.rowCount(), parent=part_idx)

        operation_idx = self.index(noperation.row, 0, part_idx)

        for arg in operation.args:
            node = NArgument(
                arg.name, arg.value, arg.type, noperation, kwarg=arg.optional
            )
            # the argument is an object stored in the model data structure
            if isinstance(arg.value, NALES_TYPES):
                obj_node = self._root.find(arg.value._name)
                idx = self.index_from_node(obj_node)
                node.link("obj", idx)

        self.insertRows(self.rowCount(operation_idx), parent=operation_idx)

        npart.display(update=True)

        # update copies of the part in the console
        self._console.update_part(part_name, npart.part)

        return noperation

    def update_model(self, idx: QModelIndex) -> None:
        """
        This method is called each time something is changed in the data model from the view
        It's job is to dispatch the event to the right method in order to keep the data model 
        synchronized
        """
        if not isinstance(ptr := idx.internalPointer(), NArgument):
            raise ValueError("Something else than a NArgument has been modified")

        if isinstance(ptr.parent, NOperation):
            self.update_operation(idx)
            part_obj = ptr.parent.parent.part
            self.update_objs_linked_to_obj(part_obj)

        elif isinstance(ptr.parent, NShapeOperation):
            self.update_shape(idx)
            shape_obj = ptr.parent.parent.shape
            self.update_objs_linked_to_obj(shape_obj)
        else:
            raise ValueError

    def update_objs_linked_to_obj(self, obj: Any):
        """
        Update any object in the model that is linked to the `obj`
        """
        for idx in self.walk():
            if isinstance(arg_ptr := idx.internalPointer(), NArgument):
                op = arg_ptr.parent
                if (
                    isinstance(op, NOperation)
                    and arg_ptr.is_linked(by="obj")
                    and arg_ptr.linked_obj is obj
                ):
                    op.update_from_node()
                elif isinstance(op, NShapeOperation):
                    NotImplementedError("Can't update this obj yet")

    def update_shape(self, idx: QModelIndex) -> None:
        shape_op = idx.internalPointer().parent
        shape_op.update()

    def update_operation(self, idx: QModelIndex) -> None:
        """
        Update the CQ / OCP data after a changed in a parameter made by the user
        """

        if isinstance(ptr := idx.internalPointer(), NArgument):
            starting_op: NOperation = ptr.parent
            starting_op.update_from_node()

    def index_from_node(self, node: "NNode") -> QModelIndex:
        for idx in self.walk():
            if idx.internalPointer() == node:
                return idx
        raise ValueError(f"The node {node} is not in the NModel")

    def add_shape(
        self, shape_name, shape_class, shape, maker_method: Callable, args: Dict
    ):
        """
        Add a shape to the data model
        """
        # Add the shape to the tree
        nshape = NShape(shape_name, shape, self._root.child(1))
        # Add the maker method to the tree as an operation
        nop = NShapeOperation(maker_method, shape_class, nshape)
        # Add the makermethod args to the tree
        for name, value in args.items():
            NArgument(name, value, nop, shape_arg=True)

        shapes_idx = self.index(self._root.child(1)._row, 0)
        self.insertRows(self.rowCount(shapes_idx), parent=shapes_idx)

    def link_object(self, idxes_to_link: List[QModelIndex], obj_idx: QModelIndex):
        """
        Link all the provided nodes indexes with the provided obj_idx
        """
        for idx in idxes_to_link:
            node = idx.internalPointer()
            node.link("obj", obj_idx)
        self.dataChanged.emit(idxes_to_link[0], idxes_to_link[-1])

    def unlink_object(self, linked_node_idx: QModelIndex):
        linked_node = linked_node_idx.internalPointer()
        linked_node.unlink()

    def link_parameters(
        self,
        indexes: List[QModelIndex],
        name_pidx: QPersistentModelIndex,
        value_pidx: QPersistentModelIndex,
    ):

        for idx in indexes:
            self.setData(
                idx,
                (name_pidx.data(), value_pidx.data(), name_pidx, value_pidx),
                Qt.EditRole,
            )

    def unlink_parameter(
        self, arg_idx: QModelIndex = None, param_idx: QModelIndex = None
    ):
        if arg_idx and not param_idx:
            arg: NArgument = arg_idx.internalPointer()
            arg.unlink_param()
            self.dataChanged.emit(arg_idx, arg_idx)

        elif param_idx and not arg_idx:
            for idx in self.walk():
                node = idx.internalPointer()

                if isinstance(node, NArgument) and node.is_linked():

                    if node._param_name_pidx.data() is None:
                        node._linked_param = None
                        self.dataChanged.emit(idx, idx)

    def update_parameters(self):
        """
        Update the modeling ops view and model when parameters are modified in the Parameter table
        (Note : It's handled with signals and slot, but It could be done with Proxy Models and having only 1 model holding all the data of the app)
        """

        for idx in self.walk():

            node = idx.internalPointer()
            if isinstance(node, NArgument):
                if node.is_linked(by="param"):
                    node._linked_param = node._param_name_pidx.data()
                    node.value = node._param_value_pidx.data()

                    self.dataChanged.emit(
                        idx, idx
                    )  # here we could modify the behaviour to send only one signal after we modified all the nodes

    def walk(self, index: QModelIndex = QModelIndex()) -> QModelIndex:

        yield index

        for child in self.childrens(index):
            yield from self.walk(child)

    def childrens(self, index: QModelIndex = QModelIndex()):
        if self.hasChildren(index):
            return [self.index(i, 0, index) for i in range(self.rowCount(index))]

        else:
            return []

    ##
    # Redifined functions
    ##
    def rowCount(self, index: QModelIndex = QModelIndex()):
        if index.isValid():
            return index.internalPointer().child_count()
        return self._root.child_count()

    def columnCount(self, index):
        if index.isValid():
            return index.internalPointer().column
        return self._root.column

    def index(self, row, column, _parent: QModelIndex = QModelIndex()):
        if not _parent or not _parent.isValid():
            parent = self._root
        else:
            parent = _parent.internalPointer()

        if not self.hasIndex(row, column, _parent):
            return QtCore.QModelIndex()

        child = parent.child(row)
        if child:
            return self.createIndex(row, column, child)
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        if index.isValid():
            if hasattr(ptr := index.internalPointer(), "parent"):
                p = ptr.parent
            else:
                p = None
            if p:
                return self.createIndex(p._row, 0, p)
        return QtCore.QModelIndex()

    def remove_operation(self, op_idx: QModelIndex) -> None:
        """
        Remove an operation at the given `op_idx` index
        """

        npart: NPart = op_idx.internalPointer().parent
        # We remove the op from the tree
        self.removeRows([op_idx], op_idx.parent())

        npart.display(update=True)

    def remove_part(self, part_idx: QModelIndex) -> None:
        """
        Remove a part at the given `part_idx` index
        """
        part_node = part_idx.internalPointer()
        self.removeRows([part_idx], part_idx.parent())

        # Remove all reference everywhere it's needed
        Part._names.remove(part_node.name)
        self._console.remove_obj(part_node.part)
        part_node.hide()
        # self.app.viewer_redraw()

    def remove_shape(self, shape_idx: QModelIndex) -> None:
        """
        Remove a part at the given `part_idx` index
        """
        shape_node = shape_idx.internalPointer()
        self.removeRows([shape_idx], shape_idx.parent())

        # Remove all reference everywhere it's needed
        NalesShape._names.remove(shape_node.name)
        self._console.remove_obj(shape_node.shape)
        shape_node.hide()

    def removeRows(
        self, rmv_idxs: List[QModelIndex], parent: QModelIndex = QModelIndex()
    ) -> bool:
        """
        Removes data from the Nales data model
        """
        # we filter the list of indexes to count only 1 row even if param name and value is selected
        if len(rmv_idxs) == 0:
            return False

        idx_to_remove = []
        for idx in rmv_idxs:
            if idx.isValid():
                if idx.row() not in [idx.row() for idx in idx_to_remove]:
                    idx_to_remove.append(idx)
            else:
                return False
        parent_node = parent.internalPointer()
        kept_childs = [
            child
            for child in parent_node.childs
            if not child in [idx.internalPointer() for idx in idx_to_remove]
        ]
        self.beginRemoveRows(parent, idx_to_remove[0].row(), idx_to_remove[-1].row())
        parent_node.childs = kept_childs
        self.endRemoveRows()
        self.layoutChanged.emit()

        return True

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """
        data method of NModel
        Allow acces to underlying Data tree
        """
        if not index.isValid():
            return None
        node = index.internalPointer()

        if isinstance(node, NArgument):
            if role == Qt.DisplayRole:
                if index.column() == 0:
                    if node.is_linked(by="param"):
                        return f"{node.name} = {node.linked_param}"
                    elif node.is_linked(by="obj"):
                        return f"{node.name} = {node.linked_node.name}"
                    else:
                        return f"{node.name} = {node.value}"

            elif role == Qt.EditRole:
                return node

            elif role == Qt.FontRole:
                if (
                    node.is_linked()
                ):  # if linked to a param , gets overidden by the stylesheet
                    font = QFont()
                    font.setItalic(True)
                    font.setBold(True)
                    return font

        elif isinstance(node, NPart) or isinstance(node, NShape):
            if role == Qt.DisplayRole:
                return node.name  # display part or shape var name

            elif role == Qt.CheckStateRole:
                if node.visible:
                    return Qt.Checked
                else:
                    return Qt.Unchecked

        if role == Qt.DisplayRole:
            return node.name
        elif role == Qt.UserRole:
            return node.data(index.column())

        elif role == Qt.EditRole:
            return node

    def flags(self, index):
        """
        NModel flags
        """
        node = index.internalPointer()
        if isinstance(node, NArgument):
            if node.is_linked():
                return Qt.ItemIsEnabled | Qt.ItemIsSelectable
            else:
                return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

        if isinstance(node, NPart) or isinstance(node, NShape):
            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable

        elif isinstance(node, NOperation):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled

    def setData(self, index: QModelIndex, value: Any, role):
        """
        NModel data setter
        """

        node = index.internalPointer()
        if role == Qt.EditRole:
            if isinstance(node, NArgument):
                if isinstance(node.parent, NShapeOperation):
                    SHAPEARG = True
                else:
                    SHAPEARG = False
                if isinstance(value, tuple):  # we assign a parameter
                    node.link("param", value)

                elif (
                    obj_node := self._root.find(value)
                ) :  # the argument is an object stored in the model data structure
                    idx = self.index_from_node(obj_node)
                    node.link("obj", (QPersistentModelIndex(idx),))

                else:
                    value_type = determine_type_from_str(value)
                    if node.is_type_compatible(value):
                        self.run_cmd.emit(EditArgument(self, value, index))

                    else:
                        self.on_arg_error.emit(node._type, value_type)

            self.dataChanged.emit(index, index)

            # Update variables linked to this part in the console
            if not SHAPEARG:
                self._console.update_part(
                    node.parent.parent.name, node.parent.parent.part
                )

        elif role == Qt.CheckStateRole:
            if isinstance(node, NPart) or isinstance(node, NShape):
                if node.visible:
                    node.hide()
                else:
                    node.display(update=True)

        return True

    def insertRows(self, row: int, count: int = 1, parent=QModelIndex()):
        """
        The node is actually not needed, this function just notify the model that rows has been added
        but there is no more information provided
        The model get the data from the NNode tree
        """
        idx = self.index(row, 0, parent)
        self.beginInsertRows(idx, row, count)
        self.endInsertRows()
        self.layoutChanged.emit()

    @property
    def parts(self) -> List[NPart]:
        nparts = self._root.childs[0].childs
        return nparts

    @property
    def objects(self) -> List[Union[NPart, NShape]]:
        objs = []
        for child in self._root.childs:
            objs.extend(child.childs)
        return objs

    @property
    def console(self):
        return self._console


if __name__ == "__main__":

    class Table(QtWidgets.QTableView):
        def __init__(self, parent=None) -> None:
            super().__init__(parent=parent)

    app = QtWidgets.QApplication(sys.argv)
    param_table = [["toto", 5], ["marie", ">Z"]]
    table = Table()
    model = ParamTableModel(param_table)
    table.setModel(model)
    table.show()
    sys.exit(app.exec_())
