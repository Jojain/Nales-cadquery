"""
Reworked code based on
http://trevorius.com/scrapbook/uncategorized/pyqt-custom-abstractitemmodel/
Adapted to Qt5 and fixed column/row bug.
TODO: handle changing data.

Taken from : https://gist.github.com/nbassler/342fc56c42df27239fa5276b79fca8e6
"""

from PyQt5.QtGui import QColor, QFont
from collections import OrderedDict, namedtuple
from inspect import signature
from tokenize import any
from typing import Any, Iterable, List, Tuple, Union
import sys
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMenu, QUndoCommand
from PyQt5.QtCore import (
    QModelIndex,
    QAbstractItemModel,
    QAbstractTableModel,
    QPersistentModelIndex,
    Qt,
    pyqtSignal,
)
from cadquery import Workplane

# from OCP.TDataStd import TDataStd_Name
# from OCP.TPrsStd import TPrsStd_AISPresentation
from cadquery.occ_impl.shapes import Shape

# from OCP.AIS import AIS_InteractiveObject, AIS_ColoredShape
# from OCP.TNaming import TNaming_Builder, TNaming_NamedShape
from nales_alpha.NDS.NOCAF import Application

# from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
# from OCP.TDF import TDF_Label, TDF_TagSource
# from OCP.TCollection import TCollection_ExtendedString
# from OCP.TopoDS import TopoDS_Shape
from nales_alpha.utils import determine_type_from_str, get_Wp_method_args_name
from nales_alpha.NDS.interfaces import NNode, NPart, NOperation, NArgument, NShape
from nales_alpha.widgets.msg_boxs import WrongArgMsgBox
import ast

import cadquery as cq


from nales_alpha.NDS.commands import EditArgument, EditParameter

from nales_alpha.nales_cq_impl import Part


class NalesParam:
    def __init__(self, name: str, value: object) -> None:
        self.name = name
        self.value = value


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
        if name and value:
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
    def parameters(self) -> dict:
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
        self.dataChanged.connect(lambda idx: self.update_operation(idx))

    def _setup_top_level_nodes(self):
        NNode(None, "Parts", self._root)
        NNode(None, "Shapes", self._root)
        NNode(None, "Others", self._root)
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

    def add_operation(
        self, part_name: str, part_obj: Part, operations: dict
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

        method_name = operations["name"]
        noperation = NOperation(
            method_name, method_name, part_obj, parent_part, operations
        )
        self.insertRows(self.rowCount(), parent=part_idx)

        operation_idx = self.index(noperation.row, 0, part_idx)

        args, kwargs = operations["parameters"][0], operations["parameters"][1]
        args = [arg.name if isinstance(arg, Part) else arg for arg in args]

        args_names = get_Wp_method_args_name(method_name)
        if len(args) == len(args_names):

            for pos, arg in enumerate(args):
                node = NArgument(args_names[pos], arg, noperation)
                if (
                    obj_node := self._root.find(arg)
                ) :  # the argument is an object stored in the model data structure
                    idx = self.index_from_node(obj_node)
                    node._linked_obj_idx = QPersistentModelIndex(idx)
                    node.name = arg

                self.insertRows(self.rowCount(operation_idx), parent=operation_idx)
        else:
            # Means the user passed an argument without calling the keyword
            nb_short_call_kwarg = len(args) - len(args_names)

            for pos, arg in enumerate(args[0 : nb_short_call_kwarg - 1]):
                node = NArgument(args_names[pos], arg, noperation)
                self.insertRows(self.rowCount(operation_idx), parent=operation_idx)

            kw_names = [kw_name for kw_name in list(kwargs.keys())]
            for kwarg_name, kwarg_val in zip(kw_names, args[nb_short_call_kwarg - 1 :]):
                kwargs[kwarg_name] = kwarg_val

        for kwarg_name, kwarg_val in kwargs.items():
            node = NArgument(kwarg_name, kwarg_val, noperation, kwarg=True)
            self.insertRows(self.rowCount(operation_idx), parent=operation_idx)

        npart.display(update=True)

        # update copies of the part in the console
        self._console.update_part(part_name, npart.part)

        return noperation

    def update_shape(self, idx: QModelIndex) -> None:
        pass

    def update_operation(self, idx: QModelIndex) -> None:

        if isinstance(ptr := idx.internalPointer(), NArgument):
            starting_op = ptr.parent
            part = starting_op.parent

            operations = part.childs[starting_op.row :]

            for operation in operations:
                if operation is starting_op:
                    pos = len(part.childs) - operation.row
                else:
                    pos = 0
                operation.update(pos)

            part.display(update=True)

    def index_from_node(self, node: "NNode") -> QModelIndex:
        for idx in self.walk():
            if idx.internalPointer() == node:
                return idx
        raise ValueError(f"The node {node} is not in the NModel")

    def add_shape(self, shape_name, shape, topo_type, method_call):
        (
            (method_name, args),
        ) = method_call.items()  # weird unpacking necessary for 1 element dict

        invoked_method = {
            "class_name": topo_type,
            "method_name": method_name,
            "args": args[0],
            "kwargs": args[1],
        }
        node = NShape(shape_name, shape, invoked_method, self._root.child(1))

        shapes_idx = self.index(self._root.child(1)._row, 0)
        self.insertRows(self.rowCount(shapes_idx), parent=shapes_idx)

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
            arg = arg_idx.internalPointer()
            arg._linked_param = None
            self.dataChanged.emit(arg_idx, arg_idx)

        elif param_idx and not arg_idx:
            for idx in self.walk():
                node = idx.internalPointer()

                if isinstance(node, NArgument) and node.is_linked():

                    if node._param_name_pidx.data() is None:
                        node._linked_param = None
                        self.dataChanged.emit(idx, idx)

    def _update_parameters(self):
        """
        Update the modeling ops view and model when parameters are modified in the Parameter table
        (Note : It's handled with signals and slot, but It could be done with Proxy Models and having only 1 model holding all the data of the app)
        """

        for idx in self.walk():

            node = idx.internalPointer()
            if isinstance(node, NArgument):
                if node.is_linked():
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
            p = index.internalPointer().parent
            if p:
                return self.createIndex(p._row, 0, p)
        return QtCore.QModelIndex()

    def remove_operation(self, op_idx: QModelIndex) -> None:
        """
        Remove an operation at the given `op_idx` index
        """

        npart = op_idx.parent().internalPointer()
        # We remove the op from the tree
        self.removeRows([op_idx], op_idx.parent())

        # We update the Part without the last operation
        try:
            last_op = npart.childs[-1]
            last_op.remove_operation()
        except IndexError:
            while npart.part.parent_obj is not None:
                npart.part = npart.part.parent_obj
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
        if not index.isValid():
            return None
        node = index.internalPointer()

        if isinstance(node, NArgument):
            if role == Qt.DisplayRole:
                if index.column() == 0:  #
                    if node.is_linked(by="param"):
                        return f"{node._arg_infos[0]} = {node.linked_param}"
                    if node.is_linked(by="obj"):
                        return f"{node.name}"
                    else:
                        return f"{node.name} = {node._value}"

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
                if isinstance(value, tuple):  # we assign a parameter
                    node._linked_param = value[0]
                    node.value = value[1]
                    node._param_name_pidx = value[2]
                    node._param_value_pidx = value[3]

                elif (
                    obj_node := self._root.find(value)
                ) :  # the argument is an object stored in the model data structure
                    idx = self.index_from_node(obj_node)
                    node._linked_obj_idx = QPersistentModelIndex(idx)
                    node.name = value

                else:
                    value_type = determine_type_from_str(value)
                    if node._type == value_type:
                        # node.value = value
                        self.run_cmd.emit(EditArgument(self, value, index))

                    else:
                        self.on_arg_error.emit(node._type, value_type)

            self.dataChanged.emit(index, index)

            # Update variables linked to this part in the console
            self._console.update_part(node.parent.parent.name, node.parent.parent.part)

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
