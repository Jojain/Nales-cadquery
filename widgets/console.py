import inspect
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget, QMainWindow
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager
from nales_alpha.NDS.commands import CQAssignAnalyzer, Command, prepare_parent_childs
import sys, io 
import ast
from PyQt5 import QtWidgets
import cadquery as cq

from nales_alpha.monkey_patcher import OperationHandler
# sys.stdout = sys.stderr = io.StringIO() # QtInProcessKernelManager related see https://github.com/ipython/ipython/issues/10658#issuecomment-307757082


class ConsoleWidget(RichJupyterWidget):
    
    name = 'Console'
    on_command = pyqtSignal(Command)
    def __init__(self, customBanner=None, namespace=dict(), *args, **kwargs):
        super(ConsoleWidget, self).__init__(*args, **kwargs)

#        if not customBanner is None:
#            self.banner = customBanner

        self.font_size = 6
        self.kernel_manager = kernel_manager = QtInProcessKernelManager()
        kernel_manager.start_kernel(show_banner=False)
        kernel_manager.kernel.gui = 'qt'
        kernel_manager.kernel.shell.banner1 = ""
        
        self.kernel_client = kernel_client = self._kernel_manager.client()
        kernel_client.start_channels()

        self.cmd_handler = OperationHandler()
        
        self.namespace = self.kernel_manager.kernel.shell.user_global_ns

        
        def stop():
            kernel_client.stop_channels()
            kernel_manager.shutdown_kernel()
            QApplication.instance().exit()

        self.exit_requested.connect(stop)
        
        self.clear()
        
        self.push_vars(namespace)

    def _get_part_varname(self, wp_id: int) -> str:

        ns = self.namespace 

        for var, value in ns.items():
            if id(value) == wp_id :
                return var 
        

    def _execute(self, source, hidden):
        """
        Execute codes in the IKernel, 
        """   
        self.cmd_handler.reset()
        ns_before_cmd = self.namespace.copy()
        super()._execute(source, hidden)

        if self.cmd_handler.has_seen_cq_cmd():            
            part_name = self._get_part_varname(self.cmd_handler.part_id)
            ops = self.cmd_handler.get_operations()
            obj = self._get_cq_obj(part_name)    

            if part_name in ns_before_cmd.keys():
                new_var = False 
            else:
                new_var = True     

            if not self.cmd_handler.error_traceback:
                cmd = Command(part_name, ops, obj, new_var = new_var)      
                self.on_command.emit(cmd)
            else:
                if not new_var:
                    self.namespace[part_name] = ns_before_cmd[part_name] #We restore the state of the part before the error
                self._append_plain_text(self.cmd_handler.error_traceback, True)    



        
    # def _get_console_namespace(self):
    #     return self.kernel_manager.kernel.shell.user_global_ns

    def _get_cq_obj(self, var_name):
        """
        Retrieve a Workplane object from the IKernel namespace
        """
        ns = self.namespace
        try:
            return ns[var_name]
        except KeyError:
            return None

    @pyqtSlot(dict)
    def push_vars(self, variableDict):
        """
        Given a dictionary containing name / value pairs, push those variables
        to the Jupyter console widget
        """
        self.kernel_manager.kernel.shell.push(variableDict)

    def clear(self):
        """
        Clears the terminal
        """
        self._control.clear()


    def print_text(self, text):
        """
        Prints some plain text to the console
        """
        self._append_plain_text(text)

    def execute_command(self, command):
        """
        Execute a command in the frame of the console widget
        """
        self._execute(command, False)
        
    def _banner_default(self):
        
        return ''



        
if __name__ == "__main__":
   
    
    import sys


    app = QApplication(sys.argv)
    
    console = ConsoleWidget(customBanner='IPython console test')
    console.show()
    
    sys.exit(app.exec_())