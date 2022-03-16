# Tests of Nales Models classes


from nales.NDS.model import NModel

############################################################
###############         NMODEL TESTING       ###############
############################################################


def test_nmodel_add_part():
    model = NModel(None)
    root_tree = model._root
    model.add_part("Toto")

    assert (node := root_tree.find("Toto")) is not None
    parts_node = root_tree.find("Parts")
    assert node in parts_node.childs


def test_nmodel_add_operation():
    pass


def test_nmodel_add_shape():
    pass


def test_nmodel_get_part_index():
    pass


def test_nmodel_get_shape_index():
    pass


def test_nmodel_update_model():
    pass


def test_nmodel_update_objs_linked_to_obj():
    pass


def test_nmodel_update_shape():
    pass


def test_nmodel_update_operation():
    pass


def test_nmodel_index_from_node():
    pass


def test_nmodel_link_object():
    pass


def test_nmodel_unlink_object():
    pass


def test_nmodel_link_parameters():
    pass


def test_nmodel_unlink_parameters():
    pass


def test_nmodel_remove_operation():
    pass


def test_nmodel_remove_part():
    pass


def test_nmodel_remove_shape():
    pass


def test_nmodel_parts():
    pass


def test_nmodel_objects():
    pass


def test_nmodel_console():
    pass


def test_nmodel_removeRows():
    pass


def test_nmodel_data():
    pass


def test_nmodel_flags():
    pass


def test_nmodel_setData():
    pass


def test_nmodel_insertRows():
    pass


def test_nmodel_childrens():
    pass


def test_nmodel_rowCount():
    pass


def test_nmodel_columnCount():
    pass


def test_nmodel_index():
    pass


def test_nmodel_parent():
    pass

