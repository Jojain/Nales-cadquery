


"""
Reworked code based on
http://trevorius.com/scrapbook/uncategorized/pyqt-custom-abstractitemmodel/
Adapted to Qt5 and fixed column/row bug.
TODO: handle changing data.

Taken from : https://gist.github.com/nbassler/342fc56c42df27239fa5276b79fca8e6
"""

from PyQt5.QtGui import QColor, QFont
from collections import OrderedDict
from inspect import signature
from tokenize import any
from typing import Iterable, List, Tuple
import sys
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMenu
from PyQt5.QtCore import QModelIndex, QAbstractItemModel, QAbstractTableModel,QItemSelectionModel, QPersistentModelIndex, QPoint, QVariant, Qt, pyqtSignal
from cadquery import Workplane

from OCP.TDataStd import TDataStd_Name
from OCP.TPrsStd import TPrsStd_AISPresentation
from cadquery.occ_impl.shapes import Shape
from OCP.AIS import AIS_InteractiveObject, AIS_ColoredShape
from OCP.TNaming import TNaming_Builder, TNaming_NamedShape
from nales_alpha.NDS.NOCAF import Application
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.TDF import TDF_Label, TDF_TagSource
from OCP.TCollection import TCollection_ExtendedString
from OCP.TopoDS import TopoDS_Shape
from nales_alpha.utils import get_Workplane_operations, get_Wp_method_args_name
from nales_alpha.NDS.interfaces import NNode, NPart, NOperation, NArgument, NShape


import cadquery as cq








class ParamTableModel(QAbstractTableModel):
    def __init__(self, param_table: List[list]):
        super().__init__()
        self._data = param_table

    def add_parameter(self):
        self.insertRows(1) # whatever value I pass it always append row which is fine in our case 


    def is_null(self):
        if len(self._data) == 0:
            return True
        else:
            return False

    @property
    def parameters(self):
        return {name: value for (name, value) in self._data}

    def remove_parameter(self, rmv_idxs : List[QModelIndex]):
        # if self.selectionModel().hasSelection():
        #     selected_param_idx = self.selectionModel().selectedRows()
        
        self.removeRows(rmv_idxs)



    def insertRows(self, row: int) -> bool:
        self.beginInsertRows(QModelIndex(), row, row)

        automatic_param_name_indices = [int(param[0][5:]) for param in self._data if (param[0].startswith("param") and param[0][5:].isnumeric())]
        automatic_param_name_indices.sort()
        if len(automatic_param_name_indices) != 0:
            idx =automatic_param_name_indices[-1] + 1
        else :
            idx = 1
        self._data.append([f"param{idx}", None])

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

        param_kept = [param for param in self._data if not param in [self._data[idx.row()] for idx in idx_to_remove]]

        # self.beginRemoveRows(QModelIndex(), idx_to_remove[0].row(), idx_to_remove[-1].row()) # may need to add -1
        self.beginRemoveRows(QModelIndex(), idx_to_remove[0].row(), idx_to_remove[-1].row()) 
        self._data = param_kept
        self.endRemoveRows()
        self.layoutChanged.emit()

        return True

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self._data[row][col]



    def flags(self, index):        
        # parameter name and value can always be edited so this is always true

        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable 




    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self._data)
    
    def columnCount(self, parent: QModelIndex) -> int:
        # there is only two columns in the param table
        return 2

    def index(self, row, column, parent = QModelIndex()):
        # print("--------------")
        # print("row ", row, "col ", column)
        # print("--------------")
        return self.createIndex(row, column, self._data[row][column])

    def setData(self, index, value, role):
        """
        setData of TableModel
        """
        if role == Qt.EditRole:
            self._data[index.row()][index.column()] = value
            self.dataChanged.emit(index,index)
            return True



class NModel(QAbstractItemModel):


    node_edited = pyqtSignal(NNode)

    def __init__(self, ctx, nodes = None):
        """
        ctx: occt viewer context
        """
        super().__init__()
        self.app = Application()
        self.app.init_viewer_presentation(ctx)
        self._root = NNode(None)
        self._root._viewer = self.app._pres_viewer # attach the viewer to the root node so child interfaces can Update the viewer without the need to send a signal
        self._root._label = self.app.doc.GetData().Root()


        self.insertRows(0,0,NNode(None, "Parts", self._root))
        self.insertRows(1,0,NNode(None, "Shapes", self._root))

        # Slots connection 

        

    def add_part(self, name: str, part: Workplane):
        """
        Add a Part to the data model

        """
        # ce genre de truc devra être géré par le model 
        # actuellement le code reconstruirait toutes les parts meme si elles n'ont pas été modifiées
        parts_idx = self.index(0, 0)

        # We check if the part is already defined
        if part_node := self._root.find(name):
            # part_idx = self.index_from_node(part_node)
            part_idx = self.index(part_node._row-1, 0, parts_idx )
            self.removeRows([part_idx.child(i,0) for i in range(self.rowCount(part_idx))], part_idx)
 

        else:
            node = NPart(name, part, self._root.child(0))    
            self.insertRows(self.rowCount(parts_idx), 0, None, parent=parts_idx)
            self.dataChanged.connect(node.rebuild) 
   



    
    def add_operations(self, part_name: str, wp: Workplane,  operations: OrderedDict):
        # Implémentation à l'arrache il faudra étudier les TFUNCTIONS et voir comment gérer de l'UNDO REDO
        parts = self._root.child(0).childs
        parts_idx = self.index(0,0) # the Parts container index
        
        for part in parts:
            if part.name == part_name:
                row = part._row
                parent_part = part
                
                break 

        part_idx = self.index(row, 0, parts_idx)
        
        
        for method, parameters in operations.items():
            operation = NOperation(method, method, wp, parent_part)
            self.insertRows(self.rowCount(), 0, operation, part_idx)

            operation_idx = self.index(operation._row, 0, part_idx)

            args, kwargs = parameters[0], parameters[1]
            args_names = get_Wp_method_args_name(method)
            for pos, arg in enumerate(args):                
                node = NArgument(args_names[pos], arg, type(arg), operation) 
                self.insertRows(self.rowCount(operation_idx),0, node, operation_idx)

            for kwarg_name, kwarg_val in kwargs.items():
                    node = NArgument(kwarg_name, kwarg_val, type(kwarg_name), operation) 
                    self.insertRows(self.rowCount(operation_idx),0, node, operation_idx)




        parent_part.rebuild()


    def index_from_node(self, node: "NNode") -> QModelIndex:
        raise NotImplementedError
        if parent_node := node.parent:
            parent_idx = self.index_from_node(parent_node)
        else:
            parent_idx = QModelIndex()
    
        node_idx = self.index(node._row, node._columns_nb, parent_idx)

        return node_idx

    def add_shape(self, shape_name, shape, topo_type, method_call):
        (method_name, args), = method_call.items()      

        # invoked_method = f"cq.{topo_type}.{method_name}{tuple(list(args.values())[0])}"
        invoked_method = {'class_name': topo_type, 'method_name': method_name, 'args': list(args.values())[0]}
        node = NShape(shape_name, shape, invoked_method, self._root.child(1))    
        # self.dataChanged.connect(node.rebuild) # ce genre de truc devra être géré par le model 
                                                # actuellement le code reconstruirait toutes les parts meme si elles n'ont pas été modifiées
        shapes_idx = self.index(self._root.child(1)._row, 0)
        self.insertRows(self.rowCount(shapes_idx), 0, node, parent=shapes_idx)
       

    def _link_parameters(self, indexes: List[QModelIndex], name_pidx:QPersistentModelIndex, value_pidx:QPersistentModelIndex):
        
        for idx in indexes:
            self.setData(idx, (name_pidx.data(), value_pidx.data(), name_pidx, value_pidx), Qt.EditRole)

    
        for part_idx in self.childrens(self.index(0,0)):
            part_idx.internalPointer().rebuild()

    def _disconnect_parameter(self, arg_idx: QModelIndex = None, param_idx: QModelIndex = None):
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

                    node_idx = self.index(node._row, 0)
                    
                    self.dataChanged.emit(node_idx,node_idx) # here we could modify the behaviour to send only one signal after we modified all the nodes
                    

                
        
        # for arg in self.arguments:
        #     if arg.linked_param:
        #         linked_args.append(arg)
        
        # for arg in linked_args:
        #     if arg

        

    

    # def _add_child(self, node, _parent: QModelIndex = QModelIndex()):
    #     if not _parent or not _parent.isValid():
    #         parent = self._root
    #     else:
    #         parent = _parent.internalPointer()
    #     parent.add_child(node)
    #     NNode()


    def walk(self, index: QModelIndex = QModelIndex()) -> QModelIndex:
        
        for idx in self.childrens(index):
            if self.hasChildren(idx):
                yield from self.walk(idx)
            else:
                yield idx

        

    def childrens(self, index: QModelIndex = QModelIndex()):
        if self.hasChildren(index):
            return [self.index(i,0, index) for i in range(self.rowCount(index))]

        else:
            return []

    ##############
    # Handlers 
    ##############
    # def _on_context_menu_request(self, pos: QPoint, selection: List[QModelIndex]):
    #     for item in selection:
    #         if isinstance(item.internalPointer(), Argument):
    #             context_menu = QMenu("Argument selection")
    #         else:
    #             return

    # def _on_double_click_item_in_view(self, index: QModelIndex):
        
    #     node = index.internalPointer()
    #     if type(node) == Argument:
    #         self.setData(index, 100)
            
    # def _on_data_changed(self, first_idx, last_idx):
    #     # handle only the first idx change for now

    ##############
    # Signals connexions 
    ##############

    







    ##
    # Redifined functions
    ##
    def rowCount(self, index: QModelIndex = QModelIndex()):
        if index.isValid():
            return index.internalPointer().child_count()
        return self._root.child_count()

    def columnCount(self, index):
        if index.isValid():
            return index.internalPointer().columns_nb
        return self._root.columns_nb


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


    def removeRows(self, rmv_idxs: List[QModelIndex], parent: QModelIndex = QModelIndex()) -> bool:
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
        kept_childs = [child for child in parent_node.childs if not child in [idx.internalPointer() for idx in idx_to_remove]]
        self.beginRemoveRows(parent, idx_to_remove[0].row(), idx_to_remove[-1].row()) 
        parent_node.childs = kept_childs
        self.endRemoveRows()
        self.layoutChanged.emit()

        return True

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()

        if isinstance(node, NArgument):
            if role == Qt.DisplayRole:
                if index.column() == 0: # 
                    if node.is_linked():
                        return f"{node._arg_infos[0]} = {node.linked_param}"
                    else:
                        return f"{node._arg_infos[0]} = {node._value}"
                # else:
                #     if node.is_linked(): # if linked to a param 
                #         return node.linked_param
                #     else :
                #         return node._value

            elif role == Qt.EditRole:
                return node


            elif role == Qt.FontRole:
                if node.is_linked(): # if linked to a param , gets overidden by the stylesheet
                    font = QFont()
                    font.setItalic(True)
                    font.setBold(True)
                    return font         

        elif isinstance(node, NPart) or isinstance(node, NShape):
            if role == Qt.DisplayRole:
                return node.name # display method's name
            
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
                return (Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            else:
                return (Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)

        if isinstance(node, NPart) or isinstance(node, NShape):
            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable


        else:
            return Qt.ItemIsEnabled

    def setData(self, index, value, role):
        """
        NModel data setter
        """
        

        node = index.internalPointer()
        if role == Qt.EditRole:
            if isinstance(node, NArgument):
                if isinstance(value, tuple): # we assign a paramerter
                    node._linked_param = value[0]
                    node.value = value[1]
                    node._param_name_pidx = value[2]
                    node._param_value_pidx = value[3]
                else:
                    node.value = value
            self.dataChanged.emit(index,index)
            
        
        elif role == Qt.CheckStateRole:
            if isinstance(node, NPart) or isinstance(node, NShape):
                if node.visible:
                    node.hide()
                else:
                    node.display(node._occt_shape)

        
        return True
    
    def insertRows(self, row, count, node: NNode, parent = QModelIndex()):
        idx = self.index(row, 0, parent)
        self.beginInsertRows(idx, row, 1)
        self.endInsertRows()
        self.layoutChanged.emit()

        

    # def insertColumns(self, column, count):
    #     pass


def setup_dummy_model():
    nodes = [NNode("part"+str(i)) for i in range(5)]
    nodes[-1].add_child(NNode(["operation"]))
    model = NModel(nodes)

    return model



if __name__ == "__main__":
    class Table(QtWidgets.QTableView):
        def __init__(self, parent = None) -> None:
            super().__init__(parent=parent)

    app = QtWidgets.QApplication(sys.argv)
    param_table = [["toto",5],["marie",">Z"]]
    table = Table()
    model = ParamTableModel(param_table)
    table.setModel(model)
    table.show()
    sys.exit(app.exec_())