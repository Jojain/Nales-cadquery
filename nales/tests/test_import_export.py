# This file test importers and exporters
import os
from pathlib import Path
from typing import List, Tuple
from ezdxf import is_dxf_file
from nales.main_window import MainWindow

TESTS_FILES_FOLDER = __file__.strip(__name__ + ".py") + "tests_files"


def _get_file_content(path: str) -> List[str]:
    with open(path, "r") as f:
        content = f.readlines()
    return content


def _read_params(file_data: List[str]) -> Tuple:
    names = []
    values = []
    types = []

    for idx, line in enumerate(file_data):
        if line.startswith("#Paramsdef>>"):
            start_idx = idx
            nb_of_params = int(line.split()[1])
            break
    params_lines = file_data[idx + 1 : idx + nb_of_params + 1]
    for line in params_lines:
        data = line.split("#")
        paramdef = data[0].split("=")
        names.append(paramdef[0].strip())
        values.append(paramdef[1].strip())
        types.append(data[1].strip())

    return tuple(names), tuple(values), tuple(types)


def test_export_param(qtbot):
    test_export_file = os.path.join(TESTS_FILES_FOLDER, "test_export_param.py")
    mw = MainWindow()
    mw.hide()
    qtbot.addWidget(mw)
    mw.param_model.add_parameter("p1", 15)
    mw.param_model.add_parameter("p2", "bonjour")
    mw.param_model.add_parameter("p3", None)
    mw._console.execute_command(f"nales.save(r'{test_export_file}')")

    assert os.path.isfile(test_export_file)

    content = _get_file_content(test_export_file)

    names, values, types = _read_params(content)

    assert names == ("p1", "p2", "p3")
    assert values == ("15", '"bonjour"', "None")
    assert types == ("int", "str", "None")


def test_import_param(qtbot):
    # Load the file created by the export test
    test_import_file = os.path.join(TESTS_FILES_FOLDER, "test_export_param.py")
    mw = MainWindow()
    mw.hide()
    qtbot.addWidget(mw)

    # Read the file and update the GUI
    mw._console.execute_command(f"nales.load(r'{test_import_file}')")
    params = mw.param_model.parameters
    assert len(params) == 3
    assert (params[0].name, params[0].value, params[0].type) == ("p1", 15, "int")
    assert (params[1].name, params[1].value, params[1].type) == (
        "p2",
        '"bonjour"',
        "str",
    )
    assert (params[2].name, params[2].value, params[2].type) == ("p3", None, None)


def test_export_parts(qtbot):
    test_import_file = os.path.join(TESTS_FILES_FOLDER, "test_import_parts.py")
    mw = MainWindow()
    mw.hide()
    qtbot.addWidget(mw)
    mw._console.execute_command(
        "p = Part(name='test_part').box(10,10,10).faces('>Z').workplane().hole(1.5)"
    )
    mw._console.execute_command(f"nales.save(r'{test_import_file}')")

    # Open the test file and store the part definition lines in a list
    with open(test_import_file, "r") as test_file:
        lines = test_file.readlines()
        part_def_lines = []
        for i, line in enumerate(lines):
            if line.startswith("#Partdef>>"):
                def_line_nb = int(line.split()[2])
                for l in lines[i + 1 : i + def_line_nb + 1]:
                    part_def_lines.append(l.strip())
                break

        # In the futur it would be better to test that we have the ast node correct, so we don't care about formatting
        assert part_def_lines[0] == "test_part = cq.Workplane()"
        assert (
            part_def_lines[1]
            == "test_part = test_part.box(length = 10, width = 10, height = 10, centered = True, combine = True, clean = True)"
        )
        assert (
            part_def_lines[2]
            == 'test_part = test_part.faces(selector = ">Z", tag = None)'
        )
        assert (
            part_def_lines[3]
            == 'test_part = test_part.workplane(offset = 0.0, invert = False, centerOption = "ProjectedOrigin", origin = None)'
        )
        assert (
            part_def_lines[4]
            == "test_part = test_part.hole(diameter = 1.5, depth = None, clean = True)"
        )


def test_import_parts(qtbot):
    test_import_file = os.path.join(TESTS_FILES_FOLDER, "test_import_parts.py")
    mw = MainWindow()
    mw.hide()
    qtbot.addWidget(mw)
    mw._console.execute_command(f"nales.load(r'{test_import_file}')")
    assert len(mw.model.parts) == 1
    p = mw.model.parts[0]
    assert (
        len(p.childs) == 4
    )  # check that all operations have been loaded, atm doesn't consider __init__ operation

    assert (
        len(p.childs[0].childs) == 6
    )  # check that we have all args of the method `box` in this case
