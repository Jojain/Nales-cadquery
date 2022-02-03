from typing import List

from nales_alpha.NDS.model import NalesParam

"""
Partdef
Part1
box,circle,cutThruAll
No
"""
Part1 = cq.Workplane()
Part1 = Part1.box(length=10, width=5, height=5, centered=True, combine=True, clean=True)
Part1 = Part1.circle(radius=1, forConstruction=False)
Part1 = Part1.cutThruAll(clean=True, taper=0)


class PythonFileReader:
    def __init__(self, file_path: str) -> None:
        with open(file_path, "r") as py_file:
            self.lines = py_file.readlines()
        self.params: List[NalesParam] = []

    def _check_file_validity(self):
        if self.lines[0] != "# This file has been generated automatically by Nales":
            return False
        else:
            return True

    def _find_parts_idx(self) -> List[int]:
        """
        Returns the position of the parts definitions
        """
        parts_idx = []
        for idx, line in enumerate(self.lines):
            if line.startswith("#Partdef>>"):
                parts_idx.append(idx)

        return parts_idx

    def _parse_parts(self):

        parts_idx = self._find_parts_idx()

        for part_idx in parts_idx:
            part_data = self.lines[part_idx + 1 : part_idx + 3]
            part_def = {}
            part_def["name"] = part_data[0].strip()
            part_def["operations"] = part_data[1].strip().split(",")
            part_def["link"] = part_data[2].strip()

        self.parts

    def _parse_params(self):
        """
        Populate `self.params` attribute with data read in the input file
        """
        for idx, line in enumerate(self.lines):
            if line.startswith("#Paramsdef>>"):
                nb_of_params = int(line.split()[1])
                params_lines = self.lines[idx + 1 : idx + nb_of_params]
                break

        for param_line in params_lines:
            data = param_line.split(
                "#"
            )  # param_line is something like : variable = 5 # int
            name = data[0].split("=")[0].strip()
            value = data[0].split("=")[1].strip()
            type_ = data[1].strip()
            param = NalesParam(name, value, type_)
            self.params.append(param)

    def _parse(self):

        self._parse_params()
        self._parse_parts()

    def _get_parts_cmds(self):
        pass
