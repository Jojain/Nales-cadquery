#%%
import graphviz 
import astpretty
import ast
from graphviz.dot import Digraph


# %%
class Grapher(ast.NodeVisitor):

    def __init__(self):
        self.graph = graphviz.Digraph()
        self.parent = None

    def visit(self, node):
        n = str(type(node))
        self.graph.node(n)
        if self.parent:
            self.graph.edge(self.parent, n)
        self.parent = n

        return super().visit(node)
grapher = Grapher()


#%%
def make_graph(ast_tree):
    astpretty.pprint(ast_tree, show_offsets=False)

    graph = graphviz.Digraph()
    parent_node = None
    for item in ast.walk(ast_tree):
        
        graph.node(str(item))
        if parent_node:
            graph.edge(parent_node, str(item))
        parent_node = str(item)
    return graph

# %%
import cadquery as cq
code = "test = cq.Workplane().box(1,5,2)"

grapher.visit(ast.parse(code))
# g = grapher.graph
# g.render("temp_test/g.gv", view=True)

#%%
from astmonkey import visitors, transformers

visitor = visitors.GraphNodeVisitor()


node = transformers.ParentChildNodeTransformer().visit(ast.parse(code))
visitor.visit(node)

raw_dot = visitor.graph.to_string()

# digraph = Digraph()
graph = graphviz.Source(raw_dot)
# %%
