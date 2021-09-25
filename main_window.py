import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView
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
from nales_alpha.NDS.model import NModel, NNode, ParamTableModel, setup_dummy_model

from qt_material import apply_stylesheet

#debug related import
# import debugpy
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
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self._console.setStyleSheet(console_theme)


        ctx = self.viewer.context
        self.model = NModel(ctx = ctx)
        self.tree.setModel(self.model)
        self.param_model = ParamTableModel([["toto",10], ["papa", 60]])
        self.param_table_view.setModel(self.param_model)

        self._setup_param_table_view()
        self._console.push_vars({"model" : self.model, "mw": self, "save": self.model.app.save_as, "cq" : cq}) 
        

        




        #Connect all the slots to the needed signals
        self._console.on_command.connect(lambda c : handle_command(self, c))


        @pyqtSlot(Command)
        def handle_command(self, command):
            """
            This function calls the approriate NModel method depending on the command received.
            """
            if command.type == "new_part":
                wp = command.workplane
                part_name = command.var
                operations = command.operations
                self.model.add_part(part_name, wp)
                if len(operations) != 0 :
                    self.model.add_operations(part_name, wp, operations)
                    self.tree.expandAll()
                    self.viewer.fit()

            if command.type == "part_edit":
                wp = command.workplane
                part_name = command.var
                operations = command.operations
                if len(operations) != 0 :
                    self.model.add_operations(part_name, wp, operations)
                    self.model.app._pres_viewer.Update()
                    self.tree.expandAll()

    def _setup_param_table_view(self):
        """
        Method for handling all the display settings of the param table view      
        """
        table = self.param_table_view
        table.horizontalHeader().hide()
        table.verticalHeader().hide()
        table.horizontalHeader().setStretchLastSection(True) 
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) 
        # self.left_panel_container.doubleClicked.connect(self.param_model.add_parameter)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    apply_stylesheet(app, theme="dark_teal.xml")

    window.show()


    app.exec_()