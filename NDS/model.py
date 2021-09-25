


"""
Reworked code based on
http://trevorius.com/scrapbook/uncategorized/pyqt-custom-abstractitemmodel/
Adapted to Qt5 and fixed column/row bug.
TODO: handle changing data.

Taken from : https://gist.github.com/nbassler/342fc56c42df27239fa5276b79fca8e6
"""

from collections import OrderedDict
from typing import Iterable, List
import sys
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QModelIndex, QAbstractItemModel, QAbstractTableModel, Qt, pyqtSignal
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


    def rebuild(self, param_edited: "Parameter" = None) :
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
            args = str(tuple(param.data(2)((param.data(0))) for param in operation.childs))
            wp_rebuilt += "."+operation.data(0) + args 

        wp = eval(wp_rebuilt)
        self.occt_shape = wp.val().wrapped

        self.display(self.occt_shape, update=True)




class Operation(NNode):
    def __init__(self, method_name: str, name, part: Workplane, parent : NNode):
        super().__init__(method_name, name, parent=parent)

        # Here we should modify the parent 'Part' shape with the help of TFunctions
        # Otherwise we will fill the memory with a lot of shapes, but as a start it's ok 
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





class Parameter(NNode):
    def __init__(self, method_args: Iterable, name, parent):
        super().__init__(method_args, name, parent=parent)
        
        self.method_args = method_args

    
    @property
    def name(self):
        self._name = self._data[0] # petit truc hacky a modifier plus tard
        return self._name 

    @name.setter 
    def name(self, value):
        self._name = value    












class ParamTableModel(QAbstractTableModel):
    def __init__(self, param_table: List[list]):
        super().__init__()
        self._data = param_table

    def add_parameter(self):
        self.insertRows(self.rowCount())


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



    def rowCount(self, parent: QModelIndex) -> int:
        return len(self._data)
    
    def columnCount(self, parent: QModelIndex) -> int:
        # there is only two columns in the param table
        return 2

    # def index(self, row, column):
    #     return self.createIndex(row, column)

    def setData(self, index, value, role):
        if role == Qt.EditRole:
            self._data[index.row()][index.column()] = value
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

            for param in parameters:
                # pour l'instant j'ai laissé tout les row count à 0 mais il faudrait le modifier
                # pour pouvoir insérer plusieurs paramètres d'un coup
                self.insertRows(self.rowCount(operation_idx),0, Parameter([param,None,type(param)], param, operation), operation_idx)
        
        parent_part.rebuild()

    def update_display(self, index, index2):
        """
        Update the display of the Part linked to :index:
        """
        pass

        




    def _add_child(self, node, _parent: QModelIndex = QModelIndex()):
        if not _parent or not _parent.isValid():
            parent = self._root
        else:
            parent = _parent.internalPointer()
        parent.add_child(node)


    ##############
    # Handlers 
    ##############

    # def _on_double_click_item_in_view(self, index: QModelIndex):
        
    #     node = index.internalPointer()
    #     if type(node) == Parameter:
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
        if role == Qt.DisplayRole:
            if isinstance(node, Parameter):
                return node.data(0)
            else:
                return node.name
        elif role == Qt.UserRole:
            return node.data(index.column())

        elif role == Qt.EditRole:
            return node

        return None

    def flags(self, index):
        
        if type(index.internalPointer()) == Parameter:
            return (Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
        else:
            return Qt.ItemIsEnabled

    def setData(self, index, value, role):
        
        node = self.data(index, role = role)
        node._data = [value,None,node._data[2]]
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