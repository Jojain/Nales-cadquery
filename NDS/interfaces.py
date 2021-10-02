
from inspect import signature
from PyQt5.QtCore import  pyqtSignal
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
        self._columns_nb = len(self._data) 
        self._childrens = []

        if parent:
            parent._childrens.append(self)
            parent._columns_nb = max(self.columns_nb, parent.columns_nb)
            self._label = TDF_TagSource.NewChild_s(parent._label)
            self._row = len(parent._childrens)
            self._name = name
            TDataStd_Name.Set_s(self._label, TCollection_ExtendedString(self.name))
        else:
            self._label = TDF_Label()
            self._name = "root"
            self._row = 0

        






    def data(self, column):
        if column >= 0 and column < len(self._data):
            return self._data[column]

    @property
    def columns_nb(self):
        # return 3
        return self._columns_nb

    def child_count(self):
        return len(self._childrens)

    def child(self, row) -> "NNode":
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



class Shape(NNode):
    def __init__(self, name, cq_shape, parent : NNode):       

        self._occt_shape = shape = cq_shape.wrapped 

        super().__init__(shape, name, parent=parent)

        self.display(self._occt_shape)

    def display(self, shape: TopoDS_Shape, update = False):
        """
        Builds the display object and attach it to the OCAF tree
        """
        if update:
            self.ais_shape.Erase(remove=True)
            self.root_node._viewer.Update()
 

        self.bldr = TNaming_Builder(self._label) #_label is  TDF_Label
        self.bldr.Generated(shape)

        named_shape = self.bldr.NamedShape()
        self._label.FindAttribute(TNaming_NamedShape.GetID_s(), named_shape)

        self.ais_shape = TPrsStd_AISPresentation.Set_s(named_shape)
        self.ais_shape.Display(update=True)
        self.root_node._viewer.Update()


class Operation(NNode):
    def __init__(self, method_name: str, name, part: Workplane, parent : NNode):
        super().__init__(method_name, name, parent=parent)

        # Here we should modify the parent 'Part' shape with the help of TFunctions
        # Otherwise we will fill the memory with a lot of shapes, but as a start it's ok 
        self.name = method_name
        Workplane_methods = get_Workplane_operations()
        self.method = Workplane_methods[method_name]





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
    def columns_nb(self):
        return 3

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
    
