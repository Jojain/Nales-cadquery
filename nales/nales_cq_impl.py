from argparse import ArgumentDefaultsHelpFormatter
from typing import Any, Callable, Dict, List, Literal, Optional
import inspect
from functools import wraps

from PyQt5.QtCore import QObject, pyqtSignal
from ncadquery import Workplane
from ncadquery.cq import VectorLike
from ncadquery.occ_impl.shapes import Shape, Solid, Face, Wire, Edge, Vertex, Compound
from nales.utils import get_method_args_with_names
from collections import namedtuple
from itertools import zip_longest
from nales.widgets.msg_boxs import StdErrorMsgBox


class CQMethodCall:
    ArgData = namedtuple("ArgData", ("name", "value", "type", "optional"))

    def __init__(self, method: Callable, *args, **kwargs) -> None:
        self.name = method.__name__
        self._args = list(args)
        self._kwargs = kwargs
        if method.__name__ == "__init__":
            method = Workplane.__init__
        self.parameters = parameters = inspect.signature(method).parameters
        self.pos_params = [
            p
            for p in parameters.values()
            if p.default is p.empty and p.name not in ("self", "cls")
        ]
        self.kw_params = [p for p in parameters.values() if p.default is not p.empty]

        self._dispatch_args_correctly()

    def _dispatch_args_correctly(self):
        """
        This method makes sure any optional (keyword) parameter that have been called by position
        and without it's keyword is put in the right attribute (self._args or self._kwargs)
        """
        method_params = [
            p for p in self.parameters.values() if p.name not in ("self", "cls")
        ]
        if len(self._args) > len(self.pos_params):
            actually_kwargs = self._args[len(self.pos_params) :]
            self._args = self._args[: len(self.pos_params)]

            kwargs_info = method_params[len(self.pos_params) :]
            for kw, val in zip(kwargs_info, actually_kwargs):
                self._kwargs[kw.name] = val

        for name, val in self._kwargs.copy().items():
            if name in [p.name for p in self.pos_params]:
                self._args.append(self._kwargs.pop(name))

    @property
    def args(self) -> List[ArgData]:
        args = []

        for arg, param in zip(self._args, self.pos_params):
            type_ = param.annotation if param.annotation != param.empty else type(arg)
            args.append(self.ArgData(param.name, arg, type_, False))
        for kwparam in self.kw_params:
            try:
                value = self._kwargs[kwparam.name]
            except KeyError:
                value = kwparam.default
            type_ = (
                kwparam.annotation
                if kwparam.annotation != kwparam.empty
                else type(value)
            )
            args.append(self.ArgData(kwparam.name, value, type_, True))

        return args


class SignalsHandler(type(QObject)):
    def __new__(cls, name, bases, dct):
        dct["on_method_call"] = pyqtSignal(dict)
        dct["on_name_error"] = pyqtSignal(str)

        return super().__new__(cls, name, bases, dct)


class PartWrapper(SignalsHandler):
    @staticmethod
    def _create_cmd(part_name, obj, operation: CQMethodCall):
        cmd = {
            "type": "part_edit",
            "obj_name": part_name,
            "operation": operation,
            "obj": obj,
        }
        return cmd

    @staticmethod
    def _operation_handler(cq_method):
        """
        When called this method wraps the given `cq_method` with all the logic needed to send data through Qt
        It does so by sending a command dict 
        """

        @wraps(cq_method)
        def cq_wrapper(*args, **kwargs):
            # Since a cq_method can have internals calls to other cq_methods, cq_wrapper is called recursively here
            parent_obj = args[0]

            # Checking if the call comes from the console or elswhere (i.e it's an internal call)
            try:
                internal_call = kwargs.pop("internal_call")
            except KeyError:
                internal_call = False

            Part._recursion_nb += 1

            new_obj = cq_method(parent_obj, *args[1:], **kwargs)

            # check that we are in the top level method call and the method is used by the user through the console
            # and that
            if Part._recursion_nb == 1 and not internal_call:
                # remove the Part object (which is the first one) from the args
                operation = CQMethodCall(cq_method, *args[1:], **kwargs)
                cmd = PartWrapper._create_cmd(new_obj._name, new_obj, operation)
                new_obj.on_method_call.emit(cmd)

            Part._recursion_nb -= 1
            return new_obj

        return cq_wrapper

    @staticmethod
    def _wrap_Workplane(dct):
        # Monkey patch every method of Workplane class to retrieve info from calls
        # for method in [method for (name, method) in inspect.getmembers(Workplane) if not (name.startswith("_") or name =="newObject") ]:
        for method in [
            method
            for (name, method) in inspect.getmembers(PatchedWorkplane)
            if not (name.startswith("_") and (name != "val" or name != "vals"))
        ]:
            method = PartWrapper._operation_handler(method)
            dct[method.__name__] = method

        return dct

    def __new__(cls, name, bases, dct):
        PartWrapper._wrap_Workplane(dct)
        return super().__new__(cls, name, bases, dct)


class PatchedWorkplane(Workplane):
    def __init__(self, *args, **kwargs):
        self._name = None
        super().__init__(*args, **kwargs)

    def newObject(self, objlist):
        # patching the transmitting of _name attribute, could be changed directly in cq file since, we need to modify the cq
        # class anyway due to name clash between QObject and Workplane classes.
        __doc__ = super().newObject.__doc__
        new_wp = super().newObject(objlist)
        new_wp._name = self._name

        return new_wp

    def workplane(
        self,
        offset: float = 0.0,
        invert: bool = False,
        centerOption: Literal[
            "CenterOfMass", "ProjectedOrigin", "CenterOfBoundBox"
        ] = "ProjectedOrigin",
        origin: Optional[VectorLike] = None,
    ):
        __doc__ = super().workplane.__doc__
        new_wp = super().workplane(
            offset, invert, centerOption=centerOption, origin=origin
        )
        new_wp._name = self._name
        return new_wp

    # redefines some methods that are used by the app but that shouldn't trigger signals
    def _val(self):
        return super().val()

    def _findSolid(self):
        return super().findSolid()

    def _end(self, pos):
        return super().end(pos)


class Part(PatchedWorkplane, QObject, metaclass=PartWrapper):

    _recursion_nb = 0
    _mw_instance = None  # this fields holds the mainwindow instance and is initialized in the main_window __init__ function
    _names = []

    def __init__(self, *args, name=None, **kwargs):
        QObject.__init__(self)

        # Checking if the call comes from the console or elswhere (i.e it's an internal call)
        try:
            internal_call = kwargs.pop("internal_call")
        except KeyError:
            internal_call = False

        PatchedWorkplane.__init__(self, *args, **kwargs)

        self.on_method_call.connect(lambda ops: self._mw_instance.handle_command(ops))

        if self._recursion_nb == 0:
            if name:
                if name not in Part._names:
                    Part._names.append(name)
                else:
                    raise ValueError(
                        f"The part name : {name} is already taken, delete it or use another name."
                    )

                self._name = name

            else:
                index = 1
                while (auto_name := f"Part{index}") in Part._names:
                    index += 1
                Part._names.append(auto_name)
                self._name = auto_name
            cmd = {
                "type": "new_part",
                "obj_name": self._name,
                "operation": CQMethodCall(self.__init__, *args, **kwargs),
                "obj": self,
            }

            if not internal_call:
                self.on_method_call.emit(cmd)

    @property
    def name(self):
        return self._name


class ShapeWrapper(SignalsHandler):

    _Vertex_methods = [
        method.__func__
        for (name, method) in inspect.getmembers(Vertex)
        if name.startswith("make")
    ]
    _Edge_methods = [
        method.__func__
        for (name, method) in inspect.getmembers(Edge)
        if name.startswith("make")
    ]
    _Wire_methods = [
        method.__func__
        for (name, method) in inspect.getmembers(Wire)
        if name.startswith("make")
    ]
    _Face_methods = [
        method.__func__
        for (name, method) in inspect.getmembers(Face)
        if name.startswith("make")
    ]
    _Solid_methods = [
        method.__func__
        for (name, method) in inspect.getmembers(Solid)
        if name.startswith("make")
    ]
    _Compound_methods = [
        method.__func__
        for (name, method) in inspect.getmembers(Compound)
        if name.startswith("make")
    ]
    _Shape_methods = [
        method.__func__
        for (name, method) in inspect.getmembers(Shape)
        if name.startswith("make")
    ]

    maker_methods = {
        "Vertex": _Vertex_methods,
        "Edge": _Edge_methods,
        "Wire": _Wire_methods,
        "Face": _Face_methods,
        "Solid": _Solid_methods,
        "Compound": _Compound_methods,
        "Shape": _Shape_methods,
    }

    @staticmethod
    def _create_cmd(
        shape_name: str, shape_class, obj: "NalesShape", maker_method: str, args: Dict,
    ):
        cmd = {
            "type": "new_shape",
            "obj_name": shape_name,
            "maker_method": maker_method,
            "obj": obj,
            "shape_class": shape_class,
            "args": args,
        }
        return cmd

    @staticmethod
    def _maker_method_wrapper(class_name: str, maker_method) -> Callable:
        @wraps(maker_method)
        def maker_meth_wrapped(*args, **kwargs):
            name = kwargs.pop("name", None)
            shape_class = globals()[class_name]
            shape = maker_method(
                shape_class, *args, **kwargs
            )  # the first arg is the classname
            shape.name = name
            all_args = list(args)
            all_args.extend([val for val in kwargs.values()])
            named_args = get_method_args_with_names(maker_method, all_args)
            cmd = ShapeWrapper._create_cmd(
                shape._name, shape_class, shape, maker_method, named_args
            )
            shape.on_method_call.emit(cmd)

            return shape

        return maker_meth_wrapped

    @staticmethod
    def _wrap_maker_methods(class_name: str, class_dict: dict) -> dict:
        methods = ShapeWrapper.maker_methods[class_name.lstrip("Nales")]

        for method in methods:
            wrapped_method = ShapeWrapper._maker_method_wrapper(class_name, method)
            class_dict[method.__name__] = wrapped_method

    def __new__(cls, name, bases, dct):
        ShapeWrapper._wrap_maker_methods(name, dct)
        return super().__new__(cls, name, bases, dct)


class NalesShape(QObject, metaclass=ShapeWrapper):

    _mw_instance = None  # this fields holds the mainwindow instance and is initialized in the main_window __init__ function
    _names = []
    on_method_call = pyqtSignal(dict)
    on_name_error = pyqtSignal(str)

    def __init__(self):
        QObject.__init__(self)

        self.on_name_error.connect(lambda msg: StdErrorMsgBox(msg, self._mw_instance))
        self.on_method_call.connect(lambda ops: self._mw_instance.handle_command(ops))

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, __name) -> None:
        if __name:
            self._name = __name
        else:
            index = 1
            while (auto_name := f"Shape{index}") in NalesShape._names:
                index += 1
            NalesShape._names.append(auto_name)
            self._name = auto_name

    @staticmethod
    def _create_cmd(shape_name, shape_obj, maker_method):
        cmd = {
            "type": "new_shape",
            "obj_name": shape_name,
            "maker_method": maker_method,
            "obj": shape_obj,
        }
        return cmd


class NalesVertex(Vertex, NalesShape):
    def __init__(self, *args, **kwargs):
        Vertex.__init__(self, args, **kwargs)
        NalesShape.__init__(self)


class NalesEdge(Edge, NalesShape):
    def __init__(self, *args, **kwargs):
        Edge.__init__(self, args, **kwargs)
        NalesShape.__init__(self)


class NalesWire(Wire, NalesShape):
    def __init__(self, *args, **kwargs):
        Wire.__init__(self, args, **kwargs)
        NalesShape.__init__(self)


class NalesFace(Face, NalesShape):
    def __init__(self, *args, **kwargs):
        Face.__init__(self, args, **kwargs)
        NalesShape.__init__(self)


class NalesSolid(Solid, NalesShape):
    def __init__(self, *args, **kwargs):
        Solid.__init__(self, *args, **kwargs)
        NalesShape.__init__(self)


class NalesCompound(Compound, NalesShape):
    def __init__(self, *args, **kwargs):
        Compound.__init__(self, args, **kwargs)
        NalesShape.__init__(self)


NALES_TYPES = (
    NalesShape,
    NalesCompound,
    NalesSolid,
    NalesFace,
    NalesWire,
    NalesEdge,
    NalesVertex,
    Part,
)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication, QMainWindow
    import sys
    import cadquery as cq

    args = CQMethodCall(cq.Workplane.cylinder, height=5, radius=15).args
    print(args)

    # app = QApplication(sys.argv)
    # mw = QMainWindow()
    # mw.handle_command = lambda x: None
    # NalesShape._mw_instance = mw
    # mw.show()

    # Part.mainwindow = mw
    # p = Part().box(10, 10, 10)
    # a = NalesSolid.makeBox(1, 1, 2)
    # NalesVertex.makeVertex(2, 2, 2)

    #
    # p.on_name_error.connect(lambda msg: StdErrorMsgBox(msg, p.mainwindow))
    # p.on_name_error.emit("This part name is already taken,\ndelete it or use another name.")

