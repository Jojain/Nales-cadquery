# Tests of Nales Models classes

import pytest

from nales.nales_cq_impl import CQMethodCall, Part
from nales.NDS.interfaces import NArgument, NNode, NPart
from nales.NDS.model import NModel
from nales.NDS.NOCAF import OCAFApplication

############################################################
###############         NMODEL TESTING       ###############
############################################################

# Hack to use Part in test without creating a NalesApp instance
# fmt: off
class hack:
    def handle_command(none): pass
Part._mw_instance = hack
# fmt: on


class DataFixture:
    def __init__(self) -> None:
        self.app = OCAFApplication()
        self.model = NModel(self.app.root_label)


@pytest.fixture
def data() -> DataFixture:
    return DataFixture()


def test_nmodel_add_part(data):
    root_tree = data.model._root
    created_node = data.model.add_part("test_part")

    assert (node := root_tree.find("test_part")) is not None
    assert node is created_node

    parts_node = root_tree.find("Parts")
    assert node in parts_node.childs


def test_nmodel_add_operation(data):
    data.model.add_part("test_part")  # already tested above

    # Preparing data
    method = Part.box
    args = (10, 5, 3)
    obj = Part(name="test", internal_call=True).box(*args)
    call = CQMethodCall(method, args)

    created_node = data.model.add_operation("test_part", obj, call)

    root_tree = data.model._root

    assert (node := root_tree.find("box")) is not None
    assert created_node is node

    assert all(isinstance(n, NArgument) for n in node.childs)


def test_nmodel_add_shape(data):
    pass


def test_nmodel_get_part_index(data):
    pass


def test_nmodel_get_shape_index(data):
    pass


def test_nmodel_update_model(data):
    pass


def test_nmodel_update_objs_linked_to_obj(data):
    pass


def test_nmodel_update_shape(data):
    pass


def test_nmodel_update_operation(data):
    pass


def test_nmodel_index_from_node(data):
    pass


def test_nmodel_link_object(data):
    pass


def test_nmodel_unlink_object(data):
    pass


def test_nmodel_link_parameters(data):
    pass


def test_nmodel_unlink_parameters(data):
    pass


def test_nmodel_remove_operation(data):
    pass


def test_nmodel_remove_part(data):
    pass


def test_nmodel_remove_shape(data):
    pass


def test_nmodel_parts(data):
    pass


def test_nmodel_objects(data):
    pass


def test_nmodel_console(data):
    pass


def test_nmodel_removeRows(data):
    pass


def test_nmodel_data(data):
    pass


def test_nmodel_flags(data):
    pass


def test_nmodel_setData(data):
    pass


def test_nmodel_insertRows(data):
    pass


def test_nmodel_childrens(data):
    pass


def test_nmodel_rowCount(data):
    pass


def test_nmodel_columnCount(data):
    pass


def test_nmodel_index(data):
    pass


def test_nmodel_parent(data):
    pass

