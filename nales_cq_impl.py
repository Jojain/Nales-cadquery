import cadquery as cq
import inspect
from functools import wraps

from PyQt5.QtCore import QObject, pyqtSignal
from cadquery import Workplane
from utils import get_Wp_method_kwargs


from widgets.msg_boxs import StdErrorMsgBox
        
class PartSignalsHandler(type(QObject)):
    def __new__(cls, name, bases, dct):  
        dct['on_method_call'] = pyqtSignal(dict)
        dct['on_name_error'] = pyqtSignal(str)

        return super().__new__(cls, name, bases, dct)

class PartWrapper(PartSignalsHandler):

    recursive = False

    @staticmethod
    def _create_cmd(*args):
        return {}

    @staticmethod
    def _operation_handler(cq_method):
        @wraps(cq_method)
        def cq_wrapper(*args, **kwargs):  
            # Since a cq_method can have internals calls to other cq_methods, cq_wrapper is called recursively here
            obj = args[0]
            parent_obj = obj.parent if obj.parent is not None else obj
            
            if not PartWrapper.recursive:
                PartWrapper.recursive = True
            try:
                obj = cq_method(obj, *args[1:], **kwargs)  
                
            except Exception as exc:
                splitter = "---------------------------------------------------------------------------"
                error_tb = f"{splitter}\nError in method Workplane.{cq_method.__name__}\n {repr(exc)}\n"
                print(error_tb)
                return parent_obj     

            if not PartWrapper.recursive: # we are in the top level method call
                operations = {}                    
                default_kwargs = get_Wp_method_kwargs(cq_method.__name__)
                if kwargs:                
                    for kwarg, val in kwargs.items():
                        default_kwargs[kwarg] = val
                
                operations[cq_method.__name__] = ([arg for arg in args[1:]], default_kwargs)
                cmd = PartWrapper._create_cmd(cq_method.__name__, obj, operations)
                obj.on_method_call.emit(cmd)

                print("emitted")

            PartWrapper.recursive = False
            return obj

        return cq_wrapper

    @staticmethod
    def _wrap_Workplane(dct):                
        # Monkey patch every method of Workplane class to retrieve info from calls
        for method in [method for (name, method) in inspect.getmembers(Workplane) if not name.startswith("_") ]:
            method = PartWrapper._operation_handler(method)
            dct[method.__name__] = method

        return dct

    def __new__(cls, name, bases, dct):
        PartWrapper._wrap_Workplane(dct)
        return super().__new__(cls, name, bases, dct) 

class Part(Workplane,QObject,metaclass=PartWrapper):
    
    mw_instance = None # this fields holds the mainwindow instance and is initialized in the main_window __init__ function
    _names = []

    def __init__(self, *args, name = None,**kwargs): 
        Workplane.__init__(self, *args, **kwargs)  
        parent = self.parent
        QObject.__init__(self)
        

        self.on_name_error.connect(lambda msg: StdErrorMsgBox(msg, self.mw_instance))
        self.on_method_call.connect(lambda ops: self.mw_instance.handle_command(ops))

        if self.parent is None:
            if name:
                if name not in Part._names:
                    Part._names.append(name)
                else:
                    self.on_name_error.emit("This part name is already taken,\ndelete it or use another name.")
                self._name = name

            else:
                index = 1           
                while (auto_name:=f"Part{index}") in Part._names:
                    index+=1
                Part._names.append(auto_name)
                self._name = auto_name
            cmd={"type":"new_part", "obj_name":self._name, "operations":{}, "obj":self}
            self.on_method_call.emit(cmd)
        else:
            self._name = self.parent._name



if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication, QMainWindow
    import sys
    app = QApplication(sys.argv)
    mw = QMainWindow()
    mw.show()

    Part.mainwindow = mw
    p = Part()
    print(type(p))
    # p.on_name_error.connect(lambda msg: StdErrorMsgBox(msg, p.mainwindow))
    # p.on_name_error.emit("This part name is already taken,\ndelete it or use another name.")
    p



class Part2(Workplane, QObject):
    """

    """
    on_method_call = pyqtSignal(dict) #dict format : name, operation_dict
    on_name_error = pyqtSignal(str)
    _names = []

    def __init__(self, *args, name = None,**kwargs):
        
        Workplane.__init__(self,*args, **kwargs)
        QObject.__init__(self)

        from nales_alpha.main_window import MainWindow
        self.on_name_error.connect(lambda msg: StdErrorMsgBox(msg, MainWindow.instance))
        self.on_method_call.connect(lambda ops: MainWindow.instance.handle_command(ops))

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
            self._name = name

        else:
            index = 1           
            while (auto_name:=f"Part{index}") in Part._names:
                index+=1
            Part._names.append(auto_name)
            self._name = auto_name
        self._monkey_patch_Workplane()

        # cmd={"type":"new_part", "obj_name":self._name, "operations":{}, "obj":self}
        # self.on_method_call.emit(cmd)

    def newObject(self, objlist):
        new_obj =  super().newObject(objlist)
        new_obj._name = self._name
        return new_obj

    def _create_cmd(self, method_name, new_obj, operations):

        cmd = {}
        
        if method_name == "__init__":
            cmd["type"] = "new_part"
        else:
            cmd["type"] = "part_edit"

        cmd["obj_name"] = self._name 
        cmd["obj"] = new_obj
        cmd["operations"] = operations

        return cmd

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
                cmd = self._create_cmd(method_name, obj, operations)
                self.on_method_call.emit(cmd)
                print("emitted")

            self.recursive_calls_id -= 1 

            return obj


        return cq_wrapper


    def _monkey_patch_Workplane(self):                
        # Monkey patch every method of Workplane class to retrieve info from calls
        for method in [method for (name, method) in inspect.getmembers(Workplane) if not (name.startswith("_") and name != "__init__")]:
        # for method in [method for (name, method) in inspect.getmembers(self) if (method in inspect.getmembers(Workplane) and not (name.startswith("_")))]:
        # for method in [method for (name, method) in inspect.getmembers(self)]:# if (name,method) in inspect.getmembers(Workplane)]:
            method = self._operation_handler(method)
            # print(method.__name__)
            setattr(self, method.__name__, method)


