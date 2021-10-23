from PyQt5.QtCore import QModelIndex, QObject, QPersistentModelIndex, QPoint, Qt
from PyQt5.QtGui import QPalette
from nales_alpha.NDS.model import NModel, ParamTableModel
from nales_alpha.NDS.interfaces import NArgument
from PyQt5.QtWidgets import QMenu, QStyle, QStyleOptionViewItem, QStyledItemDelegate, QTreeView, QWidget
from typing import List, Optional



class MyDelegate(QStyledItemDelegate):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent=parent)

    def paint(self, painter, option:QStyleOptionViewItem , index:QModelIndex ): 
        if (option.state and QStyle.State_Selected):
            optCopy = option
            optCopy.palette.setColor(QPalette.Foreground, Qt.red)
        
        super().paint(painter, optCopy, index)
    


class ModelingOpsView(QTreeView):
    def __init__(self, parent: Optional[QWidget] = ...) -> None:
        super().__init__(parent=parent)

        # self.dl = MyDelegate()
        # self.setItemDelegateForRow(0,self.dl)
        # self.actions = []
        


    def _on_context_menu_request(self, pos: QPoint, selection: List[QModelIndex], param_model: ParamTableModel, modeling_ops_model: NModel):
        for item in selection:
            node = item.internalPointer()
            if isinstance(node, NArgument):
                context_menu = QMenu("Parameter selection", self)
                submenu = context_menu.addMenu("Set parameter")
                
                if node.is_linked():
                    rmv_param_action = context_menu.addAction("Remove parameter")
                    rmv_param_action.triggered.connect(lambda : modeling_ops_model._disconnect_parameter(item))

                # add all the parameters available as linking possibility
                for (name_idx, val_idx) in [(param_model.index(i,0), param_model.index(i,1)) for i in range(param_model.rowCount())]  :

                    param_name = name_idx.internalPointer()
                    action = submenu.addAction(param_name)
                    action.triggered.connect(lambda : modeling_ops_model._link_parameters(selection, QPersistentModelIndex(name_idx), QPersistentModelIndex(val_idx)))


                context_menu.move(self.mapToGlobal(pos))
                context_menu.show()
            else:
                return