# Tests of Nales Models classes

from nales.main_window import MainWindow


def setup_window(qtbot):
    mw = MainWindow()
    mw.hide()
    qtbot.addWidget(mw)
    return mw

############################################################
###############         NMODEL TESTING       ###############
############################################################

def test_nmodel_add_part(qtbot):
def test_nmodel_add_operation(qtbot):
def test_nmodel_add_shape(qtbot):
def test_nmodel_get_part_index(qtbot):
def test_nmodel_get_shape_index(qtbot):
def test_nmodel_update_model(qtbot):
def test_nmodel_update_objs_linked_to_obj(qtbot):
def test_nmodel_update_shape(qtbot):
def test_nmodel_update_operation(qtbot):
def test_nmodel_index_from_node(qtbot):
def test_nmodel_link_object(qtbot):
def test_nmodel_unlink_object(qtbot):
def test_nmodel_link_parameters(qtbot):
def test_nmodel_unlink_parameters(qtbot):
def test_nmodel_remove_operation(qtbot):
def test_nmodel_remove_part(qtbot):
def test_nmodel_remove_shape(qtbot):

def test_nmodel_parts(qtbot):
def test_nmodel_objects(qtbot):
def test_nmodel_console(qtbot):

def test_nmodel_removeRows(qtbot):
def test_nmodel_data(qtbot):
def test_nmodel_flags(qtbot):
def test_nmodel_setData(qtbot):
def test_nmodel_insertRows(qtbot):


def test_nmodel_childrens(qtbot):
def test_nmodel_rowCount(qtbot):
def test_nmodel_columnCount(qtbot):
def test_nmodel_index(qtbot):
def test_nmodel_parent(qtbot):
