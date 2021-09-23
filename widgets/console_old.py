from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager
from nales_alpha.NDS.commands import Command
import sys, io 

sys.stdout = sys.stderr = io.StringIO() # QtInProcessKernelManager related see https://github.com/ipython/ipython/issues/10658#issuecomment-307757082


# on_command2 = 
class _ConsoleWidget(RichJupyterWidget):
    
    name = 'Console'


    def __init__(self, customBanner=None, namespace=dict(), *args, **kwargs):
        super(_ConsoleWidget, self).__init__(*args, **kwargs)

#        if not customBanner is None:
#            self.banner = customBanner

        self.font_size = 6
        self.kernel_manager = kernel_manager = QtInProcessKernelManager()
        self.pushed_vars = {}

        kernel_manager.start_kernel(show_banner=False)
        kernel_manager.kernel.gui = 'qt'
        kernel_manager.kernel.shell.banner1 = ""
        
        self.kernel_client = kernel_client = self._kernel_manager.client()
        kernel_client.start_channels()

        def stop():
            kernel_client.stop_channels()
            kernel_manager.shutdown_kernel()
            QApplication.instance().exit()

        
        def print_text2(self):
            """
            Prints some plain text to the console
            """
            self._append_plain_text("toto")


        self.executed.connect(print_text2)
        self.exit_requested.connect(stop)
        
        self.clear()
        
        self.push_vars(namespace)




    @pyqtSlot(dict)
    def push_vars(self, variable_dict):
        """
        Given a dictionary containing name / value pairs, push those variables
        to the Jupyter console widget
        """
        self.pushed_vars.update(variable_dict)
        self.kernel_manager.kernel.shell.push(variable_dict)
    def clear(self):
        """
        Clears the terminal
        """
        self._control.clear()

    @pyqtSlot(str)
    def print_text(self, text):
        """
        Prints some plain text to the console
        """
        self._append_plain_text(text)

    
    def _execute(self, source: str, hidden: bool) -> None:
        """
        Lorsque du code est entré dans la console, un signal est envoyé avec un objet Command
        Cet objet doit être réceptionné par des slots pour mettre à jour l'application en fonction de ce
        qu'elle contient
        """

        
        super()._execute(source, hidden)

    def execute_command(self, command):
        """
        Execute a command in the frame of the console widget
        """
        self._execute(command, False)
        
    def _banner_default(self):
        
        return ''

class ConsoleWidget(QWidget):   
    def __init__(self, *args, **kwargs):
        super(ConsoleWidget, self).__init__(*args, **kwargs) 
        layout = QHBoxLayout()
        self._console = _ConsoleWidget()
        layout.addWidget(self._console)
        
        self.setLayout(layout)


if __name__ == "__main__":
   
    
    import sys
    
    app = QApplication(sys.argv)
    
    console = _ConsoleWidget()
    console.show()
    
    sys.exit(app.exec_())