#%%

# THIS IS FOR DEBUG ONLY, make_graph() creates a pydot graph that can be displayed in the qtconsole
# printing the AST tree as svg
import graphviz 
from astmonkey import visitors, transformers
import ast



#%%
def make_graph(code:str):
    ast_tree = ast.parse(code)
    visitor = visitors.GraphNodeVisitor()

    node = transformers.ParentChildNodeTransformer().visit(ast_tree)
    visitor.visit(node)
    raw_dot = visitor.graph.to_string()

    graph = graphviz.Source(raw_dot)
    return graph

# %%
