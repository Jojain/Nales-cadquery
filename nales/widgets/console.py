import sys
from pprint import pprint
from typing import Any, List

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QApplication
from qtconsole.inprocess import QtInProcessKernelManager
from qtconsole.rich_jupyter_widget import RichJupyterWidget

from nales.nales_cq_impl import Part

# sys.stdout = sys.stderr = io.StringIO() # QtInProcessKernelManager related see https://github.com/ipython/ipython/issues/10658#issuecomment-307757082


class ConsoleWidget(RichJupyterWidget):

    name = "Console"

    def __init__(self, customBanner=None, namespace=dict(), *args, **kwargs):
        super(ConsoleWidget, self).__init__(*args, **kwargs)
        self.font_size = 6
        self.kernel_manager = kernel_manager = QtInProcessKernelManager()
        kernel_manager.start_kernel(show_banner=False)
        kernel_manager.kernel.gui = "qt"
        kernel_manager.kernel.shell.banner1 = ""

        self.kernel_client = kernel_client = self._kernel_manager.client()
        kernel_client.start_channels()

        self.namespace = self.kernel_manager.kernel.shell.user_global_ns

        def stop():
            kernel_client.stop_channels()
            kernel_manager.shutdown_kernel()
            QApplication.instance().exit()

        self.exit_requested.connect(stop)

        self.clear()

        self.push_vars(namespace)

    def remove_obj(self, obj: Any) -> None:
        """
        Remove the given `obj` (and all the vars associated) from the console namespace
        """
        ns = self.namespace

        for var, value in ns.copy().items():
            if id(value) == id(obj):
                ns.pop(var)

    def get_obj_varnames(self, obj: Any) -> List[str]:

        ns = self.namespace
        vars = []
        for var, value in ns.items():
            if value is obj:
                vars.append(var)
        return vars

    def _execute(self, source, hidden):
        """
        Execute codes in the IKernel, 
        """
        super()._execute(source, hidden)

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

        return ""

    def update_part(self, updated_part: "Part"):
        """
        Update all instances of a part in the console when it's modified in the GUI
        """
        raise NotImplementedError("Je dois revoir le fonctionnement de ce point")
        for var, part in [
            (var, part)
            for var, part in self.namespace.items()
            if isinstance(part, Part)
        ]:
            if part._name == name:
                self.namespace[var] = updated_part


if __name__ == "__main__":

    import sys

    app = QApplication(sys.argv)

    console = ConsoleWidget(customBanner="IPython console test")
    console.show()

    sys.exit(app.exec_())
