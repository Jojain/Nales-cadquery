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
            # self._label = TDF_TagSource.NewChild_s(parent._label)
            self._row = len(parent._childrens)
            self.name = name
            # TDataStd_Name.Set_s(self._label, TCollection_ExtendedString(self.name))
        else:
            # self._label = TDF_Label()
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


root = NNode(None, "root")

i=0
n1 = NNode(None,"1", root)
n2 = NNode(None,"2", n1)
n3 = NNode(None,"3", n2)
print(n3.root_node.name)

# nd = n3
# while True:
#     # print(nd.child(0))
#     if nd.parent:
#         print("Node "+nd.name+" -> ")
#         nd = nd.parent
#     else:
#         print("Node "+nd.name+" -> ")
#         break