"""
Reworked code based on
http://trevorius.com/scrapbook/uncategorized/pyqt-custom-abstractitemmodel/
Adapted to Qt5 and fixed column/row bug.
TODO: handle changing data.
"""

import sys
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QModelIndex, QAbstractItemModel
from cadquery import Workplane

class Dummy():
    def __init__(self):

        pass
    def __repr__(self):
        return "dummy"

class NNode(object):
    def __init__(self, data):
        self._data = data
        if type(data) == tuple:
            self._data = list(data)
        if type(data) is str or not hasattr(data, '__getitem__'):
            self._data = [data]

        self._columncount = 3#len(self._data)
        self._children = []
        self._parent = None
        self._row = 0

    def mdata(self, column):
        if column >= 0 and column < len(self._data):
            return self._data[column]

    def column_count(self):
        return self._columncount

    def childCount(self):
        return len(self._children)

    def child(self, row):
        if row >= 0 and row < self.childCount():
            return self._children[row]

    def parent(self):
        return self._parent

    def row(self):
        return self._row

    def add_Child(self, child):
        child._parent = self
        child._row = len(self._children)
        self._children.append(child)
        self._columncount = max(child.column_count(), self._columncount)


class NModel(QtCore.QAbstractItemModel):
    def __init__(self, nodes):
        QtCore.QAbstractItemModel.__init__(self)
        self._root = NNode(None)
        for node in nodes:
            self._root.add_Child(node)

    def rowCount(self, index):
        if index.isValid():
            return index.internalPointer().childCount()
        return self._root.childCount()

    def addChild(self, node, _parent):
        if not _parent or not _parent.isValid():
            parent = self._root
        else:
            parent = _parent.internalPointer()
        parent.add_Child(node)


    # Overriden Qt Methods
    def index(self, row, column, _parent=None):
        if not _parent or not _parent.isValid():
            parent = self._root
        else:
            parent = _parent.internalPointer()
        child = parent.child(row)
        if child:
            return QtCore.QAbstractItemModel.createIndex(self, row, column, child)
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        if index.isValid():
            p = index.internalPointer().parent()
            if p:
                return QtCore.QAbstractItemModel.createIndex(self, p.row(), 0, p)
        return QtCore.QModelIndex()

    def columnCount(self, index):
        if index.isValid():
            return index.internalPointer().column_count()
        return self._root.column_count()

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            return node.mdata(index.column())
        elif role == QtCore.Qt.UserRole:
            print("toto")
        return None

    def setData(self, index, value):
        pass

    def insertRows(self, row, count, data, parent):
        root_idx = self.index(0, 0) if not parent.isValid() else parent
        self.beginInsertRows(root_idx, row, count)
        for d in data:
            self.addChild(NNode((str(Dummy()),d,6)), parent)
        self.endInsertRows()
        self.layoutChanged.emit()



class MyTree(QtWidgets.QMainWindow):
    """
    """
    def __init__(self):
        super().__init__()
        self.items = []

        # Set some random data:
        for i in 'abc':
            self.items.append(NNode(i))
            self.items[-1].add_Child(NNode(['d', 'e', 'f']))
            self.items[-1].add_Child(NNode(['g', 'h', 'i']))

        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        
        self.tw = QtWidgets.QTreeView()
        self.model = NModel(self.items)
        self.tw.setModel(self.model)

        btn = QtWidgets.QPushButton("toto")
        btn2 = QtWidgets.QPushButton("print")
        layout.addWidget(self.tw)
        layout.addWidget(btn)

        self.setCentralWidget(container)

        btn.clicked.connect(lambda x: self.add_item())

        self.l = iter("xyz")


    def add_item(self):
        
        idx = self.model.index(1, 0)
        # print(idx.internalPointer()._data)
        # self.model.insertRows(0,1, ["to", "ta"], idx)

        self.model.addChild(NNode((str(Dummy()),["to", "ta"],6)), idx)
        self.model.layoutChanged.emit()




if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mytree = MyTree()
    mytree.show()
    sys.exit(app.exec_())