


"""
Reworked code based on
http://trevorius.com/scrapbook/uncategorized/pyqt-custom-abstractitemmodel/
Adapted to Qt5 and fixed column/row bug.
TODO: handle changing data.

Taken from : https://gist.github.com/nbassler/342fc56c42df27239fa5276b79fca8e6
"""

from collections import OrderedDict
import sys
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QModelIndex, QAbstractItemModel
from cadquery import Workplane

from OCP.TDataStd import TDataStd_Name
from OCP.TPrsStd import TPrsStd_AISPresentation
from cadquery.occ_impl.shapes import Shape
from OCP.AIS import AIS_InteractiveObject, AIS_ColoredShape
from OCP.TNaming import TNaming_Builder, TNaming_NamedShape
from nales_alpha.NDS.NOCAF import Application
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.TDF import TDF_Label
from OCP.TCollection import TCollection_ExtendedString

class NNode():
    def __init__(self, data):
        self._data = data
        self._label = None
        if type(data) == tuple:
            self._data = list(data)
        if type(data) is str or not hasattr(data, '__getitem__'):
            self._data = [data]

        self._columncount = len(self._data) 
        self._childrens = []
        self._parent = None
        self._row = 0
        self.name = None

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

    def parent(self):
        return self._parent


    def add_child(self, child: "NNode") -> None:
        child._parent = self
        child._row = len(self._childrens)
        self._childrens.append(child)
        self._columncount = max(child.column_count(), self._columncount)
        self._label = TDF_TagSource.NewChild_s(self._parent._label)
        TDataStd_Name.Set_s(self._label, TCollection_ExtendedString(self.name))




class Root(NNode):
    def __init__(self, storage_format: str = "XmlOcaf"):
        super().__init__(None)
        self._label = TDF_Label()


class Part(NNode):
    def __init__(self, name: str, part: Workplane):
        super().__init__(part)
        self.name = name
        
        bldr = TNaming_Builder(self._label)
        bldr.Generated(shape.wrapped)

        named_shape = bldr.NamedShape()
        self._label.FindAttribute(TNaming_NamedShape.GetID_s(), named_shape)

        self.ais_shape = TPrsStd_AISPresentation.Set_s(named_shape)
        self.ais_shape.Display(update=True)


class Operation(NNode):
    def __init__(self, data, name):
        super().__init__(data)
        self.name = name


        bldr = TNaming_Builder(self._label)
        bldr.Generated(shape.wrapped)

        named_shape = bldr.NamedShape()
        self._label.FindAttribute(TNaming_NamedShape.GetID_s(), named_shape)
        
        #Disable display of the parent shape
        self._parent.ais_shape.Erase()

        #And update the display with the new shape
        self.ais_shape = TPrsStd_AISPresentation.Set_s(named_shape)
        self.ais_shape.Display(update=True)


class Parameter(NNode):
    def __init__(self, data, name):
        super().__init__(data)
        self.name = name


















class NModel(QAbstractItemModel):
    def __init__(self, nodes = None):
        super().__init__()
        self._root = Root(None)
        self.app = Application()


    def add_part(self, name: str, part: Workplane):
        # nb_of_parts = self._root.child_count()
        node = Part(name, part)     
        self.insertRows(self.rowCount(), 1, node)
   
    def add_operations(self, part_name: str, operations: OrderedDict):
        #debug only :
        parts = self._root._childrens
        
        for part in parts:
            if part.name == part_name:
                row = part._row
                break 

        part_idx = self.index(row, 0)
        

        for operation, parameters in reversed(operations.items()):
            operation = Operation(operation, operation)
            self.insertRows(self.rowCount(), 0, operation, part_idx)

            operation_idx = self.index(operation._row, 0, part_idx)

            for param in parameters:
                # pour l'instant j'ai laissé tout les row count à 0 mais il faudrait le modifier
                # pour pouvoir insérer plusieurs paramètres d'un coup
                self.insertRows(self.rowCount(operation_idx),0, Parameter(param, param), operation_idx)
        


    def _add_child(self, node, _parent: QModelIndex = QModelIndex()):
        if not _parent or not _parent.isValid():
            parent = self._root
        else:
            parent = _parent.internalPointer()
        parent.add_child(node)

    # Redifined functions
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
            p = index.internalPointer().parent()
            if p:
                return self.createIndex(p._row, 0, p)
        return QtCore.QModelIndex()



    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            return node.name
        elif role == QtCore.Qt.UserRole:
            return node.data(index.column())
        return None

    # def flags(self, index):
    #     pass

    def setData(self, index, value):
        pass
        #must reimplement dataChanged() signal
    
    def insertRows(self, row, count, node: NNode, parent = QModelIndex()):
        idx = self.index(row, 0, parent)
        self.beginInsertRows(idx, row, 1)
        self._add_child(node, parent)
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
    app = QtWidgets.QApplication(sys.argv)
    mytree = MyTree()
    mytree.tw.show()
    sys.exit(app.exec_())