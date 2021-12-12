#%%
import inspect
from typing import Callable, Dict, List, Union
from cadquery import Workplane
import cadquery 
from inspect import signature
import cadquery
from collections import OrderedDict
import ast

PY_TYPES_TO_AST_NODE = {int : ast.Constant, float: ast.Constant, str: ast.Constant, tuple: ast.Tuple, list: ast.List,
bool: ast.Constant, set: ast.Set}

# class Number(type)


def determine_type_from_str(string: str):
    
    node = ast.parse(string).body[0].value

    if string == "True" or string == "False":
        return bool 
    
    if isinstance(node, ast.Tuple):
        return tuple 
    elif isinstance(node, ast.List):
        return list 
    elif isinstance(node, ast.Dict):
        return dict
    
    try:
        int(string)
        return int
    except ValueError:
        try:
            float(string)
            return float 
        except ValueError:
            return str


    
    

    

def get_Workplane_methods() -> Dict[str,Callable]:
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


def get_Wp_method_args_name(method: Union[str,Callable]) -> list:
    if isinstance(method, str):
        method = get_Workplane_methods()[method]
    params = inspect.signature(method).parameters
    args = []
    for p in params.values():
        if p.default is p.empty and p.name != "self": 
            args.append(p.name)
    return args

def get_Wp_method_kwargs(method: Union[str,Callable]) -> dict:
    if isinstance(method, str):
        method = get_Workplane_methods()[method]
    params = inspect.signature(method).parameters
    kwargs = dict()
    for p in params.values():
        if not p.default is p.empty: 
            kwargs[p.name] = p.default
    return kwargs
    
def get_topo_class_methods(class_name: str) -> Dict[str,Callable]:

    topo_class = getattr(cadquery, class_name)
    return dict((func,getattr(topo_class,func)) for func in dir(topo_class) if callable(getattr(topo_class, func)) and not func.startswith("_"))

def get_cq_topo_classes() -> List[str]:
    """
    Returns all the cadquery topological classes
    """

    return ["Shape", "Compound", "CompSolid", "Solid", "Face", "Wire", "Edge", "Vertex"]

def get_topo_class_args_name(class_name: str, method: str) -> list:
    if isinstance(method, str):
        method = get_topo_class_methods(class_name)[method]
    params = inspect.signature(method).parameters
    args = []
    for p in params.values():
        if p.default is p.empty and p.name != "self": 
            args.append(p.name)
    return args   

def get_topo_class_kwargs_name(class_name: str, method: str) -> OrderedDict:
    if isinstance(method, str):
        method = get_topo_class_methods(class_name)[method]
    params = inspect.signature(method).parameters
    kwargs = OrderedDict()
    for p in params.values():
        if not p.default is p.empty: 
            kwargs[p.name] = p.default
    return kwargs


def get_cq_class_kwargs_name(class_name: str)-> OrderedDict:

    cq_classes = {class_name : obj for (class_name,obj) in inspect.getmembers(cadquery) if inspect.isclass(obj)}
    params = inspect.signature(cq_classes[class_name]).parameters
    kwargs = OrderedDict()
    for p in params.values():
        if not p.default is p.empty: 
            kwargs[p.name] = p.default
    return kwargs


def get_cq_types():
    """
    Returns all the cadquery available types
    """ 
    types = []
    for _, obj in inspect.getmembers(cadquery):
        if inspect.isclass(obj):
            types.append(obj)
    return types
    




if __name__ == "__main__":
    p = determine_type_from_str("'XY'")
    print(p)