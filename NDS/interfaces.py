
import ast
from inspect import signature
from typing import Union
from PyQt5.QtCore import  QModelIndex, pyqtSignal
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
from nales_alpha.utils import PY_TYPES_TO_AST_NODE, get_Workplane_operations
from OCP.Quantity import Quantity_NameOfColor

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

class NBuildable():
    """
    Abstract class the needs to be subclassed
    It provides utilities to work with the AST nodes each interface classe can holds
    """
    cmd_ast = None

class NPart(NNode):

    # viewer_updated = pyqtSignal()

    def __init__(self, name: str, part: Workplane, parent):
        super().__init__(part, name, parent=parent)
        
        self.visible = True 

        if len(part.objects) != 0:

            self._occt_shape = part.val().wrapped

        self._occt_shape = TopoDS_Shape()

        self.display()


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
            self.root_node._viewer.Update()


        self.bldr = TNaming_Builder(self._label) #_label is  TDF_Label
        self.bldr.Generated(self._occt_shape)

        named_shape = self.bldr.NamedShape()
        self._label.FindAttribute(TNaming_NamedShape.GetID_s(), named_shape)

        self.ais_shape = TPrsStd_AISPresentation.Set_s(named_shape)
        # self.ais_shape = TPrsStd_AISPresentation.Set_s(self._label, TNaming_NamedShape.GetID_s())
        # self.ais_shape.SetTransparency(0.1)
        self.ais_shape.Display(update=True)
        self.root_node._viewer.Update()
        # self.root_node._viewer.fit()

        self.visible = True

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

        obj = self.root_node.console_namespace[self.name]
        self._occt_shape = obj.val().wrapped
        if self.visible:
            self.display()


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

class NOperation(NNode, NBuildable):

    updated = pyqtSignal()

    def __init__(self, method_name: str, name, part: Workplane, parent : NNode):
        super().__init__(method_name, name, parent=parent)

        # Here we should modify the parent 'Part' shape with the help of TFunctions
        # Otherwise we will fill the memory with a lot of shapes, but as a start it's ok 
        self.name = method_name
        self.visible = False
        Workplane_methods = get_Workplane_operations()
        self.method = Workplane_methods[method_name]
        self._ast_node = self._get_ast()

    def __repr__(self) -> str:
        pass

    def _get_ast(self) -> ast.Call:
        """
        Creates an AST node 
        """

        args_nodes = []
        kwargs_nodes = []
        for child in self._childs:
            if child.is_kwarg:
                kwargs_nodes.append(child.ast_node)
            else:
                args_nodes.append(child.ast_node)

        part_name = ast.Name(self._parent.name, ctx = ast.Store())
        

        

        assign_val = ast.parse(f"{self._parent.name}.end(0)").body[0].value #it's just easier to let python make the nodes for us
        method_node = ast.Attribute(assign_val,self.name, ctx = ast.Load())        
        method_call = ast.Call(func = method_node, args=args_nodes, keywords=kwargs_nodes) 

        assign = ast.Assign(targets = [part_name], value = method_call, type_comment = None)        
        module = ast.Module([assign], type_ignores = None)        
        ast.fix_missing_locations(module)
        return module


                
    def update(self, idx: QModelIndex):
        if idx.parent().internalPointer() == self:
            # pos = idx.row()
            pos = self._row
            node = self._get_ast()
            # self._ast_node = node =  update_operation_index(node, pos)

            import pickle
            with open(r"D:\Projets\Nales\nales_alpha\temp_test\toto", "wb") as out:
                pickle.dump(node, out)

            code = compile(node,"nales", "exec")
            exec(code, self.root_node.console_namespace)
            

            self.updated.emit()       
                






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

        self._param_name_pidx = None
        self._param_value_pidx = None
        

        self._get_args_names_and_types()

    # def __repr__(self) -> str:
    #     return 


        

    @property
    def ast_node(self):
        #on considère atm que les types builtins 
        try:
            raw = ast.literal_eval(str(self._value))
        except SyntaxError:
            raise ValueError("Wrong arg value")
        arg_type = type(raw)
        

        constant_node = PY_TYPES_TO_AST_NODE[arg_type](value = self._value, kind=None)
        if self.is_kwarg():
            kw_node = ast.keyword(arg=self.name, value = constant_node)
            ast.fix_missing_locations(kw_node)
            return kw_node
        else:
            ast.fix_missing_locations(constant_node)
            return constant_node

 

    def is_kwarg(self):
        return self._kwarg

    def is_linked(self):
        if self._linked_param:
            return True 
        else:
            return False
    
    def _get_shape_source(self):
        """
        A SUPPRIMER / NArgument should not be able to go back the tree like that

        If the Argument is a cq shape object we retrieve the source code to be able to rebuild everything from scratch        
        """
        var_name = self.name

        for shape_node in self.walk(self.root_node.child(1)):
            if var_name == shape_node.name:
                return shape_node._source_code

    

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

    @property 
    def linked_param(self):
        return self._linked_param
    

