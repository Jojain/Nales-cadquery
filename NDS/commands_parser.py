#%%
import ast
from nales_alpha.NDS.ast_grapher import make_graph
from ast import Assign, Name, Store, Constant
# from ast import unparse
# %%
class Transformer(ast.NodeTransformer):
    
    def visit_Assign(self, node):

        
        self.generic_visit(node)
        new_node = Assign([Name("toto", Store())], Constant(0,None))

        # Assign([Name(tempvar, Store())], <inner_call>),

        #     Expr(Call(
        #         <outer_function_name_expr>,
        #         args=[Name(tempvar, Load())],
        #         keyword=[]))
        return new_node

# %%
