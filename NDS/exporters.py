from pickletools import pyfloat
from typing import Dict, List

from NDS.model import NModel


class PythonFileWriter:
    def __init__(self, model: NModel) -> None:
        self.model = model
        self.parts_data = []
        self.shapes_data = []
        self.others_data = []

        self._prepare_data()

    def _get_arg_data(self, narg):

        arg_data = {}

        arg_data["name"] = narg.name
        arg_data["linked"] = narg.is_linked
        arg_data["value"] = narg.value

        return arg_data

    def _get_operation_data(self, nop):

        op_data = {"name": None, "args": [], "linked": False}

        for arg in nop.childs:
            arg_data = self._get_arg_data(arg)
            op_data["args"].append(arg_data)

            if arg_data["linked"]:
                op_data["linked"] = True

        op_data["name"] = nop.name

        return op_data

    def _get_part_data(self, npart):

        part_data = {"name": None, "operations": [], "linked": False}

        for operation in npart.childs:
            op_data = self._get_operation_data(operation)
            part_data["operations"].append(op_data)

            if op_data["linked"]:
                part_data["linked"] = True

        part_data["name"] = npart.name

        return part_data

    def _prepare_parts_data(self):
        nparts = self.model.parts

        for npart in nparts:
            self.parts_data.append(self._get_part_data(npart))

    def _prepare_shapes_data(self):
        pass

    def _prepare_others_data(self):
        pass

    def _prepare_data(self):
        self._prepare_parts_data()
        self._prepare_shapes_data()
        self._prepare_others_data()

    def _arg_data_to_str(self, arg_data: Dict):
        return f'{arg_data["name"]} = {arg_data["value"]}'

    def _op_data_to_str(self, op_data: Dict):

        op_str = f"{op_data['name']}("
        for arg in op_data["args"]:
            op_str += self._arg_data_to_str(arg)
            if arg is not op_data["args"][-1]:
                op_str += ","

        op_str += ")"
        return op_str

    def _part_data_to_str(self, part_data):

        part_str = f'{part_data["name"]} = cq.Workplane()\n'

        for op in part_data["operations"]:
            part_str += f'{part_data["name"]} = {part_data["name"]}.{self._op_data_to_str(op)}\n'

        return part_str

    def write_file(self, path):
        with open(path, "w") as py_file:

            py_file.write("# This file has been generated automatically by Nales\n")
            py_file.write(
                "# Don't modify this file unless you know what you are doing\n"
            )
            py_file.write("import cadquery as cq\n")

            for part in self.parts_data:
                py_file.write(self._part_data_to_str(part))
                py_file.write("\n")

