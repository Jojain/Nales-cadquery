from typing import List, Literal, Optional
import cadquery as cq
import inspect
from functools import wraps

from PyQt5.QtCore import QObject, pyqtSignal
from cadquery import Workplane
from cadquery.cq import VectorLike, _selectShapes
from cadquery.occ_impl.geom import Plane, Vector
from cadquery.occ_impl.shapes import Face, Shape
from utils import get_Wp_method_kwargs
from copy import copy


from widgets.msg_boxs import StdErrorMsgBox







class PartSignalsHandler(type(QObject)):
    def __new__(cls, name, bases, dct):  
        dct['on_method_call'] = pyqtSignal(dict)
        dct['on_name_error'] = pyqtSignal(str)

        return super().__new__(cls, name, bases, dct)

class PartWrapper(PartSignalsHandler):
    @staticmethod
    def _create_cmd(part_name, obj, operations):
        cmd={"type":"part_edit", "obj_name":part_name, "operations":operations, "obj":obj}
        return cmd

    @staticmethod
    def _operation_handler(cq_method):
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

            if Part._recursion_nb == 1 and not internal_call: # we are in the top level method call and the method is used by the user through the console
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
        for method in [method for (name, method) in inspect.getmembers(PatchedWorkplane) if not (name.startswith("_") and (name != "val" or name !="vals")) ]:
            method = PartWrapper._operation_handler(method)
            dct[method.__name__] = method

        return dct

    def __new__(cls, name, bases, dct):
        PartWrapper._wrap_Workplane(dct)
        return super().__new__(cls, name, bases, dct) 

class PatchedWorkplane(Workplane):
    _name = None
    def __init__(self,*args, **kwargs):
        super().__init__(*args,**kwargs)

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
        new_wp = super().workplane(offset, invert, centerOption=centerOption, origin=origin)
        new_wp._name = self._name
        return new_wp
        
    # redefines some methods that are used by the app but that shouldn't trigger signals
    def _val(self):
        return super().val()

    def _findSolid(self):
        return super().findSolid()
    def _end(self,pos):
        return super().end(pos)


class Part(PatchedWorkplane,QObject,metaclass=PartWrapper):

    
    _recursion_nb = 0
    _mw_instance = None # this fields holds the mainwindow instance and is initialized in the main_window __init__ function
    _names = []

    def __init__(self, *args, name = None,**kwargs): 
        QObject.__init__(self)
        PatchedWorkplane.__init__(self, *args, **kwargs)          

        self.on_name_error.connect(lambda msg: StdErrorMsgBox(msg, self._mw_instance))
        self.on_method_call.connect(lambda ops: self._mw_instance.handle_command(ops))

        if self._recursion_nb == 0:
            if name:
                if name not in Part._names:
                    Part._names.append(name)
                else:
                    self.on_name_error.emit("This part name is already taken,\ndelete it or use another name.")
                    return
                self._name = name

            else:
                index = 1           
                while (auto_name:=f"Part{index}") in Part._names:
                    index+=1
                Part._names.append(auto_name)
                self._name = auto_name
            cmd={"type":"new_part", "obj_name":self._name, "operations":{}, "obj":self}
            self.on_method_call.emit(cmd)


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




