import inspect
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QMessageBox
from cadquery.cq import Workplane
from nales_alpha.uic.mainwindow import Ui_MainWindow
import qtconsole
from PyQt5.QtCore import pyqtSlot, pyqtSignal
import cadquery as cq
import OCP
from OCP.TDocStd import TDocStd_Application, TDocStd_Document

from nales_alpha.NDS import NOCAF
# from nales_alpha.NDS.NOCAF import Feature, Part
import re
from nales_alpha.NDS.commands import Command
from nales_alpha.NDS.model import NModel, NNode, ParamTableModel

import nales_alpha.monkey_patcher 
from nales_alpha.monkey_patcher import OperationHandler

from qt_material import apply_stylesheet
from nales_alpha.views.tree_views import ModelingOpsView
#debug related import
# import debugpy

from nales_alpha.utils import get_Workplane_methods
from nales_alpha.widgets.msg_boxs import WrongArgMsgBox, StdErrorMsgBox

from nales_cq_impl import Part
# debugpy.debug_this_thread()


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

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    instance = None

    def __init__(self):
        super().__init__()
        MainWindow.instance = self
        self.setupUi(self)
        self._console.setStyleSheet(console_theme)


        ctx = self.viewer.context
        self.model = NModel(ctx = ctx, console = self._console)
        self.modeling_ops_tree.setModel(self.model)
        self.param_model = ParamTableModel([])
        self.param_table_view.setModel(self.param_model)
        self.param_model.dataChanged.connect(self.model._update_parameters)
        self.param_model.rowsRemoved.connect(lambda first : self.model._disconnect_parameter(param_idx = first))

        # Views / Widgets setup
        self._setup_param_table_view()
        self._setup_modeling_ops_view()
                


        self._console.push_vars({"model" : self.model, "mw": self, "save": self.model.app.save_as, "Part":Part}) 


        #Connect all the slots to the needed signals
        self._console.on_command.connect(lambda c : handle_command(self, c))
        self.model.on_arg_error.connect(lambda exp_typ, rcv_typ: WrongArgMsgBox(exp_typ,rcv_typ, self))
        
        # self.sh = SignalHandler()
        # self.sh.on_name_error.connect(lambda error_msg: StdErrorMsgBox(error_msg, self))

        @pyqtSlot(Command)
        def handle_command(self, cmd):
            """
            This function calls the approriate NModel method depending on the command received.
            """
            return
            if cmd.type == "undefined":
                return 
            
            if cmd.type == "other":
                pass

            if cmd.type in ("new_part","part_edit","part_override"):
                part = cmd.obj
                part_name = cmd.var

                if cmd.type in ("new_part", "part_override"):
                    self.model.add_part(part_name, part)
                
                for operation in cmd.operations:
                    if len(operation) != 0:
                        self.model.add_operations(part_name, part, operation)
                        # self.modeling_ops_tree.expandAll()

                        self.modeling_ops_tree.expand(self.model.childrens()[0])
                        self.modeling_ops_tree.expand(self.model.childrens(self.model.childrens()[0])[0])
                        self.viewer.fit()


            if cmd.type == "new_shape":
                shape = cmd.obj
                shape_name = cmd.var
                topo_type = cmd.topo_type
                method_call = cmd.operations
                self.model.add_shape(shape_name, shape, topo_type, method_call)     
                self.modeling_ops_tree.expandAll()

        

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