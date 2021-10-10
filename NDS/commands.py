#%%
from typing import Any
from PyQt5.QtCore import QObject
import ast
# import astpretty
from ast import Expr, Assign, Name, Call, Store, Attribute, Load, Constant, Expression, Module, Del, iter_child_nodes, walk
import cadquery.cqgi
from cadquery import Workplane
from cadquery.occ_impl.shapes import Shape
import cadquery as cq
from collections import OrderedDict
from graphviz.backend import command
from nales_alpha.utils import get_cq_class_kwargs_name, get_cq_topo_classes, get_cq_types, get_Wp_method_kwargs, get_topo_class_kwargs_name
from nales_alpha.NDS.ast_grapher import make_graph


     

def prepare_parent_childs(tree):
    """
    Adds parent and chils attributes to ast nodes
    """
    for node in ast.walk(tree):
        node.childs = []
        for child_node in ast.iter_child_nodes(node):
            node.childs.append(child_node)
            child_node.parent = node

class CQCallAnalyze(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.sub_cmd = Command()


    def visit_Call(self, node: Call) -> None:
        
        

        self.generic_visit(node)

class CommandAnalyzer(ast.NodeVisitor):
    def __init__(self, ns, ns_before_cmd) -> None:
        super().__init__()
        self._console_ns = ns
        self._console_ns_before_cmd = ns_before_cmd
        self.commands = []

    def visit_Module(self, mnode: Module) -> Any:
        for node in mnode.body:
            if isinstance(node, Assign):
                analyzer = CQAssignAnalyzer(self._console_ns, self._console_ns_before_cmd)        
                analyzer.visit(node)
                self.commands.append(analyzer.get_command())

class CQAssignAnalyzer(ast.NodeVisitor):
    def __init__(self, ns, ns_before_cmd) -> None:
        super().__init__()
        self._console_ns = ns
        self._console_ns_before_cmd = ns_before_cmd
        self._cq_assign_type = None
        self._assigned_node = None
        self._root_call_node = None
        self._cmd = Command()
        self.sub_commands = []
        
        


    def _get_root_node_from_Call(self, node: Call) -> Name:
        """
        Gets the root of a chain call
        for example 'p = a.b.c.d()' would isolate the Name node linked to 'a'
        """
        assert isinstance(node, Call)

        call_root = None

        for sub_node in walk(node):
            if isinstance(sub_node, Name):
                # This is needed if we have nested calls, for example :
                # u = cq.Edge.makeLine(cq.Vector(1,1,1), cq.Vector(1,1,2))
                # It makes sure to return the Name node bounded to cq.Edge and not to cq.Vector
                if call_root:
                    node_call = sub_node
                    while not isinstance(node_call, Call):
                        node_call = node_call.parent
                    if node_call is node:
                        call_root = sub_node
                        
                else:
                    call_root = sub_node
                
        return call_root

    def _is_Workplane(self, var_name) -> bool:
        try:
            obj_type  = self._console_ns[var_name]          
        except KeyError:            
            return False
        if isinstance(obj_type,Workplane):
            return True
    

    def _is_Shape(self, var_name) -> bool:
        try:
            obj_type  = self._console_ns[var_name]          
        except KeyError:            
            return False
        if isinstance(obj_type,Shape):
            return True
    
    def _is_cq_obj(self, var_name: str) -> bool:
        cq_types = get_cq_types()
        try:
            obj  = self._console_ns[var_name]          
        except KeyError:            
            return False
        if type(obj) in cq_types:
            return True


    def _cq_call_type(self, node: Call) -> str:

        call_root = self._get_root_node_from_Call(node)
        if call_root.id == "cq":
            if call_root.parent.attr in get_cq_topo_classes():
                call_type = "Shape"
            elif call_root.parent.attr == "Workplane":
                call_type = "Workplane"
            else:
                call_type = "Other"              

        elif self._is_cq_obj(call_root.id):
            if self._is_Workplane(call_root.id):
                call_type = "Workplane"
            elif self._is_Shape(call_root.id):            
                call_type = "Shape"
            else:
                call_type = "Other"

        return call_type

    def is_cq_assign(self, node: Assign) -> bool:
        """
        Returns if an assignement value is made from a cq object or from cq class

        Also sets the value of `_cq_assign_type` parameter
        """
        self._assigned_node = node.value 

        if isinstance(node.value, Call):
            call_root = self._get_root_node_from_Call(node.value)
        elif isinstance(node.value, Name):
            call_root = node.value
        else:
            return False

        if call_root.id == "cq":
            if call_root.parent.attr in get_cq_topo_classes():
                self._cq_assign_type = "Shape"
            elif call_root.parent.attr == "Workplane":
                self._cq_assign_type = "Workplane"
            else:
                self._cq_assign_type = "Other"              
            return True 

        elif self._is_cq_obj(call_root.id):
            if self._is_Workplane(call_root.id):
                self._cq_assign_type = "Workplane"
            elif self._is_Shape(call_root.id):            
                self._cq_assign_type = "Shape"
            else:
                self._cq_assign_type = "Other"

        else:
            return False
            
            
    def _is_from_main_call_stack(self, node: Any) -> None:

        looked_node = self._root_call_node
        while looked_node != self._assigned_node:
            if looked_node is node:
                return True
            looked_node = looked_node.parent
        return False
        
    def get_command(self) -> "Command":
        cmd = self._cmd
        if cmd.type != "undefined":
            try:
                cmd.obj = self._console_ns[self._cmd.var]
            except KeyError:
                cmd.type = "undefined"
        if cmd.operations:
            cmd.operations = OrderedDict(reversed(list(cmd.operations.items())))
        else:
            cmd.operations = OrderedDict()
        return cmd 



    def _get_operations(self, node: Call):

        assert isinstance(node, Call)
        call_type = self._cq_call_type(node)

        if call_type == "Workplane":
            return self._get_call_stack(node)
        else:
            return self._get_call(node)

    def visit_Call(self, node: Call) -> Any:

        if not self._is_from_main_call_stack(node):

            call_type = self._cq_call_type(node)
            cmd = SubCommand
            self.sub_commands.append(cmd)

            if call_type == "Workplane":
                cmd.type = "new_part"
                    
            elif call_type == "Shape":
                cmd.type = "new_shape"
                cmd.topo_type = node.parent.attr
            else:
                cmd.type = "other"

            cmd.operations = self._get_operations(node)
            

        self.generic_visit(node)


    def visit_Assign(self, node):

        if self.is_cq_assign(node):
            # assign is something like :
            # part = cq.Workplane().box(1,1,1)
            # part = cq.Edge.makeEdge(v1,v2)          
            # part = aCqObj.sphere(5) 
            # vector = cq.Vector(0,0,1) 

            self._cmd.var = node.targets[0].id
            
            if isinstance(node.value, Call):
                self._root_call_node = root_node = self._get_root_node_from_Call(node.value)

            assign_type = self._cq_assign_type

            cmd = self._cmd 
            if assign_type == "Workplane":      
                if root_node.parent.attr == "Workplane" or self._is_Workplane(root_node.id):
                    cmd.type = "new_part"
                else:
                    cmd.type = "part_edit"
                    
            elif assign_type == "Shape":
                cmd.type = "new_shape"
                cmd.topo_type = root_node.parent.attr
            else:
                cmd.type = "other"

            cmd.operations = self._get_operations(node.value)


            # if self._cq_assign_type in ["Workplane, Shape"]:                 
            #     if isinstance(node.value, Call):    
            #         root_node = self._get_root_node_from_Call(node.value)
            #         self._cmd.operations = self._get_call_stack(node.value)
            #     else:
            #         #Node is a Name node referring to a cq object in memory
            #         root_node = node                

            #     try:    
            #         if root_node.id == "cq":
            #             if root_node.parent.attr == "Workplane":
            #                 self._cmd.type = "new_part"

            #             elif root_node.parent.attr in get_cq_topo_classes():
            #                 self._cmd.type = "new_shape"
            #                 self._cmd.topo_type = node.parent.attr
                            
            #         elif root_node.id == self._cmd.var:
            #             self._cmd.type = "part_edit"

            #         elif self._is_Workplane(root_node.id):                    
            #             self._cmd.type = "new_part"

            #     except AttributeError:
            #         pass

            # elif self._cq_assign_type == "Others":
            #     pass


            self.generic_visit(node)

        else:
            # The command is not cq related so we stop the parsing
            return 

    def _get_call(self, node: Call) -> OrderedDict:
        """
        Retrieve the the call of a cq function, and return it as an Ordered dict associating the function to its params
        """
        root = self._get_root_node_from_Call(node)
        
        call = OrderedDict()

        if (class_name := root.parent.attr) in get_cq_topo_classes():
            method_name = root.parent.parent.attr
            kwargs = get_topo_class_kwargs_name(class_name, method_name)
        else:
            method_name = root.parent.attr
            kwargs = get_cq_class_kwargs_name(class_name)

        for invoked_kw in node.keywords:
            kwargs[invoked_kw.arg] = invoked_kw.arg.value.value # override defaults kwargs by the ones passed
    
        call[method_name] = ([arg.value if hasattr(arg, "value") else arg.id for arg in node.args ], kwargs)

        return call

    def _get_call_stack(self, node: Call) -> OrderedDict:
        """
        Retrieve the call stack of a Workplane, and return it as an Ordered dict associating method to parameters
        """
        

        call_stack = OrderedDict()                
        for sub_node in ast.walk(node):
            if isinstance(sub_node, Call):
                method_name = sub_node.func.attr                
                kwargs = get_Wp_method_kwargs(method_name)
                for invoked_kw in sub_node.keywords:
                    kwargs[invoked_kw.arg] = invoked_kw.arg.value.value # override defaults kwargs by the ones passed
                
                call_stack[method_name] = ([arg.value if hasattr(arg, "value") else arg.id for arg in sub_node.args ], kwargs)

        return call_stack



class Command():
    """
    This class is used to interface the GUI, the backend and the frontend
    Command object store information about how the application should be changed/updated

    It's designed to receive chode chunks and return information about what this code should do to the application
    It review code_chunks with ast nodes

    Command types are given below :
     - new_part
     - part_edit
     - part_override
     - new_shape
    """

    def __init__(self):
        self.type = "undefined"
        self.var = None 
        self.operations = None
        self.obj = None
        self.topo_type = None

class SubCommand():
    def __init__(self):
        self.type = "unbound"
        self.operations = None
        self.obj = None
        self.topo_type = None


if __name__ == "__main__":
    import astpretty
    import cadquery as cq
    from cadquery import cq
    from astmonkey import visitors, transformers
    debug = True
    cmd = "a = b.box(1,1,1).sphere(2)\nu = b"
    c=cq.Workplane().box(1,1,1).sphere(2)
    ns = {"cq":cadquery, "b":c}
    ns2 = {"a": 5,"cq":cadquery, "b":c}
    cmd_analyzer = CQAssignAnalyzer(ns2, ns) # call this line in the ipython window to view the graph

    ast_tree = ast.parse(cmd)
    from astmonkey import transformers, visitors
    import graphviz
    visitor = visitors.GraphNodeVisitor()
    node = ParentChildNodeTransformer().visit(ast_tree)
    visitor.visit(node)
    raw_dot = visitor.graph.to_string()
    graph = graphviz.Source(raw_dot)
    cmd_analyzer.visit(node)
    cmd = cmd_analyzer.get_command()
    print(cmd_analyzer.call_stack.items())
   
   
# %%
