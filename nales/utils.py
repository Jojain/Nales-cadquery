#%%
import inspect
from typing import Any, Callable, Dict, Iterable, List, Literal, Set, Tuple, Union
from functools import wraps
import ast
import typing

from nales.widgets.msg_boxs import StdErrorMsgBox


def handle_error(func):
    """
    Decorator that handle errors to display them as a MsgBox and avoid app crash
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as exc:
            StdErrorMsgBox(exc.args[0])

    return wrapper


def handle_cmd_error(method):
    """
    Decorator that handle errors to display them as a MsgBox and avoid app crash
    """
    if method.__name__ not in ["redo", "undo"]:
        raise ValueError(f"{method} is not a method of a QUndoCommand")

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            method(self, *args, **kwargs)
        except Exception as exc:
            exc_name = type(exc).__name__
            exc_val = str(exc)
            self.setObsolete(True)
            StdErrorMsgBox([exc_name, exc_val])

    return wrapper


class TypeChecker:
    TYPE_MAPPING = {
        "Tuple": tuple,
        "List": list,
        "Dict": dict,
        "Literal": str,
        "Set": set,
        "Iterable": list,
    }

    def __init__(self, type_) -> None:
        self._type = type_

    def _subtypes(self, type_=None) -> Any:
        checktype = self._type if type_ is None else type_
        origin = typing.get_origin(checktype)

        if origin == Union:
            for arg in typing.get_args(checktype):
                yield arg
        else:
            yield checktype

    def _cast_from_typing(self, type_, value):

        typing_name = getattr(type_, "_name", None)
        if (
            typing_name == "Literal"
            or type_ == str
            or typing.get_origin(type_) == Literal
        ):
            return str(value)

        eval_value = ast.literal_eval(str(value))

        if typing_name in self.TYPE_MAPPING.keys():
            return self.TYPE_MAPPING[typing_name](eval_value)
        else:
            return type_(eval_value)

    def check(self, value: str) -> bool:
        """
        Returns if the input string can be casted in a suitable type
        """
        try:
            self.cast(value)
            return True
        except:
            return False

    def cast(self, value: str) -> Any:
        """
        Cast `value` in the first type that match `self._type`
        """
        for type_ in self._subtypes():
            try:
                return self._cast_from_typing(type_, value)
            except:
                pass

        raise TypeError(
            f"Couldn't cast {value} in any of the types : {[t for t in self._subtypes()]}"
        )


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

    if string.isnumeric():
        return int
    else:
        try:
            float(string)
            return float
        except ValueError:
            return str


def get_method_args_with_names(method: Callable, args: List) -> Dict:
    params = inspect.signature(method).parameters
    named_args = {}
    for p, arg in zip(
        tuple(params.values())[1:], args
    ):  # the first param is `cls` so we get rid of it
        named_args[p.name] = arg
    return named_args


if __name__ == "__main__":
    typ = typing.Iterable[
        typing.Union[typing.Tuple[float, float], typing.Tuple[float, float, float]]
    ]
    tc = TypeChecker(typ)
    print(type(tc.cast("[(5,5,5)]")))
