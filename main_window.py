import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractItemView, QAction, QHeaderView, QMainWindow, QMessageBox, QUndoCommand, QUndoStack, QUndoView
from nales_alpha.uic.mainwindow import Ui_MainWindow
from PyQt5.QtCore import pyqtSlot, pyqtSignal

from data_user_interface import NalesDIF

from nales_alpha.NDS.commands import DeleteTreeItem
# from nales_alpha.NDS.NOCAF import Feature, Part

from nales_alpha.NDS.model import NModel, ParamTableModel

from qt_material import apply_stylesheet
from nales_alpha.views.tree_views import ModelingOpsView

#debug related import
import debugpy
debugpy.debug_this_thread()

from nales_alpha.utils import get_Workplane_methods
from nales_alpha.widgets.msg_boxs import WrongArgMsgBox, StdErrorMsgBox

from nales_alpha.nales_cq_impl import Part


console_theme ="""QPlainTextEdit, QTextEdit { background-color: yellow;
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

class MainWindow(QMainWindow, Ui_MainWindow):

    instance = None

    def __init__(self):
        super().__init__()
        Part._mw_instance = self #give a reference to the main_window to the Part class, for connecting signals and slots

        self.setupUi(self)
        self._console.setStyleSheet(console_theme)

        self.main_menu = QMainWindow.menuBar(self)
        self.main_menu.setEnabled(True)

        ctx = self.viewer.context
        self.model = NModel(ctx = ctx, console = self._console)
        self.modeling_ops_tree.setModel(self.model)
        self.param_model = ParamTableModel([])
        self.param_table_view.setModel(self.param_model)
        self.param_model.dataChanged.connect(self.model._update_parameters)
        self.param_model.rowsRemoved.connect(lambda first : self.model._disconnect_parameter(param_idx = first))
        
        
        #Undo stack handling
        self._setup_undo_stack()

        self._setup_actions()


        self.nalesdif = NalesDIF(self)


        # Views / Widgets setup
        self._setup_param_table_view()
        self._setup_modeling_ops_view()
        
        self._console.push_vars({"nales": self.nalesdif, "Part":Part}) 


        #Connect all the slots to the needed signals
        self.model.on_arg_error.connect(lambda exp_typ, rcv_typ: WrongArgMsgBox(exp_typ,rcv_typ, self))


    def _setup_actions(self):

        self.delete_action = QAction(self)
        self.delete_action.setShortcut("Del")
        self.main_menu.addAction(self.delete_action)
        self.delete_action.triggered.connect(lambda: self.push_cmd(DeleteTreeItem(self.model, self.modeling_ops_tree.selectedIndexes())))

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

        self.uview = QUndoView(self.undo_stack)
        self.uview.setWindowTitle("Commands")
        self.uview.show()

        #connect signals
        self.model.run_cmd.connect(self.push_cmd)


    @pyqtSlot(dict)
    def handle_command(self, cmd):
        """
        This function calls the approriate NModel method depending on the command received.
        """
        
        if cmd["type"] == "undefined":
            return 
        
        if cmd["type"] == "other":
            pass

        if cmd["type"] in ("new_part","part_edit","part_override"):
            part = cmd["obj"]
            part_name = cmd["obj_name"]

            if cmd["type"]in ("new_part", "part_override"):
                self.model.add_part(part_name, part)
            
            operation = cmd["operations"]
            if len(operation) != 0:
                # self.model.add_operations(part_name, part, operation)
                self.model.add_operation(part_name, part, operation)
                # self.modeling_ops_tree.expandAll()

                self.modeling_ops_tree.expand(self.model.childrens()[0])
                self.modeling_ops_tree.expand(self.model.childrens(self.model.childrens()[0])[0])
                self.viewer.fit()


        
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
        tree.customContextMenuRequested.connect(lambda pos: tree._on_context_menu_request(pos, tree.selectionModel().selectedRows(), self.param_model, self.model)) 
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

        self.add_param_btn.clicked.connect(self.param_model.add_parameter)        
        self.rmv_param_btn.clicked.connect(lambda : self.param_model.remove_parameter(param_table.selectionModel().selectedIndexes()))
        


# if __name__ == "__main__":
def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    extra = {

    # Button colors
    'danger': '#dc3545',
    'warning': '#ffc107',
    'success': '#17a2b8',

    # Font
    'font-family': 'Roboto',
}

    apply_stylesheet(app, theme="dark_teal.xml",extra=extra)
# 
    window.show()


    app.exec_()