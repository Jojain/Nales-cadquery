
#%%
import inspect
from cadquery import Workplane
from functools import wraps
import cadquery as cq
from nales_alpha.utils import get_Workplane_methods, get_Wp_method_kwargs, get_topo_class_methods



class OperationHandler():
    def __init__(self):
        super().__init__()
        self.operations = []
        self.part_id = None
        self.recursive_calls_id = 0
        self.main_call_id = 1
        self._monkey_patch()

    def reset(self):
        self.part_id = None 
        self.operations = []

    def has_seen_cq_cmd(self):
        if self.part_id is None and len(self.operations) == 0:
            return False 
        else:
            return True

    def _operation_handler(self, cq_method):
        @wraps(cq_method)
        def cq_wrapper(*args, **kwargs):  
            parent_wp_obj = args[0] 
            method_name = cq_method.__name__ if cq_method.__name__ != "__init__" else "Workplane"
            self.part_id = id(parent_wp_obj)

            # Since we aren't interested by the operations data of an internal call
            # we start a counter of recursive calls that is decrease after the `cq_method` call
            # Thus by checking the call id we know if it's an internal call or not
            self.recursive_calls_id += 1

            # Since a cq_method can have internals calls to other cq_methods, cq_wrapper is called recursively here
            obj = cq_method(*args, **kwargs)        

            if self.main_call_id == self.recursive_calls_id:
                operations = {}                    
                default_kwargs = get_Wp_method_kwargs(method_name)
                if kwargs:                
                    for kwarg, val in kwargs.items():
                        default_kwargs[kwarg] = val
                
                operations[method_name] = ([arg for arg in args[1:]], default_kwargs)

                self.operations.append(operations)

            self.recursive_calls_id -= 1 

            return obj


        return cq_wrapper


    def _monkey_patch(self):                
        # Monkey patch every method of Workplane class to retrieve info from calls
        for method in [method for (name, method) in inspect.getmembers(cq.Workplane) if not (name.startswith("_") and name != "__init__")]:
            method = self._operation_handler(method)
            setattr(cq.Workplane, method.__name__, method)



if __name__ == "__main__":
    import pprint
    oh = OperationHandler()
    test = cq.Workplane().sphere(2).box(1,1,1).union(cq.Workplane().sphere(3))
    print("test part_id", oh.part_id)
    print(id(globals()["test"]))
    pprint.pprint(oh.operations)

    oh.reset()

    toto = test.sphere(2)
    print("toto part_id", oh.part_id)
    print(id(globals()["toto"]))

    pprint.pprint(oh.operations)

    



# %%
