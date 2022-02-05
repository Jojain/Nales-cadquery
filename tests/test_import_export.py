# This file test importers and exporters
import os
from pathlib import Path
from typing import List, Tuple
from nales_alpha.main_window import MainWindow

TESTS_FILES_FOLDER = __file__.strip(__name__ + ".py") + "tests_files"


def _get_file_content(path: str) -> List[str]:
    with open(path, "r") as f:
        content = f.readlines()
    return content


def _read_param(line: str) -> Tuple:
    data = line.split("#")
    paramdef = data[0].split("=")
    name = paramdef[0].strip()
    value = paramdef[1].strip()
    type_ = data[1].strip()

    return name, value, type_


def test_export_param(qtbot):
    test_export_file = os.path.join(TESTS_FILES_FOLDER, "test_export_param.py")
    mw = MainWindow()
    mw.hide()
    qtbot.addWidget(mw)
    mw.param_model.add_parameter("test_param", 15)
    mw._console.execute_command(f"nales.save(r'{test_export_file}')")

    assert os.path.isfile(test_export_file)

    content = _get_file_content(test_export_file)

    for idx, line in enumerate(content):
        if line.startswith("#Paramsdef>>"):
            start = idx
            break

    data = _read_param(content[start + 1])  # there is only one param to check

    assert data[0] == "test_param"
    assert data[1] == "15"
    assert data[2] == "int"
