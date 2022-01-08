from PyQt5.QtWidgets import QUndoCommand


class AddOperation(QUndoCommand):
    def __init__(self)