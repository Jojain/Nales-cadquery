import ast
from os import link
from typing import List, Tuple

from nales.nales_cq_impl import Part
from nales.NDS.model import NalesParam


class PythonFileReader:
    def __init__(self, file_path: str) -> None:
        with open(file_path, "r") as py_file:
            self.lines = py_file.readlines()
        self.params: List[NalesParam] = []
        self.parts: List[dict] = []  # dict is : name, operations{name:args}, is_linked

        self._parse()

    def _check_file_validity(self):
        if self.lines[0] != "# This file has been generated automatically by Nales":
            return False
        else:
            return True

    def _find_parts_idxes(self) -> List[int]:
        """
        Returns the position of the parts definitions
        """
        partsdef_idxes = []
        for idx, line in enumerate(self.lines):
            if line.startswith("#Partdef>>"):
                partsdef_idxes.append(idx)
        return partsdef_idxes

    def _build_parts(self):

        non_linked_parts = [part for part in self.parts if not part["is_linked"]]
        linked_parts = [part for part in self.parts if part["is_linked"]]

        self.objects = {}

        for part in non_linked_parts:

            for op in part["operations"]:
                args = part["operations"][op]
                if op == "Workplane":
                    obj = Part(*args, name=part["name"], internal_call=True)
                else:
                    obj = eval(f"obj.{op}(*{args}, internal_call=True)")

                self.objects[op] = obj

        self.parts = non_linked_parts + linked_parts

    def _get_operation_data(self, line: str) -> Tuple[str, str]:
        """
        Gets data operation data from a line in the python file
        """

        def handle_node(node, args, linked_args):
            if isinstance(node, ast.Name):
                value = node.id
                args.append(value)
                linked_args.append(value)
            elif isinstance(node, ast.Constant):
                args.append(node.value)
            elif isinstance(node, ast.keyword):
                return handle_node(node.value, args, linked_args)
            elif isinstance(node, ast.Tuple):
                elts = []
                for node_elem in node.elts:
                    handle_node(node_elem, elts, [])
                args.append(tuple(elts))

            else:
                raise ValueError(f"Node type {type(node)} not handled")

        ast_node = ast.parse(line)
        call_node = ast_node.body[0].value
        name = call_node.func.attr
        args = []
        linked_args = []
        for arg in call_node.args:
            handle_node(arg, args, linked_args)
        for kw in call_node.keywords:
            handle_node(kw, args, linked_args)

        return name, args + linked_args

    def _parse_partdef(self, partdef_idx: int):
        def remove_prefix(prefix, s):
            return s[len(prefix) :] if s.startswith(prefix) else s

        part_name, nb_of_ops, is_linked = remove_prefix(
            "#Partdef>> ", self.lines[partdef_idx]
        ).split()

        if is_linked == "True":
            is_linked = True
        else:
            is_linked = False

        part_def = {"name": part_name, "operations": {}, "is_linked": is_linked}

        for line in self.lines[partdef_idx + 1 : partdef_idx + int(nb_of_ops) + 1]:
            op_name, op_args = self._get_operation_data(line)
            part_def["operations"][op_name] = op_args

        return part_def

    def _parse_parts(self):
        partdef_idxes = self._find_parts_idxes()

        for partdef_idx in partdef_idxes:
            self.parts.append(self._parse_partdef(partdef_idx))

        self._build_parts()

    def _parse_params(self):
        """
        Populate `self.params` attribute with data read in the input file
        """
        for idx, line in enumerate(self.lines):
            if line.startswith("#Paramsdef>>"):
                nb_of_params = int(line.split()[1]) + 1
                params_lines = self.lines[idx + 1 : idx + nb_of_params]
                break

        for param_line in params_lines:
            data = param_line.split(
                "#"
            )  # param_line is something like : variable = 5 # int
            name = data[0].split("=")[0].strip()
            type_ = data[1].strip()
            value = NalesParam.cast(type_, data[0].split("=")[1].strip())

            param = NalesParam(name, value,)
            self.params.append(param)

    def _parse(self):

        self._parse_params()
        self._parse_parts()
