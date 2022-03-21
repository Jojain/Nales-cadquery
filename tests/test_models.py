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

    def add_dummy_part(self):
        """
        Sets the NModel data as if the user had type:
        Part().box(10,10,10) 
        in the console.
        It is used by tests that needs data to be feeded into the model to be relevant
        """
        name1 = "test1"
        self.model.add_part(name1)
        # Preparing data
        method1 = Part.__init__
        method2 = Part.box
        args1 = (10, 10, 10)

        call1 = CQMethodCall(method1)
        call2 = CQMethodCall(method2, *args1)

        obj1 = Part(name=name1, internal_call=True)
        self.model.add_operation(name1, obj1, call1)
        obj1 = obj1.box(*args1, internal_call=True)
        self.box_op = self.model.add_operation(name1, obj1, call2)

    def add_dummy_2part(self):
        """
        Sets the NModel data as if the user had type:
        obj = Part(name="test1").box(10,10,10) 
        Part(name="test2").box(20,20,20).cut(obj)
        in the console.
        It is used by tests that needs data to be feeded into the model to be relevant
        """
        name1, name2 = "test1", "test2"
        self.model.add_part(name1)
        self.model.add_part(name2)
        # Preparing data
        method1 = Part.__init__
        method2 = Part.box
        method3 = Part.cut
        args1 = (10, 10, 10)
        args2 = (20, 20, 20)

        call1 = CQMethodCall(method1)
        call2 = CQMethodCall(method2, *args1)

        obj1 = Part(name=name1, internal_call=True)
        self.model.add_operation(name1, obj1, call1)
        obj1 = obj1.box(*args1, internal_call=True)
        self.model.add_operation(name1, obj1, call2)

        call3 = CQMethodCall(method3, obj1)

        obj2 = Part(name=name2, internal_call=True)
        self.model.add_operation(name2, obj2, call1)
        obj2 = obj2.box(*args2, internal_call=True)
        self.model.add_operation(name2, obj2, call2)
        obj2 = obj2.cut(obj1, internal_call=True)
        self.model.add_operation(name2, obj2, call3)


@pytest.fixture
def data() -> DataFixture:
    return DataFixture()


@pytest.fixture
def dummy_model() -> DataFixture:
    d = DataFixture()
    d.add_dummy_2part()
    return d


# d = DataFixture()
# d.add_dummy_part()
# d


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
    kwargs = (True, True, True)  # default kwargs
    obj = Part(name="test", internal_call=True).box(*args)
    call = CQMethodCall(method, *args)

    created_node = data.model.add_operation("test_part", obj, call)

    root_tree = data.model._root

    assert (node := root_tree.find("box")) is not None
    assert created_node is node

    assert all(isinstance(n, NArgument) for n in created_node.childs)

    for child, arg_val in zip(created_node.childs, (args + kwargs)):
        assert child.value == arg_val


def test_nmodel_add_shape(data):
    """
    Shapes adding must behave like part:
    -> add_shape must add the Shape node as well as the first operation which is the classmethod used
    to construct that shape

    Then it must be possible to add subsquent shapes operations like Part since some shapes have this kind of methods
    (like Face with Chamfer for exemple) and if base class evolve then it will be easier to implement the changes
    """
    raise NotImplementedError


def test_nmodel_walk(dummy_model):
    """
    Test the walking of the data tree
    """
    m: NModel = dummy_model.model
    idxs = []
    for idx in m.walk():
        idxs.append(idx)

    assert len(idxs) == 31
    assert idxs[0].internalPointer() is None
    assert idxs[1].internalPointer().name == "Parts"
    assert idxs[2].internalPointer().name == "test1"


def test_nmodel_get_part_index(data):
    """
    Tests that the model return the correct index when asking for a part index
    """
    m: NModel = data.model
    m.add_part("toto")
    m.add_part("bamboo")
    m.add_part("tata")

    parts_idx = m.index(0, 0)
    expected_toto_idx = m.index(0, 0, parts_idx)
    expected_tata_idx = m.index(2, 0, parts_idx)
    toto_idx = m.get_part_index("toto")
    tata_idx = m.get_part_index("tata")

    assert expected_toto_idx.internalPointer() is toto_idx.internalPointer()
    assert expected_tata_idx.internalPointer() is tata_idx.internalPointer()


def test_nmodel_get_shape_index(data):
    """
    Tests that the model return the correct index when asking for a shape index
    """
    m: NModel = data.model
    m.add_shape("toto")
    m.add_shape("bamboo")
    m.add_shape("tata")

    shapes_idx = m.index(1, 0)
    expected_toto_idx = m.index(0, 0, shapes_idx)
    expected_tata_idx = m.index(2, 0, shapes_idx)
    toto_idx = m.get_shape_index("toto")
    tata_idx = m.get_shape_index("tata")

    assert expected_toto_idx.internalPointer() is toto_idx.internalPointer()
    assert expected_tata_idx.internalPointer() is tata_idx.internalPointer()


def test_nmodel_index_from_node(data):
    """
    Tests that the model creates the right index from a specific node
    """
    m: NModel = data.model
    node1 = m.add_part("p1")
    node2 = NNode("dummy")
    assert m.index_from_node(node1).internalPointer() is node1

    with pytest.raises(ValueError):
        m.index_from_node(node2)


def test_nmodel_update_objs_linked_to_obj(data):
    pass


def test_nmodel_update_model(dummy_model):
    """
    Tests that the model return the correct index when asking for a shape index
    """
    m: NModel = dummy_model.model

    # change the model data by hand
    npart = m.parts_nodes[0]
    part1, part2 = tuple(node.part for node in m.parts_nodes)
    arg = npart.childs[1].childs[0]  # return NArgument length
    arg.value = 26  # change the data
    changed_idx = m.index_from_node(arg)

    # We tell the model that something has been changed
    m.dataChanged.emit(changed_idx, changed_idx)

    m.update_model(changed_idx)
    updated_part1, updated_part2 = tuple(node.part for node in m.parts_nodes)

    assert updated_part1._val().Volume() > part1._val().Volume()
    # part2 is a box from which we cut part1, so if part1 size increase
    # part2 volume decrease
    assert updated_part2._val().Volume() < part2._val().Volume()

    ##############################################
    # Test that an error is raise if something that is not a NArgument is modified

    with pytest.raises(ValueError):
        wrong_node = m.index_from_node(npart)  # give a NPart index
        m.update_model(wrong_node)


def test_nmodel_update_shape(data):
    raise NotImplementedError


def test_nmodel_update_operation(data):
    data.add_dummy_part()
    m: NModel = data.model
    part = m.parts_nodes[0].part
    initial_volume = part._val().Volume()
    # modifying value of the param
    box_op = data.box_op
    length = box_op.childs[0]
    length.value = 20
    idx = m.index_from_node(length)
    m.update_operation(idx)

    # check that part has correctly been updated
    part = m.parts_nodes[0].part
    new_volume = part._val().Volume()

    assert initial_volume < new_volume


def test_nmodel_link_object(dummy_model):
    m: NModel = dummy_model.model
    cut_arg_node: NArgument = m._root.find("toCut", NArgument)
    obj_node = m._root.find("test1", NPart)
    idx = m.index_from_node(cut_arg_node)
    m.link_object([idx], m.index_from_node(obj_node))

    assert cut_arg_node.is_linked(by="obj")

    # and test the un linking
    m.unlink_object(idx)
    assert not cut_arg_node.is_linked(by="obj")


def test_nmodel_link_parameters(data):
    raise NotImplementedError


def test_nmodel_unlink_parameters(data):
    raise NotImplementedError


def test_nmodel_remove_operation(data):
    raise NotImplementedError


def test_nmodel_remove_part(data):
    raise NotImplementedError


def test_nmodel_remove_shape(data):
    raise NotImplementedError


def test_nmodel_parts(data):
    raise NotImplementedError


def test_nmodel_objects(data):
    raise NotImplementedError


def test_nmodel_console(data):
    raise NotImplementedError


def test_nmodel_removeRows(data):
    raise NotImplementedError


def test_nmodel_data(data):
    raise NotImplementedError


def test_nmodel_flags(data):
    raise NotImplementedError


def test_nmodel_setData(data):
    raise NotImplementedError


def test_nmodel_insertRows(data):
    raise NotImplementedError


def test_nmodel_childrens(data):
    raise NotImplementedError


def test_nmodel_rowCount(data):
    raise NotImplementedError


def test_nmodel_columnCount(data):
    raise NotImplementedError


def test_nmodel_index(data):
    raise NotImplementedError


def test_nmodel_parent(data):
    raise NotImplementedError

