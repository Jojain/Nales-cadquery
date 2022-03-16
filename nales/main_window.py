import os
import sys
from functools import partial
from typing import List

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import QModelIndex, QPoint, QSettings, pyqtSlot
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QFileDialog,
    QHeaderView,
    QMainWindow,
    QMenu,
    QUndoCommand,
    QUndoStack,
    QUndoView,
)
from qt_material import apply_stylesheet

from nales.actions import FitViewAction
from nales.commands.add_commands import AddOperation, AddParameter, AddPart, AddShape
from nales.commands.delete_commands import DeleteOperation, DeleteParameter, DeletePart
from nales.commands.edit_commands import LinkObject, LinkParameter, UnlinkParameter
from nales.data_user_interface import NalesPublicAPI
from nales.nales_cq_impl import (
    CQMethodCall,
    NalesCompound,
    NalesEdge,
    NalesFace,
    NalesShape,
    NalesSolid,
    NalesVertex,
    NalesWire,
    Part,
)
from nales.NDS.exporters import PythonFileWriter
from nales.NDS.importers import PythonFileReader
from nales.NDS.interfaces import NArgument, NNode, NOperation, NPart
from nales.NDS.model import NModel, ParamTableModel
from nales.NDS.NOCAF import OCAFApplication
from nales.uic.mainwindow import Ui_MainWindow
from nales.utils import sort_args_kwargs
from nales.views.tree_views import ModelingOpsView
from nales.widgets.console import ConsoleWidget
from nales.widgets.msg_boxs import StdErrorMsgBox, WrongArgMsgBox
from nales.widgets.ribbon_widget import RibbonButton

console_theme = """QPlainTextEdit, QTextEdit { background-color: yellow;
        color: yellow ;
        selection-background-color: yellow}
.error { color: red; }
.in-prompt { color: navy; }
.in-prompt-number { font-weight: bold; }
.out-prompt { color: darkred; }
.out-prompt-number { font-weight: bold; }
/* .inverted is used to highlight selected completion */
.inverted { background-color: black ; color: white; }
"""


class NalesApp(QMainWindow, Ui_MainWindow):

    instance = None

    def __init__(self):
        super().__init__()

        self.setupUi(self)
        self.setWindowTitle("Nales")

        # Private variables
        self._console.setStyleSheet(console_theme)
        self._ocafapp = OCAFApplication(ctx=self.viewer.context)

        self.main_menu = QMainWindow.menuBar(self)
        self.main_menu.setEnabled(True)

        self.settings = QSettings("Nales Tech", "Nales", self)

        self.model = NModel(self._ocafapp.root_label)
        self.modeling_ops_tree.setModel(self.model)
        self.param_model = ParamTableModel([])
        self.param_table_view.setModel(self.param_model)
        self.param_model.dataChanged.connect(self.model.update_parameters)
        self.param_model.rowsRemoved.connect(
            lambda first: self.model.unlink_parameter(param_idx=first)
        )

        # Undo stack handling
        self._setup_undo_stack()

        self._setup_actions()

        self.api = NalesPublicAPI(self)

        # Views / Widgets setup
        self._setup_param_table_view()
        self._setup_modeling_ops_view()

        self._setup_ribbon()

        self._setup_exposed_classes()
        self._console.push_vars(
            {
                "nales": self.api,
                "Workplane": Part,
                "Part": Part,
                "Shape": NalesShape,
                "Compound": NalesCompound,
                "Solid": NalesSolid,
                "Face": NalesFace,
                "Wire": NalesWire,
                "Edge": NalesEdge,
                "Vertex": NalesVertex,
            }
        )

        # Connect all the slots to the needed signals
        self.model.on_arg_error.connect(
            lambda exp_typ, rcv_typ: WrongArgMsgBox(exp_typ, rcv_typ, self)
        )

        self.model.display_node.connect(self.display_node)
        self.model.hide_node.connect(self.hide_node)
        self.model.dataChanged.connect(self._ocafapp.presentation_redraw)

        self.model.console_remove_obj.connect(self._console.remove_obj)
        self.model.console_update_part.connect(self._console.update_part)

    def _setup_exposed_classes(self):
        Part._mw_instance = self  # give a reference to the main_window to the Part class, for connecting signals and slots
        NalesVertex._mw_instance = self  # give a reference to the main_window to the Part class, for connecting signals and slots
        NalesSolid._mw_instance = self  # give a reference to the main_window to the Part class, for connecting signals and slots
        NalesFace._mw_instance = self  # give a reference to the main_window to the Part class, for connecting signals and slots
        NalesCompound._mw_instance = self  # give a reference to the main_window to the Part class, for connecting signals and slots
        NalesWire._mw_instance = self  # give a reference to the main_window to the Part class, for connecting signals and slots
        NalesEdge._mw_instance = self  # give a reference to the main_window to the Part class, for connecting signals and slots

    def _setup_actions(self):

        self._actions = {}

        self._actions["delete"] = delete = QAction(self)
        self._actions["fitview"] = fitview = FitViewAction(self)

        delete.setShortcut("Del")
        # self.addAction(delete)
        # self.addAction(fitview)
        self.main_menu.addAction(delete)
        self.main_menu.addAction(fitview)
        delete.triggered.connect(self.delete_tree_item)
        fitview.triggered.connect(self.viewer.fit)

    def _setup_undo_stack(self):
        """
        Setup the undo stack and undo view
        """

        self.undo_stack = QUndoStack(self)
        undo = self.undo_stack.createUndoAction(self, "Undo")
        redo = self.undo_stack.createRedoAction(self, "Redo")
        undo.setShortcut("Ctrl+Z")
        redo.setShortcut("Ctrl+Y")
        self.main_menu.addAction(undo)
        self.main_menu.addAction(redo)

        self.undo_view = QUndoView(self.undo_stack)
        self.undo_view.setWindowTitle("Commands")
        self.undo_view.setEmptyLabel("Initial state")

        # connect signals
        self.model.run_cmd.connect(lambda cmd: self.push_cmd(cmd))
        self.param_model.run_cmd.connect(lambda cmd: self.push_cmd(cmd))

    @pyqtSlot(dict)
    def handle_command(self, cmd: dict):
        """
        This function calls the approriate NModel method depending on the command received.
        """

        if cmd["type"] == "new_shape":
            self.push_cmd(
                AddShape(
                    self.model,
                    cmd["obj_name"],
                    cmd["shape_class"],
                    cmd["obj"],
                    cmd["maker_method"],
                    cmd["args"],
                )
            )

        if cmd["type"] == "other":
            pass

        if cmd["type"] in ("new_part", "part_edit"):
            part = cmd["obj"]
            part_name = cmd["obj_name"]
            operation = cmd["operation"]

            if cmd["type"] == "new_part":
                self.push_cmd(AddPart(self.model, part_name, part, operation))
            else:
                self.push_cmd(AddOperation(self.model, part_name, part, operation))

            self.viewer.fit()

        self.modeling_ops_tree.expandAll()

    def delete_tree_item(self) -> None:
        """
        """
        selected_idx = self.modeling_ops_tree.selectedIndexes()
        if len(selected_idx) != 1:
            return
        else:
            idx = selected_idx[0]
            node = idx.internalPointer()

            if isinstance(node, NPart):
                self.push_cmd(DeletePart(self.model, idx))
            elif isinstance(node, NOperation):
                if node is node.parent.childs[-1]:
                    self.push_cmd(DeleteOperation(self.model, idx))
                else:
                    StdErrorMsgBox(
                        "Cannot delete an operation that is not the last one"
                    )

    def delete_parameter(self) -> None:

        selected_idx = self.param_table_view.selectionModel().selectedIndexes()
        if len(selected_idx) > 0:
            self.push_cmd(DeleteParameter(self.param_model, selected_idx))

    def push_cmd(self, cmd: QUndoCommand) -> None:
        """
        Push the reiceved command on the stack
        """

        self.undo_stack.push(cmd)

    def _setup_modeling_ops_view(self):
        """
        Method for handling all the display settings of the modeling operations tree view      
        """
        tree = self.modeling_ops_tree
        tree.setHeaderHidden(True)
        tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        tree.customContextMenuRequested.connect(
            lambda pos: self._on_context_menu_request(
                tree, pos, tree.selectionModel().selectedRows()
            )
        )
        # connecting slots

    def _setup_param_table_view(self):
        """
        Method for handling all the display settings of the param table view      
        """
        param_table = self.param_table_view
        param_table.horizontalHeader().hide()
        param_table.verticalHeader().hide()
        param_table.horizontalHeader().setStretchLastSection(True)
        param_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        param_model = self.param_model
        self.add_param_btn.clicked.connect(
            lambda: self.push_cmd(AddParameter(param_model))
        )
        self.rmv_param_btn.clicked.connect(self.delete_parameter)

    def _on_context_menu_request(
        self, tree: ModelingOpsView, pos: QPoint, selection: List[QModelIndex]
    ):
        param_model = self.param_model
        selection = [
            idx for idx in selection if isinstance(idx.internalPointer(), NArgument)
        ]
        context_menu = QMenu("Parameter selection", tree)
        param_submenu = context_menu.addMenu("Set parameter")
        object_submenu = context_menu.addMenu("Set object")

        selected_nodes = [item.internalPointer() for item in selection]
        if all([node.is_linked(by="param") for node in selected_nodes]):
            rmv_param_action = context_menu.addAction("Remove parameter")
            rmv_param_action.triggered.connect(
                lambda: self.push_cmd(
                    UnlinkParameter(self.param_model, self.model, selection)
                )
            )

            # add all the parameters available as linking possibility
        for (name_idx, val_idx) in [
            (param_model.index(i, 0), param_model.index(i, 1))
            for i in range(param_model.rowCount())
        ]:

            param_name = name_idx.internalPointer()
            action = param_submenu.addAction(param_name)
            # Using partial instead of lambda to solve problem of closure with lambda within loops
            # Check here for reference : https://stackoverflow.com/questions/19837486/lambda-in-a-loop
            action.triggered.connect(
                partial(
                    self.push_cmd,
                    LinkParameter(
                        self.param_model, self.model, selection, name_idx, val_idx,
                    ),
                )
            )

        # add all the objects available as linking possibility
        parent_nobjs = [arg.parent.parent for arg in selected_nodes]
        for nobj in self.model.objects:
            if nobj not in parent_nobjs:
                action = object_submenu.addAction(nobj.name)
                nobj_idx = self.model.index_from_node(nobj)

                action.triggered.connect(
                    partial(self.push_cmd, LinkObject(self.model, nobj_idx, selection))
                )

            context_menu.move(tree.mapToGlobal(pos))
            context_menu.show()

    def _setup_ribbon(self):
        self.addToolBar(self._ribbon)
        home_tab = self._ribbon.add_ribbon_tab("Home")
        file_pane = home_tab.add_ribbon_pane("File")

        # load action
        load = QAction("Load", self)
        load.triggered.connect(self.open_file)
        icon = QtGui.QIcon(":/icons/load_dm.png")
        load.setIcon(icon)
        file_pane.add_ribbon_widget(RibbonButton(self, load))

        # save action
        save = QAction("Save", self)
        save.triggered.connect(self.save_file)
        icon = QtGui.QIcon(":/icons/save_dm.png")
        save.setIcon(icon)
        file_pane.add_ribbon_widget(RibbonButton(self, save))

        # commands history action
        cmd_history = QAction("Open cmd\nHistory", self)
        # icon = QtGui.QIcon(":/icons/save_dm.png")
        # cmd_history.setIcon(icon)
        cmd_history.triggered.connect(self.undo_view.show)
        file_pane.add_ribbon_widget(RibbonButton(self, cmd_history))

        # edit_panel = home_tab.add_ribbon_pane("Edit")

        # view_panel = home_tab.add_ribbon_pane("View")
        # home_tab.add_spacer()

        # about_tab = self._ribbon.add_ribbon_tab("About")
        # info_panel = about_tab.add_ribbon_pane("Info")

    def hide_node(self, node: NNode):
        """
        Hides the provided node in the 3D viewer
        """
        node.hide()
        self._ocafapp.presentation_redraw()

    def display_node(self, node: NNode):
        """
        Displays the provided node in the 3D viewer
        """
        update = True if node.ais_solid else False
        node.display(update)
        self._ocafapp.presentation_redraw()

    def save_file(self, path=None):

        last_dir = self.settings.value("LAST_SAVE_PATH")
        if not path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Open a file", last_dir, "Python files (*.py)"
            )
        if path == "":  # the users exited the Filedialog
            return

        self.settings.setValue("LAST_SAVE_PATH", os.path.dirname(path))

        writer = PythonFileWriter(self.model, self.param_model)

        writer.write_file(path)

    def open_file(self, path=None):
        print("have been called")

        last_dir = self.settings.value("LAST_SAVE_PATH")
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open a file", last_dir, "Python files (*.py)"
            )

        if path == "":  # the user exited the Filedialog
            return

        self.settings.setValue("LAST_READ_PATH", os.path.dirname(path))

        reader = PythonFileReader(path)

        if not reader.success:
            StdErrorMsgBox(reader.error)
            return

        for param in reader.params:
            name = param.name
            try:
                value = param.value
            except TypeError as exc:
                StdErrorMsgBox(
                    f"Couldn't read the param {name}\nCheck param type : {param.type}"
                )
                return
            self.param_model.add_parameter(name, value)

        for part in reader.parts:
            name = part["name"]
            for op_name, args in part["operations"]:
                obj = reader.objects[op_name]
                if op_name != "Workplane":
                    args = sort_args_kwargs(Part, op_name, args)

                    method = getattr(Part, op_name)
                    operation = CQMethodCall(method, *args[0], **args[1])
                    self.model.add_operation(name, obj, operation)

            self._actions["fitview"].trigger()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = NalesApp()
    extra = {
        # Button colors
        "danger": "#dc3545",
        "warning": "#ffc107",
        "success": "#17a2b8",
        # Font
        "font-family": "Roboto",
    }

    apply_stylesheet(app, theme="dark_teal.xml", extra=extra)
    window.show()

    app.exec_()


if __name__ == "__main__":
    main()
