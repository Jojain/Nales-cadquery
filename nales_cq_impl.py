from typing import List, Literal, Optional
import inspect
from functools import wraps

from PyQt5.QtCore import QObject, pyqtSignal
from cadquery import Workplane
from cadquery.cq import VectorLike, _selectShapes
from cadquery.occ_impl.geom import Plane, Vector
from cadquery.occ_impl.shapes import Shape, Solid, Face, Wire, Edge, Vertex
from utils import get_Wp_method_kwargs


from widgets.msg_boxs import StdErrorMsgBox


class SignalsHandler(type(QObject)):
    def __new__(cls, name, bases, dct):
        dct["on_method_call"] = pyqtSignal(dict)
        dct["on_name_error"] = pyqtSignal(str)

        return super().__new__(cls, name, bases, dct)


class PartWrapper(SignalsHandler):
    @staticmethod
    def _create_cmd(part_name, obj, operations):
        cmd = {
            "type": "part_edit",
            "obj_name": part_name,
            "operations": operations,
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

            try:
                internal_call = kwargs.pop("internal_call")
            except KeyError:
                internal_call = False

            Part._recursion_nb += 1

            new_obj = cq_method(parent_obj, *args[1:], **kwargs)

            if (
                Part._recursion_nb == 1 and not internal_call
            ):  # we are in the top level method call and the method is used by the user through the console
                operations = {}
                default_kwargs = get_Wp_method_kwargs(cq_method.__name__)
                if kwargs:
                    for kwarg, val in kwargs.items():
                        default_kwargs[kwarg] = val

                operations["name"] = cq_method.__name__
                operations["parameters"] = ([arg for arg in args[1:]], default_kwargs)
                cmd = PartWrapper._create_cmd(new_obj._name, new_obj, operations)
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
    _name = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def newObject(self, objlist):
        # patching the transmitting of _name attribute, could be changed directly in cq file since, we need to modify the cq
        # class anyway due to name clash between QObject and Workplane classes.
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
        """
        Creates a new 2D workplane, located relative to the first face on the stack.

        :param offset:  offset for the workplane in its normal direction . Default
        :param invert:  invert the normal direction from that of the face.
        :param centerOption: how local origin of workplane is determined.
        :param origin: origin for plane center, requires 'ProjectedOrigin' centerOption.
        :type offset: float or None=0.0
        :type invert: boolean or None=False
        :type centerOption: string or None='ProjectedOrigin'
        :type origin: Vector or None
        :rtype: Workplane object 

        The first element on the stack must be a face, a set of
        co-planar faces or a vertex.  If a vertex, then the parent
        item on the chain immediately before the vertex must be a
        face.

        The result will be a 2D working plane
        with a new coordinate system set up as follows:

           * The centerOption parameter sets how the center is defined.
             Options are 'CenterOfMass', 'CenterOfBoundBox', or 'ProjectedOrigin'.
             'CenterOfMass' and 'CenterOfBoundBox' are in relation to the selected
             face(s) or vertex (vertices). 'ProjectedOrigin' uses by default the current origin
             or the optional origin parameter (if specified) and projects it onto the plane
             defined by the selected face(s).
           * The Z direction will be the normal of the face,computed
             at the center point.
           * The X direction will be parallel to the x-y plane. If the workplane is  parallel to
             the global x-y plane, the x direction of the workplane will co-incide with the
             global x direction.

        Most commonly, the selected face will be planar, and the workplane lies in the same plane
        of the face ( IE, offset=0).  Occasionally, it is useful to define a face offset from
        an existing surface, and even more rarely to define a workplane based on a face that is
        not planar.
        """
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
        PatchedWorkplane.__init__(self, *args, **kwargs)

        self.on_name_error.connect(lambda msg: StdErrorMsgBox(msg, self._mw_instance))
        self.on_method_call.connect(lambda ops: self._mw_instance.handle_command(ops))

        if self._recursion_nb == 0:
            if name:
                if name not in Part._names:
                    Part._names.append(name)
                else:
                    self.on_name_error.emit(
                        "This part name is already taken,\ndelete it or use another name."
                    )
                    return
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
                "operations": {},
                "obj": self,
            }
            self.on_method_call.emit(cmd)


class NalesShape(Shape, QObject, metaclass=SignalsHandler):

    _mw_instance = None  # this fields holds the mainwindow instance and is initialized in the main_window __init__ function
    _names = []

    def __init__(self, obj, name: str = None):
        QObject.__init__(self)
        Shape.__init__(self, obj)

        self.on_name_error.connect(lambda msg: StdErrorMsgBox(msg, self._mw_instance))
        self.on_method_call.connect(lambda ops: self._mw_instance.handle_command(ops))

        if name:
            if name not in Shape._names:
                Shape._names.append(name)
            else:
                self.on_name_error.emit(
                    "This Shape name is already taken,\ndelete it or use another name."
                )
                return
            self._name = name

        else:
            index = 1
            while (auto_name := f"Shape{index}") in Shape._names:
                index += 1
            Shape._names.append(auto_name)
            self._name = auto_name
        cmd = {
            "type": "new_shape",
            "obj_name": self._name,
            "maker_method": {},
            "obj": self,
        }
        self.on_method_call.emit(cmd)

    @staticmethod
    def _wrap_maker_methods():
        """
        Wrap all the maker methods of the class to add Qt sending data logic
        When the method is called from the console, it populate the treeview and NModel directly
        """

        for method in [
            method for (name, method) in inspect.getmembers(__class__) if "make" in name
        ]:
            method = __class__._maker_method_wrapper(method)
            __dict__[method.__name__] = method

    @staticmethod
    def _maker_method_wrapper(maker_method):
        @wraps(maker_method)
        def cq_wrapper(*args, **kwargs):
            shape = maker_method(*args, **kwargs)
            cmd = Shape._create_cmd(shape._name, shape, maker_method)
            shape.on_method_call.emit(cmd)

            return shape

        return cq_wrapper

    @staticmethod
    def _create_cmd(shape_name, shape_obj, maker_method):
        cmd = {
            "type": "new_shape",
            "obj_name": shape_name,
            "maker_method": maker_method,
            "obj": shape_obj,
        }
        return cmd


class NalesVertex(NalesShape, Vertex):
    __dict__ = Vertex.__dict__

    NalesShape._wrap_maker_methods()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication, QMainWindow
    import sys

    app = QApplication(sys.argv)
    mw = QMainWindow()
    mw.show()

    Part.mainwindow = mw
    p = NalesVertex
    print(type(p))
    # p.on_name_error.connect(lambda msg: StdErrorMsgBox(msg, p.mainwindow))
    # p.on_name_error.emit("This part name is already taken,\ndelete it or use another name.")

