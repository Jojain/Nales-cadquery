#%%
from typing import Any
from PyQt5.QtCore import QObject
import ast
# import astpretty
from ast import Expr, Assign, Name, Call, Store, Attribute, Load, Constant, Expression, Module
import cadquery.cqgi
from cadquery import Workplane
from cadquery.occ_impl.shapes import Shape
import cadquery as cq
from collections import OrderedDict
from nales_alpha.utils import get_Workplane_operations, get_cq_topo_classes, get_shapes_classes_methods
from nales_alpha.NDS.ast_grapher import make_graph

class CallAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.call_type = "undefined"
        self._temp_parent = None
        self.root = None


    def generic_visit(self, node: ast.Call) -> Any:
        
        #We make sure the first node passed to the Analyzer is a Call node
        if not self.root:
            self.root = node
            if not isinstance(node, ast.Call):
                raise ValueError(f"{ast.Call} expected got {type(node)}")

        node.parent =  self._temp_parent
        self._temp_parent = node

        try:    
            if node.id == "cq":
                if node.parent.attr == "Workplane":
                    self.call_type = "Workplane_assign"
                elif node.parent.attr in get_cq_topo_classes():
                    self.call_type = "Shape_assign"

        except AttributeError:
            pass

        super().generic_visit(node)


    

class CommandAnalyzer(ast.NodeVisitor):
    def __init__(self, namespace: dict, ns_before_cmd: dict, debug = False):
        self.cmd = Command() 
        self.ns_before_cmd = ns_before_cmd
        self.ns = namespace
        self.cmd.operations = OrderedDict()
        self.cmd.invoked_method = {}

        
        self.debug = debug

    def visit_Module(self, node: Module) -> Any:
        if self.debug:
            self.graph = make_graph(node)

        self.generic_visit(node)

    def visit_Call(self, node):
        # astpretty.pprint(node, show_offsets = False, indent = "    ")
        func = node.func
        if type(node.func) == Attribute:            
            attribute = func.attr
            if attribute == "Workplane":
                self.cmd.type = "new_part"
            if attribute in get_Workplane_operations().keys():
                # If every node.args is a constant :
                try:
                    self.cmd.operations[attribute] = tuple(arg.value for arg in node.args)
                except AttributeError:
                    # else, if an arg is a name (i.e an object):
                    args = []                 
                    for arg in node.args:
                        # since we can have both Constant and Objects :
                        try:
                            args.append(arg.value)
                        except AttributeError:
                            args.append((arg.id,True))
                    self.cmd.operations[attribute] = tuple(args)                        


            else:      
                # Checks if the Call is from a method of CQ Topological Shape class         
                try:
                    func_name = func.attr 
                    func_bounded_class = func.value.attr

                    if func_name in get_shapes_classes_methods(func_bounded_class):
                        self.cmd.invoked_method["class_name"] = func_bounded_class
                        self.cmd.invoked_method["method_name"] = func_name
                        # If every node.args is a constant :
                        try:
                            args = tuple(arg.value for arg in node.args)
                        except AttributeError:
                            # else, if an arg is a name (i.e an object):
                            args = []                 
                            for arg in node.args:
                                # since we can have both Constant and Objects :
                                try:
                                    args.append(arg.value)
                                except AttributeError:
                                    args.append(arg.name)

                        self.cmd.invoked_method["args"] = tuple(args)
                               


                except AttributeError:
                    #
                    pass
                        

        self.generic_visit(node)
    

    def visit_Assign(self, node):

        target = node.targets[0]
        # On considère qu'on a jamais de cas tel que a = b = monObj
        # Donc on s'occupe que de la première target
        self.cmd.var = var = target.id
        call_type = self._get_assign_type(node)

        try:
            obj = self.ns[self.cmd.var] 
        except KeyError: 
            raise KeyError(f"{self.cmd.var} variable doesnt exists in the console namespace")

        if not var in self.ns_before_cmd.keys():
            if call_type == "Workplane_assign":
                self.cmd.type = "new_part"
                self.cmd.part = obj
            elif call_type == "Shape_assign":
                self.cmd.type = "new_shape"
                self.cmd.shape = obj


        elif var in self.ns_before_cmd.keys():
            if call_type == "Workplane_assign":
                self.cmd.type = "part_edit"
                self.cmd.part = obj
            elif call_type == "Shape_assign":
                self.cmd.type = "shape_edit"    
                self.cmd.shape = obj


        self.generic_visit(node)


    def _get_assign_type(self, node) -> str:
        """
        Decipher is a assignment node is a cadquery one
        The current implementation only considers assignments invoked with a Call ast node.
        For example, if the var sphere is a cq object, `new_sphere = sphere` won't be considered as a cq type assignment

        :returns: a string reprensenting the type, valid values are 'Workplane' , 'Shape', 'undefined'
        """
        call_analyzer = CallAnalyzer()

        if isinstance(node.value, ast.Call):
            call_analyzer.visit(node.value)

        return call_analyzer.call_type

    def get_command(self):
        return self.cmd

class Command():
    """
    This class is used to interface the GUI, the backend and the frontend
    Command object store information about how the application should be changed/updated

    It's designed to receive chode chunks and return information about what this code should do to the application
    It review code_chunks with ast nodes

    Command types are given below :
     - new_part
     - part_edit
    """

    def __init__(self):
        self.type = "undefined"


if __name__ == "__main__":
    
    import cadquery as cq
    from cadquery import cq
    from astmonkey import visitors, transformers
    debug = True
    cmd = "a = Workplane().box(1,1,1).sphere(2)"
    cmd_analyzer = CommandAnalyzer(globals(), globals(), True) # call this line in the ipython window to view the graph

    cmd_analyzer.visit(ast.parse(cmd))

    graph = cmd_analyzer.graph
   
# %%
