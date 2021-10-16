from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget, QMainWindow
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager
from nales_alpha.NDS.commands import CQAssignAnalyzer, Command, prepare_parent_childs
import sys, io 
import ast
from PyQt5 import QtWidgets
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

        def stop():
            kernel_client.stop_channels()
            kernel_manager.shutdown_kernel()
            QApplication.instance().exit()

        self.exit_requested.connect(stop)
        
        self.clear()
        
        self.push_vars(namespace)



    def _execute(self, source, hidden):
        """
        Execute codes in the IKernel, 
        """   
        ns = self._get_console_namespace()
        ns_before_cmd = ns.copy() # on récupère l'état du namespace avant l'exécution de la cmd

        super()._execute(source, hidden)
        
        # self.exit_requested.connect a voir si je peux gerer les erreurs de la console avec un signal pour pas excecuter la suite du code
        # self.executed.connect

        # analyzer = CommandAnalyzer(ns, ns_before_cmd)
        analyzer = CQAssignAnalyzer(ns, ns_before_cmd)
        cmd_raw_ast = ast.parse(source)
        # this must be called before the analyzer visit the tree
        prepare_parent_childs(cmd_raw_ast)
        analyzer.visit(cmd_raw_ast)

        
        cmds = analyzer.get_commands()        
        for cmd in cmds:
            self.on_command.emit(cmd)



        
    def _get_console_namespace(self):
        return self.kernel_manager.kernel.shell.user_global_ns

    def get_workplane(self, var_name):
        """
        Retrieve a Workplane object from the IKernel namespace
        """
        ns = self._get_console_namespace()
        try:
            return ns[var_name]
        except KeyError:
            print(f"No Workplane named {var_name}")
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