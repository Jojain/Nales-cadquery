from PyQt5.QtCore import QObject
import ast
# import astpretty
from ast import Expr, Assign, Name, Call, Store, Attribute, Load, Constant, Expression, Module
import cadquery.cqgi
from cadquery import Workplane
import cadquery as cq
from collections import OrderedDict


class CommandAnalyzer(ast.NodeVisitor):
    def __init__(self, namespace: dict, ns_before_cmd: dict):
        self.cmd = Command() 
        self.ns_before_cmd = ns_before_cmd
        self.ns = namespace
        self.cmd.operations = OrderedDict()

    def visit_Call(self, node):
        # astpretty.pprint(node, show_offsets = False, indent = "    ")

        if type(node.func) == Attribute:
            if node.func.attr != "cq" and node.func.attr != "Workplane": # dont count cq.Workplane() as an operation
                
                self.cmd.operations[node.func.attr] = tuple(arg.value for arg in node.args)

        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            # On considère qu'on a jamais de cas tel que a = b = monObj
            # Donc on s'occupe que de la première target
            self.cmd.var = target.id
        try:
            obj = self.ns[self.cmd.var] 
        except KeyError: 
            return

        if isinstance(obj, Workplane) and not self.cmd.var in self.ns_before_cmd.keys():
            self.cmd.workplane = obj # maybe try to target the globals() of the qtconsole
            self.cmd.type = "new_part"

        elif isinstance(obj, Workplane) and self.cmd.var in self.ns_before_cmd.keys():
            self.cmd.type = "part_edit"            
            self.cmd.workplane = obj

            
        self.generic_visit(node)



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
    a = Workplane()
    cmd = "a = Workplane().box(1,1,1).sphere(2)"


    analyzer = CommandAnalyzer(globals())
    tree = ast.parse(cmd, mode="exec")

    analyzer.visit(tree)

    print(analyzer.cmd.type)
    cmd = analyzer.get_command()
    print(cmd.operations)
    
    