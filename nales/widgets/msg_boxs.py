from typing import List, Union

from PyQt5.QtWidgets import QApplication, QMessageBox
from qt_material import apply_stylesheet


class WrongArgMsgBox(QMessageBox):
    def __init__(self, expected_arg_type, received_arg_type, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Error")
        self.setText(("Wrong argument type"))
        self.setInformativeText(
            f"The argument type should be of type : \n{expected_arg_type}\nBut received :\n{received_arg_type}"
        )
        self.setStandardButtons(QMessageBox.Ok)
        self.setStyleSheet("QLabel{min-width:250 px}")
        self.exec_()


class StdErrorMsgBox(QMessageBox):
    def __init__(self, error_msg: Union[str, List[str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Error")
        if isinstance(error_msg, list):
            text = "\n".join(error_msg)
        else:
            text = error_msg
        self.setText(text)
        self.setStandardButtons(QMessageBox.Ok)
        self.setStyleSheet("QLabel{min-width:500 px}")
        self.exec_()


if __name__ == "__main__":
    app = QApplication([])
    apply_stylesheet(app, theme="dark_teal.xml")
    msgbox = WrongArgMsgBox(tuple)
    app.exec_()
