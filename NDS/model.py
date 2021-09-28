


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
from nales_alpha.utils import get_Workplane_operations



import cadquery as cq

class NNode():
    error = pyqtSignal(str) # is emitted when an error occurs
    def __init__(self, data, name = None, parent = None):
        self._data = data
        self._parent = parent
        if type(data) == tuple:
            self._data = list(data)
        if type(data) is str or not hasattr(data, '__getitem__'):
            self._data = [data]
        self._columncount = len(self._data) 
        self._childrens = []

        if parent:
            parent._childrens.append(self)
            parent._columncount = max(self.column_count(), parent._columncount)
            self._label = TDF_TagSource.NewChild_s(parent._label)
            self._row = len(parent._childrens)
            self.name = name
            TDataStd_Name.Set_s(self._label, TCollection_ExtendedString(self.name))
        else:
            self._label = TDF_Label()
            self._name = "root"
            self._row = 0

        






    def data(self, column):
        if column >= 0 and column < len(self._data):
            return self._data[column]

    def column_count(self):
        return self._columncount

    def child_count(self):
        return len(self._childrens)

    def child(self, row):
        if row >= 0 and row < self.child_count():
            return self._childrens[row]


    def has_children(self):
        if len(self._childrens) != 0:
            return True
        else: 
            return False

    @property
    def parent(self):
        return self._parent

    @property
    def childs(self):
        return self._childrens

    @property
    def name(self):
        return self._name 

    @name.setter 
    def name(self, value):
        self._name = value    


    @property
    def root_node(self):
        root = self.parent
        while True:
            if root.parent:
                root = root.parent
            else:
                return root

    # def add_child(self, child: "NNode") -> None:
    #     child._parent = self
    #     child._row = len(self._childrens)
    #     self._childrens.append(child)
    #     self._columncount = max(child.column_count(), self._columncount)
    #     self._label = TDF_TagSource.NewChild_s(self._parent._label)
    #     TDataStd_Name.Set_s(self._label, TCollection_ExtendedString(self.name))



class Part(NNode):

    # viewer_updated = pyqtSignal()

    def __init__(self, name: str, part: Workplane, parent):
        super().__init__(part, name, parent=parent)
        
        if len(part.objects) != 0:

            self.occt_shape = part.val().wrapped

        self.occt_shape = TopoDS_Shape()

        self.display(self.occt_shape)

    def display(self, shape: TopoDS_Shape, update = False):
        """
        Builds the display object and attach it to the OCAF tree
        """
        if update:
            self.ais_shape.Erase(remove=True)
            self.root_node._viewer.Update()
            # self.root_node._viewer
            # return

        self.bldr = TNaming_Builder(self._label) #_label is  TDF_Label
        self.bldr.Generated(shape)

        named_shape = self.bldr.NamedShape()
        self._label.FindAttribute(TNaming_NamedShape.GetID_s(), named_shape)

        self.ais_shape = TPrsStd_AISPresentation.Set_s(named_shape)
        # self.ais_shape = TPrsStd_AISPresentation.Set_s(self._label, TNaming_NamedShape.GetID_s())
        self.ais_shape.Display(update=True)
        self.root_node._viewer.Update()


    def rebuild(self, param_edited: "Argument" = None) :
        """
        Reconstruit le workplane et le réaffiche
        Il faut voir si je peux faire un truc du style:

        new_wp = old.end(n) avec n la pos de l'opération du param modifié
        for operations in self.childs:
            new_wp += operation(args)
        """

        #Pour l'instant on rebuild tout le Workplane
        # Mais il faut recup param_edited, localiser la

        #Il faudrait créer un AST Tree mais pour l'instant on fait ça salement

        wp_rebuilt = "cq.Workplane()"

        for operation in self.childs:
            args = str(tuple(param.value for param in operation.childs))
            wp_rebuilt += "."+operation.data(0) + args 

        wp = eval(wp_rebuilt)
        self.occt_shape = wp.val().wrapped

        self.display(self.occt_shape, update=True)




class Operation(NNode):
    def __init__(self, method_name: str, name, part: Workplane, parent : NNode):
        super().__init__(method_name, name, parent=parent)

        # Here we should modify the parent 'Part' shape with the help of TFunctions
        # Otherwise we will fill the memory with a lot of shapes, but as a start it's ok 
        self.name = method_name
        Workplane_methods = get_Workplane_operations()
        self.method = Workplane_methods[method_name]


        # self.cq_shape = part.val()
        # self.occt_shape = part.val().wrapped
        # bldr = TNaming_Builder(self._label)
        # bldr.Generated(self.occt_shape)

        # named_shape = bldr.NamedShape()
        # self._label.FindAttribute(TNaming_NamedShape.GetID_s(), named_shape)
        
        # #Disable display of the parent shape
        # self._parent.ais_shape.Erase()

    #     self.display(self.occt_shape)

    # def display(self, shape):
    #     """
    #     Builds the display object and attach it to the OCAF tree
    #     """
    #     self.bldr = TNaming_Builder(self._label)
    #     self.bldr.Generated(shape)

    #     named_shape = self.bldr.NamedShape()
    #     self._label.FindAttribute(TNaming_NamedShape.GetID_s(), named_shape)


    #     #And update the display with the new shape
    #     self.ais_shape = TPrsStd_AISPresentation.Set_s(named_shape)
    #     self.ais_shape.Display(update=True)





class Argument(NNode):
    """
    The underlying data of an Argument is as follow :
    name : cq argument name
    value : value
    linked_param : the name of the parameter linked to this arg, None if not connected to any
    type: value type : a voir si je garde ca
    If the Argument is linked to a Parameter, the Parameter name is displayed
    """
    def __init__(self, arg_name:str, value, type,  parent):
        super().__init__(None, arg_name, parent=parent)


        self._name = arg_name
        self._value = value
        self._type = type
        self._linked_param = None

        self._param_name_pidx = None
        self._param_value_pidx = None

        self._get_args_names_and_types()

    def is_linked(self):
        if self._linked_param:
            return True 
        else:
            return False


    def _get_args_names_and_types(self):
        parent_method = self.parent.method
        sig = signature(parent_method)

        args_infos = tuple((p_name, p_obj.annotation) for (p_name, p_obj) in sig.parameters.items() if p_name != "self" )
        self._arg_infos = args_infos[self._row]


    @property
    def linked_param(self):
        if self.is_linked():
            return self._linked_param
        else:
            raise ValueError("This argument is not linked to a param")



    @property
    def name(self):
        return self._name 

    @name.setter 
    def name(self, value):
        self._name = value    


    @property 
    def value(self):
        return self._value
    @value.setter
    def value(self, value):
        try:
            self._value = self._type(value)
        except (ValueError , TypeError) as exp:
            if exp == ValueError:
                error_msg = f"Expected arguments if of type: {self._type} you specified argument of type {type(value)}"
                self.error.emit(error_msg)
            # print(error_msg)

    @property 
    def linked_param(self):
        return self._linked_param
    








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
       

        # Slots connection 

        

    def add_part(self, name: str, part: Workplane):
        node = Part(name, part, self._root)    

        self.dataChanged.connect(node.rebuild) # ce genre de truc devra être géré par le model 
                                                # actuellement le code reconstruirait toutes les parts meme si elles n'ont pas été modifiées

        self.insertRows(self.rowCount(), 1, node)
   
    def add_operations(self, part_name: str, wp: Workplane,  operations: OrderedDict):
        # Implémentation à l'arrache il faudra étudier les TFUNCTIONS et voir comment gérer de l'UNDO REDO
        parts = self._root._childrens
        
        for part in parts:
            if part.name == part_name:
                row = part._row
                parent_part = part
                break 

        part_idx = self.index(row, 0)
        
        
        for operation, parameters in reversed(operations.items()):
            operation = Operation(operation, operation, wp, parent_part)
            self.insertRows(self.rowCount(), 0, operation, part_idx)

            operation_idx = self.index(operation._row, 0, part_idx)

            for param_value in parameters:
                # pour l'instant j'ai laissé tout les row count à 0 mais il faudrait le modifier
                # pour pouvoir insérer plusieurs paramètres d'un coup

                # ---------- Il faudra récupérer le vrai ARG name ici et pas passer deux fois le param value comme un sale
                self.insertRows(self.rowCount(operation_idx),0, Argument(str(param_value), param_value, type(param_value), operation), operation_idx)
        
        parent_part.rebuild()

    def _link_parameters(self, indexes: List[QModelIndex], name_pidx:QPersistentModelIndex, value_pidx:QPersistentModelIndex):
        
        for idx in indexes:
            self.setData(idx, (name_pidx.data(), value_pidx.data(), name_pidx, value_pidx), Qt.EditRole)

    
        for part_idx in self.childrens():
            part_idx.internalPointer().rebuild()

    def _disconnect_parameter(self, arg_idx: QModelIndex = None, param_idx: QModelIndex = None):
        if arg_idx and not param_idx:
            arg = arg_idx.internalPointer()
            arg._linked_param = None 
            self.dataChanged.emit(arg_idx, arg_idx)

        elif param_idx and not arg_idx:
            for idx in self.walk():
                node = idx.internalPointer()

                if isinstance(node, Argument) and node.is_linked():
                    
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
            if isinstance(node, Argument):
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

        

    

    def _add_child(self, node, _parent: QModelIndex = QModelIndex()):
        if not _parent or not _parent.isValid():
            parent = self._root
        else:
            parent = _parent.internalPointer()
        parent.add_child(node)


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
            return index.internalPointer().column_count()
        return self._root.column_count()


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



    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()

        if isinstance(node, Argument):
            if role == Qt.DisplayRole:
                if index.column() == 0:
                    return node._arg_infos[0]
                else:
                    if node.is_linked(): # if linked to a param 
                        return node.linked_param
                    else :
                        return node._value
            elif role == Qt.FontRole:
                if node.is_linked(): # if linked to a param , gets overidden by the stylesheet
                    font = QFont()
                    font.setItalic(True)
                    font.setBold(True)
                    return font         

        elif isinstance(node, Operation):
            if role == Qt.DisplayRole:
                return node.name # display method's name

        if role == Qt.DisplayRole:
            return node.name
        elif role == Qt.UserRole:
            return node.data(index.column())

        elif role == Qt.EditRole:
            return node
        
 


        return None

    def flags(self, index):
        node = index.internalPointer()
        if isinstance(node, Argument):
            if node.is_linked():
                return (Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            else:
                return (Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
        else:
            return Qt.ItemIsEnabled

    def setData(self, index, value, role):
        
        node = self.data(index, role = role)
        if isinstance(node, Argument):
            if isinstance(value, tuple): # we assign a paramerter
                node._linked_param = value[0]
                node.value = value[1]
                node._param_name_pidx = value[2]
                node._param_value_pidx = value[3]
                return True

            node.value = value

        self.dataChanged.emit(index,index)
        return True
    
    def insertRows(self, row, count, node: NNode, parent = QModelIndex()):
        idx = self.index(row, 0, parent)
        self.beginInsertRows(idx, row, 1)
        self.endInsertRows()
        self.layoutChanged.emit()

        

    def insertColumns(self, column, count):
        pass


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