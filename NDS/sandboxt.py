#%%
import graphviz 
import astpretty
import ast
from graphviz.dot import Digraph
from astmonkey import visitors, transformers
import cadquery as cq

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



def make_graph(code):

    grapher.visit(ast.parse(code))

    visitor = visitors.GraphNodeVisitor()
    node = transformers.ParentChildNodeTransformer().visit(ast.parse(code))
    visitor.visit(node)

    raw_dot = visitor.graph.to_string()

    # digraph = Digraph()
    graph = graphviz.Source(raw_dot)
    
    return graph



code = "test = cq.Workplane().box(1,5,2)"





# %%
