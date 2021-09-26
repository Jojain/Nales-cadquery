from PyQt5.QtCore import QModelIndex, QPersistentModelIndex, QPoint
from nales_alpha.NDS.model import NModel, ParamTableModel, Argument
from PyQt5.QtWidgets import QMenu, QTreeView, QWidget
from typing import List, Optional



class ModelingOpsView(QTreeView):
    def __init__(self, parent: Optional[QWidget] = ...) -> None:
        super().__init__(parent=parent)

        # self.actions = []
        


    def _on_context_menu_request(self, pos: QPoint, selection: List[QModelIndex], param_model: ParamTableModel, modeling_ops_model: NModel):
        for item in selection:
            node = item.internalPointer()
            if isinstance(node, Argument):
                context_menu = QMenu("Parameter selection", self)
                submenu = context_menu.addMenu("Set parameter")
                
                if node._linked_param:
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