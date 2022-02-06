# This script makes a correction to the import path of the ressource_py since pyuic does it automatically
# and wrongly

import sys

file_to_modify = sys.argv[1]

with open(file_to_modify, "r") as inp:
    inp_lines = inp.readlines()

new_lines = []
for line in inp_lines:
    if "import resources_rc" in line:
        new_lines.append("from nales.resources import resources_rc")
    else:
        new_lines.append(line)

with open(file_to_modify, "w") as out:
    out.writelines(new_lines)
