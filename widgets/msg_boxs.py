
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget
from PyQt5.QtCore import QSize, Qt
from qt_material import apply_stylesheet


class WrongArgMsgBox(QMessageBox):
    def __init__(self, expected_arg_type, received_arg_type, parent = None ):
        super().__init__(parent)
        self.setWindowTitle("Error")
        self.setText(("Wrong argument type"))
        self.setInformativeText(f"The argument type should be of type : \n{expected_arg_type}\nBut received :\n{received_arg_type}")
        self.setStandardButtons(QMessageBox.Ok)
        self.setStyleSheet("QLabel{min-width:250 px}")
        self.exec_()

class StdErrorMsgBox(QMessageBox):
    def __init__(self, error_msg, parent = None ):
        super().__init__(parent)
        self.setWindowTitle("Error")
        self.setText(error_msg)
        self.setStandardButtons(QMessageBox.Ok)
        self.setStyleSheet("QLabel{min-width:250 px}")
        self.exec_()



if __name__ == "__main__":
    app = QApplication([])
    apply_stylesheet(app, theme="dark_teal.xml")
    msgbox = WrongArgMsgBox(tuple)
    app.exec_() 