
#%%
from typing import OrderedDict
from PyQt5.QtCore import QObject, pyqtSignal
from nales_alpha.NDS.commands import  Command
from cadquery import Workplane
from functools import wraps
import cadquery as cq
from nales_alpha.utils import get_Workplane_methods, get_Wp_method_kwargs, get_topo_class_methods



class OperationHandler(QObject):
    on_command = pyqtSignal(Command)
    def __init__(self, ns):
        super().__init__()
        self.ns = ns
        
        self.operations = []
        # self.monkey_patch()
     


    def operation_handler(self, cq_method):
        @wraps(cq_method)
        def wrapper(*args, **kwargs):   
            for method_name, method in get_Workplane_methods().items():
                if cq_method.__name__ == method.__name__:
                    operations = OrderedDict()
                    default_kwargs = get_Wp_method_kwargs(method_name)

                    if kwargs:
                
                        for kwarg, val in kwargs.items():
                            default_kwargs[kwarg] = val
                    
                    operations[method_name] = ([arg for arg in args[1:]], default_kwargs)

                    self.operations.append(operations)

                    return cq_method(*args, **kwargs)

        return wrapper


    def monkey_patch(self):
        for method_name, method in get_Workplane_methods().items():
            method = self.operation_handler(method)




# u = Workplane()
# u = u.box(1,1,1)
# print(u.val().Volume())


# %%
