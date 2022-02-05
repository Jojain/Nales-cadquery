# This file test importers and exporters
from typing import List
from nales_alpha.main_window import MainWindow


def _get_file_content(path: str) -> List[str]:
    with open(path, "r") as f:
        content = f.readlines()
    return content


def test_export_param(qtbot):
    test_export_file = r"D:\Projets\Nales\nales_alpha\nales_alpha\tests\tests_files\test_export_param.py"
    mw = MainWindow()
    mw.hide()
    qtbot.addWidget(mw)
    mw.param_model.add_parameter("test_param", 15)
    mw._console.execute_command(f"nales.save({test_export_file})")

    content = _get_file_content(test_export_file)

    for idx, line in enumerate(content):
        if line.startswith("#Paramdef>>"):
            start = idx
            break
    data = content[start + 1].split()
    assert data[0] == "test_param"
    assert data[1] == "15"
    assert data[2] == "int"
