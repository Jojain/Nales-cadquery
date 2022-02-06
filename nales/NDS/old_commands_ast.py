#%%
from typing import Any, List, Tuple, Union
from PyQt5.QtCore import QObject
import ast

# import astpretty
from ast import (
    Expr,
    keyword,
    Assign,
    Name,
    Call,
    Store,
    Attribute,
    Load,
    Constant,
    Expression,
    Module,
    Del,
    iter_child_nodes,
    walk,
)
import ncadquery.cqgi
from ncadquery import Workplane
from ncadquery.occ_impl.shapes import Shape
import ncadquery as cq
from collections import OrderedDict

# from graphviz.backend import command
from nales.utils import (
    get_cq_class_kwargs_name,
    get_cq_topo_classes,
    get_cq_types,
    get_Wp_method_kwargs,
    get_topo_class_kwargs_name,
)

# from nales.NDS.ast_grapher import make_graph

# from collections import OrderedDict
from nales.utils import (
    get_cq_class_kwargs_name,
    get_cq_topo_classes,
    get_cq_types,
    get_Wp_method_kwargs,
    get_topo_class_kwargs_name,
)


def prepare_parent_childs(tree):
    """
    Adds parent and chils attributes to ast nodes
    """
    for node in ast.walk(tree):
        node.childs = []
        for child_node in ast.iter_child_nodes(node):
            node.childs.append(child_node)
            child_node.parent = node


class CQAssignAnalyzer(ast.NodeVisitor):
    def __init__(self, ns, ns_before_cmd) -> None:
        super().__init__()
        self._console_ns = ns
        self._console_ns_before_cmd = ns_before_cmd
        self._cq_assign_type = None
        self._assigned_node = None
        self._root_call_node = None
        self._cmds = []
        self._prepared = False

    def _get_root_node_from_Call(self, node: Call) -> Name:
        """
        Gets the root of a chain call
        for example 'p = a.b.c.d()' would isolate the Name node linked to 'a'
        """
        call_root = None

        for sub_node in walk(node.func):
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
            obj_type = self._console_ns[var_name]
        except KeyError:
            return False
        if isinstance(obj_type, Workplane):
            return True

    def _is_Shape(self, var_name) -> bool:
        try:
            obj_type = self._console_ns[var_name]
        except KeyError:
            return False
        if isinstance(obj_type, Shape):
            return True

    def _var_existed(self, var_name) -> bool:
        """
        Returns if the var_name existed in the namespace before the command or not
        """
        try:
            self._console_ns_before_cmd[var_name]
        except KeyError:
            return False
        return True

    def _is_cq_obj(self, var_name: str) -> bool:
        cq_types = get_cq_types()
        try:
            obj = self._console_ns[var_name]
        except KeyError:
            return False
        if type(obj) in cq_types:
            return True

    def _cq_call_type(self, node: Call) -> str:
        """
        Returns the ncadquery call type, valid types are :
        - Shape
        - Workplane
        - Other
        """

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

    def _is_cq_call(self, node: Call) -> bool:
        """
        Returns if a Call node is a ncadquery call (i.e it calls a ncadquery fonction / method)
        """

        call_root = self._get_root_node_from_Call(node)

        if call_root.id == "cq" or self._is_cq_obj(call_root.id):
            return True
        else:
            return False

    def _get_assign_type(self, assign_node, root_node):

        if assign_node is None:
            return "unbound"

        if self._is_cq_obj(assign_node.id) and not self._is_Workplane(root_node.id):
            if self._var_existed(assign_node.id):
                return "part_override"
            elif root_node.parent.attr == "Workplane":
                return "new_part"
            else:
                return "shape_override"

        if assign_node.id == root_node.id:
            return "part_edit"
        elif root_node.parent.attr == get_cq_topo_classes():
            return "new_shape"
        elif root_node.parent.attr == "Workplane":
            return "new_part"
        else:
            return "other"

    def _is_cq_assign(self, node: Assign) -> bool:
        """
        Returns if an assignement value is made from a cq object or from cq class

       
        """
        self._assigned_node = node.value

        if isinstance(node.value, Call):
            call_root = self._get_root_node_from_Call(node.value)
        elif isinstance(node.value, Name):
            call_root = node.value
        else:
            return False

        if call_root.id == "cq" or self._is_cq_obj(call_root.id):
            return True
        else:
            return False

    def _is_from_main_call_stack(self, node: Any) -> None:
        """
        Returns if the `node` considered is from the main call stack of the assignment or expression
        Example :
        a = b.c.d(u.v.p())
        - Will return True if the node considered is the node linked to "c" 
        - Will return False if the node considered is the node linked to "v"
        """

        looked_node = self._root_call_node
        while True:
            if looked_node is node:
                return True
            try:
                looked_node = looked_node.parent
            except AttributeError:
                break
        if looked_node is self._assigned_node:
            return False

    def get_commands(self) -> "Command":
        cmds = self._cmds
        for cmd in cmds:
            if cmd.type != "undefined":
                try:
                    cmd.obj = self._console_ns[cmd.var]
                except KeyError:
                    if cmd.type != "unbound":
                        cmd.type = "undefined"
            if cmd.operations:
                cmd.operations = dict(reversed(list(cmd.operations.items())))
            else:
                cmd.operations = dict()

        return cmds

    def _get_operations(self, node: Call) -> dict:

        assert isinstance(node, Call)
        call_type = self._cq_call_type(node)

        if call_type == "Workplane":
            return self._get_call_stack(node)
        else:
            return self._get_call(node)

    def visit_Call(self, node: Call) -> Any:
        if not self._is_from_main_call_stack(node):

            if self._is_cq_call(node):
                cmd = Command(subcommand=True)
                cmd.operations = self._get_operations(node)
                call_type = self._cq_call_type(node)

                if call_type == "Workplane":
                    cmd.type = "new_part"

                elif call_type == "Shape":
                    cmd.type = "new_shape"
                    cmd.topo_type = node.parent.attr
                else:
                    cmd.type = "other"

                cmd.operations = self._get_operations(node)

                self._cmds.append(cmd)

        self.generic_visit(node)

    def visit_Assign(self, node):

        if self._is_cq_assign(node):
            # assign is something like :
            # part = cq.Workplane().box(1,1,1)
            # part = cq.Edge.makeEdge(v1,v2)
            # part = aCqObj.sphere(5)
            # vector = cq.Vector(0,0,1)

            main_cmd = Command()
            self._cmds.append(main_cmd)
            main_cmd.var = node.targets[0].id

            if isinstance(node.value, Call):
                self._root_call_node = root_node = self._get_root_node_from_Call(
                    node.value
                )

            main_cmd.type = self._get_assign_type(node.targets[0], root_node)

            main_cmd.operations = self._get_operations(node.value)

            self.generic_visit(node)

        else:
            # The command is not cq related so we stop the parsing
            return

    def visit(self, node):
        if not self._prepared:
            prepare_parent_childs(node)
            self._prepared = True
        super().visit(node)

    def _get_call(self, node: Call) -> dict:
        """
        Retrieve the call of a cq function, and return it as an dict associating the function to its params
        """
        root = self._get_root_node_from_Call(node)

        call = dict()

        if (class_name := root.parent.attr) in get_cq_topo_classes():
            method_name = root.parent.parent.attr
            kwargs = get_topo_class_kwargs_name(class_name, method_name)
        else:
            method_name = root.parent.attr
            kwargs = get_cq_class_kwargs_name(class_name)

        for invoked_kw in node.keywords:
            kwargs[
                invoked_kw.arg
            ] = (
                invoked_kw.arg.value.value
            )  # override defaults kwargs by the ones passed

        args = [
            arg.value
            if hasattr(arg, "value")
            else (arg.func.attr if hasattr(arg, "func") else arg.id)
            for arg in node.args
        ]
        call[method_name] = (args, kwargs)

        return call

    def _get_args_values(self, node: Call) -> list:
        """
        Returns args value, handling different types of values
        """
        args_node = node.args
        values = []
        for arg_node in args_node:
            if isinstance(arg_node, Constant):
                values.append(arg_node.value)

            elif isinstance(arg_node, (ast.Tuple, ast.List)):

                for item in arg_node.elts:
                    if isinstance(item, Constant):
                        values.append(item.value)
                    elif isinstance(item, Name):
                        values.append(item.id)

                # values = ",".join([str(val) for val in values])

        return values

    def _get_kwargs_values(self, node: keyword) -> Any:
        """
        Returns kwargs value, handling different types of values
        """
        value_node = node.value
        if isinstance(value_node, Constant):
            value = value_node.value

        elif isinstance(value_node, (ast.Tuple, ast.List)):
            values = []
            for item in value_node.elts:
                if isinstance(item, Constant):
                    values.append(item.value)
                elif isinstance(item, Name):
                    values.append(item.id)

            value = ",".join([str(val) for val in values])

        return value

    def _get_call_stack(self, node: Call) -> dict:
        """
        Retrieve the call stack of a Workplane, and return it as an Ordered dict associating method to parameters
        """

        call_stack = dict()
        for sub_node in ast.walk(node):
            if isinstance(sub_node, Call):
                method_name = sub_node.func.attr
                kwargs = get_Wp_method_kwargs(method_name)
                for invoked_kw in sub_node.keywords:
                    kwargs[invoked_kw.arg] = self._get_kwargs_values(
                        invoked_kw
                    )  # override defaults kwargs by the ones passed

                # call_stack[method_name] = ([arg.value if hasattr(arg, "value") else arg.id for arg in sub_node.args ], kwargs)

                args = self._get_args_values(sub_node)
                call_stack[method_name] = (args, kwargs)

        return call_stack


class Command:
    """
    This class is used to interface the GUI, the backend and the frontend
    Command object store information about how the application should be changed/updated

    It's designed to receive chode chunks and return information about what this code should do to the application
    It review code_chunks with ast nodes

    Command types are given below :
     - new_part
     - part_edit
     - part_override
    #  - new_shape
    """

    def __init__(self, var: str, operations: List[dict], obj: Any, new_var: bool):
        self.var = var
        self.operations = operations
        self.obj = obj
        self.new_var = new_var

        self.type = self._get_cmd_type()
        self.topo_type = None

    def _get_cmd_type(self):
        if list(self.operations[0].keys())[0] == "Workplane" and not self.new_var:
            return "part_override"
        elif list(self.operations[0].keys())[0] == "Workplane" and self.new_var:
            return "new_part"
        elif list(self.operations[0].keys())[0] != "Workplane" and not self.new_var:
            return "part_edit"
        else:
            return "unbound"


if __name__ == "__main__":
    import astpretty
    import ncadquery as cq
    from ncadquery import cq
    from astmonkey import visitors, transformers

    debug = True
    cmd = "a = b.box(1,1,1).sphere(2)\nu = b"
    c = cq.Workplane().box(1, 1, 1).sphere(2)
    ns = {"cq": ncadquery, "b": c}
    ns2 = {"a": 5, "cq": ncadquery, "b": c}
    cmd_analyzer = CQAssignAnalyzer(
        ns2, ns
    )  # call this line in the ipython window to view the graph

    ast_tree = ast.parse(cmd)
    from astmonkey import transformers, visitors
    import graphviz

    visitor = visitors.GraphNodeVisitor()
    node = ParentChildNodeTransformer().visit(ast_tree)
    visitor.visit(node)
    raw_dot = visitor.graph.to_string()
    graph = graphviz.Source(raw_dot)
    cmd_analyzer.visit(node)
    cmd = cmd_analyzer.get_commands()
    print(cmd_analyzer.call_stack.items())


# %%
