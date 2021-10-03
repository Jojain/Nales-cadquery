#%%
import inspect
from tokenize import String
from typing import Callable, Dict, List
from cadquery import Workplane
from inspect import signature
from cadquery.occ_impl import shapes

def get_Workplane_operations() -> Dict[str,Callable]:
    """
    This function retrieve all the 'operations' of the Workplane
    object that can be display in the gui
    """
    
    # For now it just gives all the public method of the class
    # but it the future we want to not take in accout things like
    # workplane, transformed, selectors, etc.

    operations = dict((func,getattr(Workplane,func)) for func in dir(Workplane) if callable(getattr(Workplane, func)) and not func.startswith("_"))
    operations["Workplane"] = Workplane.__init__

    return operations

def get_shapes_classes_methods(class_name: String) -> List:
    
    methods = []
    for name, obj in inspect.getmembers(shapes):
        if inspect.isclass(obj):
            if class_name == name:
                methods = [func for func in dir(obj) if callable(getattr(obj,func)) and not func.startswith("_")]
    return methods
    
    

def get_cq_topo_classes() -> List[str]:
    """
    Returns all the cadquery topological classes
    """
    classes = []
    for name, obj in inspect.getmembers(shapes):
        if inspect.isclass(obj):
            classes.append(name)
    return classes


if __name__ == "__main__":
    # print(get_Workplane_operations())
    print(get_shapes_classes_methods("Edge"))