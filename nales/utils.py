#%%
import inspect
from typing import Callable, Dict, List, Literal, Union
from ncadquery import Workplane
import ncadquery
from inspect import signature
from collections import OrderedDict
import ast


PY_TYPES_TO_AST_NODE = {
    int: ast.Constant,
    float: ast.Constant,
    str: ast.Constant,
    tuple: ast.Tuple,
    list: ast.List,
    bool: ast.Constant,
    set: ast.Set,
}


def sort_args_kwargs(part_cls, method_name: str, mixed_args: list) -> tuple:
    sig = inspect.signature(getattr(part_cls, method_name))

    args = []
    kwargs = {}
    for idx, p in enumerate(
        list(sig.parameters.values())[1:]
    ):  # remove the first param with is self
        if p.default is inspect.Parameter.empty:
            args.append(mixed_args[idx])
        else:
            kwargs[p.name] = mixed_args[idx]
    return args, kwargs


def determine_type_from_str(string: str):

    if len(string) == 0:
        return None
    selector_chars = ("%", "|", ">", "<", "#")
    # if any(char in string for char in selector_chars):
    #     return str

    try:
        node = ast.parse(string).body[0].value
    except SyntaxError:
        # Means the user provided a str without the quotes
        return str

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


def get_Workplane_methods() -> Dict[str, Callable]:
    """
    This function retrieve all the 'operations' of the Workplane
    object that can be display in the gui
    """

    # For now it just gives all the public method of the class
    # but it the future we want to not take in accout things like
    # workplane, transformed, selectors, etc.

    operations = dict(
        (func, getattr(Workplane, func))
        for func in dir(Workplane)
        if callable(getattr(Workplane, func)) and not func.startswith("_")
    )
    operations["Workplane"] = Workplane.__init__

    return operations


def get_method_args_with_names(method: Callable, args: List) -> Dict:
    params = inspect.signature(method).parameters
    named_args = {}
    for p, arg in zip(
        tuple(params.values())[1:], args
    ):  # the first param is `cls` so we get rid of it
        named_args[p.name] = arg
    return named_args


def get_Wp_method_args_name(method: Union[str, Callable]) -> list:
    if isinstance(method, str):
        method = get_Workplane_methods()[method]
    params = inspect.signature(method).parameters
    args = []
    for p in params.values():
        if p.default is p.empty and p.name != "self":
            # if p.name != "self": # TODO Si l'utilisateur renseigne une valeur à un arg par défaut ça bug
            args.append(p.name)
    return args


def get_Wp_method_kwargs(method: Union[str, Callable]) -> dict:
    if isinstance(method, str):
        method = get_Workplane_methods()[method]
    params = inspect.signature(method).parameters
    kwargs = dict()
    for p in params.values():
        if not p.default is p.empty:
            kwargs[p.name] = p.default
    return kwargs


def get_topo_class_methods(class_name: str) -> Dict[str, Callable]:

    topo_class = getattr(ncadquery, class_name)
    return dict(
        (func, getattr(topo_class, func))
        for func in dir(topo_class)
        if callable(getattr(topo_class, func)) and not func.startswith("_")
    )


def get_cq_topo_classes() -> List[str]:
    """
    Returns all the ncadquery topological classes
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


def get_cq_class_kwargs_name(class_name: str) -> OrderedDict:

    cq_classes = {
        class_name: obj
        for (class_name, obj) in inspect.getmembers(ncadquery)
        if inspect.isclass(obj)
    }
    params = inspect.signature(cq_classes[class_name]).parameters
    kwargs = OrderedDict()
    for p in params.values():
        if not p.default is p.empty:
            kwargs[p.name] = p.default
    return kwargs


def get_cq_types():
    """
    Returns all the ncadquery available types
    """
    types = []
    for _, obj in inspect.getmembers(ncadquery):
        if inspect.isclass(obj):
            types.append(obj)
    return types


if __name__ == "__main__":
    p = determine_type_from_str("'XY'")
    print(p)
