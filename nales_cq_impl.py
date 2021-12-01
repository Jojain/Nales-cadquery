import cadquery as cq
import inspect
from functools import wraps

from PyQt5.QtCore import QObject, pyqtSignal
from cadquery import Workplane
from utils import get_Wp_method_kwargs


from widgets.msg_boxs import StdErrorMsgBox





class Part(Workplane, QObject):
    """

    """
    on_part_edit = pyqtSignal(dict) #dict format : name, operation_dict
    on_name_error = pyqtSignal(str)
    _names = []

    def __init__(self, *args, name = None,**kwargs):
        
        Workplane.__init__(self,*args, **kwargs)
        QObject.__init__(self)

        from nales_alpha.main_window import MainWindow
        self.on_name_error.connect(lambda msg: StdErrorMsgBox(msg, MainWindow.instance))

        self._operations = []
        self.part_id = None
        self.recursive_calls_id = 0
        self.main_call_id = 1
        self.error_traceback = None

        if name:
            if name not in Part._names:
                Part._names.append(name)
            else:
                self.on_name_error.emit("This part name is already taken,\ndelete it or use another name.")
            self.name = name


        else:
            index = 1           
            while (auto_name:=f"Part{index}") in Part._names:
                index+=1
            Part._names.append(auto_name)
            self.name = name
        
        self._monkey_patch_Workplane()

    def _operation_handler(self, cq_method):
        @wraps(cq_method)
        def cq_wrapper(*args, **kwargs):  
            parent_wp_obj = self.parent if self.parent is not None else self
            method_name = cq_method.__name__ if cq_method.__name__ != "__init__" else "Workplane"
            self.part_id = id(parent_wp_obj)

            # Since we aren't interested by the operations data of an internal call
            # we start a counter of recursive calls that is decrease after the `cq_method` call
            # Thus by checking the call id we know if it's an internal call or not
            self.recursive_calls_id += 1

            # Since a cq_method can have internals calls to other cq_methods, cq_wrapper is called recursively here
            try:
                obj = cq_method(self, *args, **kwargs)  
                obj.name = "toto"
                
            except Exception as exc:
                splitter = "---------------------------------------------------------------------------"
                error_tb = f"{splitter}\nError in method Workplane.{cq_method.__name__}\n {repr(exc)}\n"
                self.error_traceback = error_tb
                self.recursive_calls_id -= 1 
                return parent_wp_obj      

            if self.main_call_id == self.recursive_calls_id:
                operations = {}                    
                default_kwargs = get_Wp_method_kwargs(method_name)
                if kwargs:                
                    for kwarg, val in kwargs.items():
                        default_kwargs[kwarg] = val
                
                operations[method_name] = ([arg for arg in args[1:]], default_kwargs)

                # self._operations.append(operations)
                self.on_part_edit.emit(operations)

            self.recursive_calls_id -= 1 

            return obj


        return cq_wrapper


    def _monkey_patch_Workplane(self):                
        # Monkey patch every method of Workplane class to retrieve info from calls
        for method in [method for (name, method) in inspect.getmembers(Workplane) if not (name.startswith("_") and name != "__init__")]:
            method = self._operation_handler(method)
            setattr(self, method.__name__, method)

    # def _monkey_patch_Workplane(self):                
    #     # Monkey patch every method of Workplane class to retrieve info from calls
    #     for method in [method for (name, method) in inspect.getmembers(cq.Workplane) if not (name.startswith("_") and name != "__init__")]:
    #         method = self._operation_handler(method)
    #         setattr(cq.Workplane, method.__name__, method)


# p = Part()
# print(Part._names)
# p = Part()
# print(Part._names)
# p = Part(name="Part10")
# print(Part._names)
# p = Part(name="Part10")
# print(Part._names)
# p = Part(inPlane="ZY",name="Wheel")
# print(Part._names)

