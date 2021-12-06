
import ast
from inspect import signature
from typing import Union
from PyQt5.QtCore import  QModelIndex, QObject, pyqtSignal
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
from nales_alpha.utils import PY_TYPES_TO_AST_NODE, get_Workplane_methods
from OCP.Quantity import Quantity_NameOfColor

import cadquery as cq

import debugpy
debugpy.debug_this_thread()

class NNode():
    # error = pyqtSignal(str) # is emitted when an error occurs
    def __init__(self, data, name = None, parent = None):
        self._data = data
        self._parent = parent
        if type(data) == tuple:
            self._data = list(data)
        if type(data) is str or not hasattr(data, '__getitem__'):
            self._data = [data]
        self._columns_nb = len(self._data) 
        self._childs = []

        if parent:
            parent._childs.append(self)
            parent._columns_nb = max(self.columns_nb, parent.columns_nb)
            self._label = TDF_TagSource.NewChild_s(parent._label)
            self._row = len(parent._childs)
            self._name = name
            TDataStd_Name.Set_s(self._label, TCollection_ExtendedString(self.name))
        else:
            self._label = TDF_Label()
            self._name = "root"
            self._row = 0

        

    def __str__(self):
            return f"{self.name}"


    def walk(self, node: "NNode" = None) -> "NNode":
        base_node = node if node else self       
    
        yield base_node

        for child in base_node.childs:      
            yield from self.walk(child)
    

    def find(self, node_name: str, node_type = None) -> "NNode" or None:
        for node in self.walk():
            if node.name == node_name:
                if node_type:
                    if isinstance(node, node_type):                    
                        return node 
                else:
                    return node

                



    def data(self, column):
        if column >= 0 and column < len(self._data):
            return self._data[column]

    @property
    def columns_nb(self):
        # return 3
        return self._columns_nb

    def child_count(self):
        return len(self._childs)

    def child(self, row) -> "NNode":
        if row >= 0 and row < self.child_count():
            return self._childs[row]


    def has_children(self):
        if len(self._childs) != 0:
            return True
        else: 
            return False

    @property
    def parent(self):
        return self._parent

    @property
    def childs(self):
        return self._childs
    @childs.setter
    def childs(self, new_childs):
        self._childs = new_childs
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

class NPart(NNode):

    # viewer_updated = pyqtSignal()

    def __init__(self, name: str, part: Workplane, parent):
        super().__init__(part, name, parent=parent)
        self.part = part
        self.visible = True 
        self._solid = TopoDS_Shape()
        self._active_shape = None

        # if len(part.objects) != 0:

        #     self._occt_shape = part.val().wrapped
        # else:
        #     self._occt_shape = TopoDS_Shape()

        self.display()


    
    def update_display_shapes(self):
        solid = self.part.findSolid(internal_call = True).wrapped
        self._solid = solid
       
        if active_shape := self.part.val(internal_call = True).wrapped is solid:
            self._active_shape = None 
        else:
            self._active_shape = active_shape



    def hide(self):

        self.visible = False
        self.ais_shape.Erase(remove=True)
        self.root_node._viewer.Update()

    def display(self, update = False):
        """
        Builds the display object and attach it to the OCAF tree
        """
        

        if update:
            self.ais_shape.Erase(remove=True)
            self.update_display_shapes()
            self.root_node._viewer.Update()


        self.bldr = TNaming_Builder(self._label) #_label is  TDF_Label
        self.bldr.Generated(self._solid)

        named_shape = self.bldr.NamedShape()
        self._label.FindAttribute(TNaming_NamedShape.GetID_s(), named_shape)

        # self.ais_shape = TPrsStd_AISPresentation.Set_s(named_shape)
        self.ais_shape = TPrsStd_AISPresentation.Set_s(self._label, TNaming_NamedShape.GetID_s())
        # self.ais_shape.SetTransparency(0.1)
        self.ais_shape.Display(update=True)
        self.root_node._viewer.Update()

        self.visible = True




class NShape(NNode):
    def __init__(self, name, cq_shape, invoked_method: dict, parent : NNode):       

        self._occt_shape = shape = cq_shape.wrapped 
        self._source_code = self._retrieve_source_code(invoked_method)
        self.visible = False
        super().__init__(shape, name, parent=parent)

        # self.display(self._occt_shape)

    def _retrieve_source_code(self, invoked_method: dict) -> str:
        source = f"cq.{invoked_method['class_name']}.{invoked_method['method_name']}{invoked_method['args']}"
        return source

    def hide(self):
        self.visible = False
        self.ais_shape.Erase()
        self.root_node._viewer.Update()

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
        self.ais_shape.SetTransparency(0.5)
        self.ais_shape.SetColor(Quantity_NameOfColor.Quantity_NOC_ALICEBLUE)     
        self.ais_shape.Display(update=True)
        self.root_node._viewer.Update()

        self.visible = True

    def _update(self):

        code = self.source_code
        exec(code, self.root_node.console_namespace)    

class NOperation(NNode):


    def __init__(self, method_name: str, name, part: Workplane, parent : NNode):
        super().__init__(method_name, name, parent=parent)
        self.parent.part = part
        
        self.name = method_name
        self.method = getattr(part,method_name).__func__
        

        if method_name == "Workplane":
            self._root_operation = True 
        else:
            self._root_operation = False

               
    def _update(self, pos):
        part = self.parent.part 
        part = part.end(pos, internal_call=True)
        args = [child.value for child in self.childs]      
        part = self.method(part,*args, internal_call = True)  
        # part = self.method(internal_call = True)  
        self.parent.part = part
        # self.parent.part = self.method(*args, internal_call = True)

            






class NArgument(NNode):
    """
    The underlying data of an Argument is as follow :
    name : cq argument name
    value : value
    linked_param : the name of the parameter linked to this arg, None if not connected to any
    type: value type : a voir si je garde ca
    If the Argument is linked to a Parameter, the Parameter name is displayed
    """
    def __init__(self, arg_name:str, value, parent, kwarg=False):
        super().__init__(None, arg_name, parent=parent)

        self._name = arg_name
        if type(value) == str and (value in self.root_node.console_namespace.keys()):
            self._type = type(self.root_node.console_namespace[value])
            self._value = self.root_node.console_namespace[value]
        else:
            self._type = type(value)
            self._value = value
            
        self._kwarg = kwarg # Boolean indicating if the arg is a kwarg or not
        

        self._linked_param = None
        self._linked_obj = None

        self._param_name_pidx = None
        self._param_value_pidx = None
        

        self._get_args_names_and_types()


    def is_kwarg(self):
        return self._kwarg

    def is_linked(self):
        if self._linked_param or self._linked_obj:
            return True 
        else:
            return False
    

    def _get_args_names_and_types(self):
        parent_method = self.parent.method
        sig = signature(parent_method)

        args_infos = tuple((p_name, p_obj.annotation) for (p_name, p_obj) in sig.parameters.items() if p_name != "self" )
        self._arg_infos = args_infos[self._row-1]


    @property
    def linked_param(self):
        if self.is_linked():
            return self._linked_param
        else:
            raise ValueError("This argument is not linked to a param")

    @property
    def linked_obj(self):
        if self.is_linked():
            return self._linked_obj
        else:
            raise ValueError("This argument is not linked to an object")

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
        if self._type is type(None):
            return None
        if self.is_linked():
            return self._type(self._param_value_pidx.data())
        else:            
            return self._type(self._value)

    @value.setter
    def value(self, value):
        self._value = value
        # if self.is_linked():
        #     self._value = value 
        # else:
        #     try:    
        #         self._value = self._type(value)
        #     except (ValueError , TypeError, AttributeError) as exp:
        #         if exp == ValueError or exp == AttributeError:
        #             error_msg = f"Expected arguments if of type: {self._type} you specified argument of type {type(value)}"
        #             print(error_msg)


    @property 
    def linked_param(self):
        return self._linked_param
    

