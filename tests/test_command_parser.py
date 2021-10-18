#%%
import ast
from unittest import TestCase
from nales_alpha.NDS.commands import CQAssignAnalyzer
import pytest
import cadquery as cq

def get_analyzer_cmds(namespace, code):
    ns_before = namespace.copy()
    exec(code,namespace)    
    an = CQAssignAnalyzer(namespace, ns_before)
    an.visit(ast.parse(code))
    return an.get_commands()


class TestCommandParser(TestCase):
    
    def test_Workplane_creation_cmd(self):
        code = "part = cq.Workplane()"
        ns = {"cq": cq}

        cmds = get_analyzer_cmds(ns, code)

        self.assertTrue(len(cmds) == 1)

        ops = cmds[0].operations
        self.assertTrue("Workplane" in ops.keys())

        keys = ('inPlane', 'origin', 'obj')
        values = ('XY',(0, 0, 0), None)
        for key,val in zip(keys,values):
            self.assertTrue(key in ops["Workplane"][1].keys())
            self.assertTrue(val in ops["Workplane"][1].values())
        

if __name__ == "__main__":
    cmd = "part = cq.Workplane()"

    ns = {"cq": cq}
    ns_before = ns.copy()
    exec(cmd,ns)    
    an = CQAssignAnalyzer(ns, ns_before)    
    an.visit(ast.parse(cmd))
    c = an.get_commands()
    op = c[0].operations
    print(op)
    print(type(op["Workplane"][1]["inPlane"]))


# %%
