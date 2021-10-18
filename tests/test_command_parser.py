#%%
import ast
from unittest import TestCase
from nales_alpha.NDS.commands import CQAssignAnalyzer
import pytest
import cadquery as cq
from collections import OrderedDict


def get_analyzer_cmds(namespace, code):
    ns_before = namespace.copy()
    exec(code, namespace)
    an = CQAssignAnalyzer(namespace, ns_before)
    an.visit(ast.parse(code))
    return an.get_commands()


class TestCommandParser(TestCase):
    def test_Workplane_creation_cmd(self):
        code = "part = cq.Workplane()"
        ns = {"cq": cq}

        cmds = get_analyzer_cmds(ns, code)

        self.assertTrue(cmds[0].type == "new_part")
        self.assertTrue(len(cmds) == 1)

        ops = cmds[0].operations

        self.assertDictEqual(
            ops,
            {"Workplane": ([], {"inPlane": "XY", "origin": (0, 0, 0), "obj": None})},
        )

    def test_chain_call_Wp_creation(self):
        code = "part = cq.Workplane().sphere(1).box(1,1,1)"
        ns = {"cq": cq}

        cmds = get_analyzer_cmds(ns, code)
        ops = cmds[0].operations
        
        dict_ops = {
            "Workplane": ([], {"inPlane": "XY", "origin": (0, 0, 0), "obj": None}),
            "sphere": (
                [1],
                {
                    "direct": (0, 0, 1),
                    "angle1": -90,
                    "angle2": 90,
                    "angle3": 360,
                    "centered": True,
                    "combine": True,
                    "clean": True,
                },
            ),
            "box": ([1, 1, 1], {"centered": True, "combine": True, "clean": True}),
        }
        self.assertTrue(cmds[0].type == "new_part")
        self.assertDictEqual(ops, dict_ops)

    def test_part_edit_cmd(self):
        code = "part = part.sphere(1).box(1,1,1)"
        ns = {"cq": cq, "part":cq.Workplane()}

        cmds = get_analyzer_cmds(ns, code)        
        self.assertTrue(cmds[0].type == "part_edit")

    def test_part_override_cmd(self):
        code = "part = cq.Workplane().sphere(1).box(1,1,1)"
        ns = {"cq": cq, "part":cq.Workplane()}
        cmds = get_analyzer_cmds(ns, code)        
        self.assertTrue(cmds[0].type == "part_override")

    def test_subcommands(self):
        code = "part = cq.Workplane().sphere(1).union(cq.Workplane().box(1,1,1))"
        ns = {"cq": cq}     
        cmds = get_analyzer_cmds(ns, code)  

        self.assertTrue(len(cmds) == 2)
        self.assertTrue(cmds[0].type == "new_part")  
        self.assertTrue(cmds[1].type == "unbound")  


    def test_new_shape(self):
        pass 

    def test_shape_override(self):
        pass

if __name__ == "__main__":
    from pprint import pprint
    # import
    cmd = "part = cq.Workplane().sphere(1).union(cq.Workplane().box(1,1,1))"

    ns = {"cq": cq}
    ns_before = ns.copy()
    exec(cmd, ns)
    an = CQAssignAnalyzer(ns, ns_before)
    an.visit(ast.parse(cmd))
    c = an.get_commands()
    op = c[0].operations
    pprint(op,width=1)
    op = c[1].operations
    pprint(op,width=1)


# %%
