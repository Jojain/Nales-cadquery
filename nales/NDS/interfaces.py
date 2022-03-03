from nales.utils import TypeChecker
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Union,
)
import typing
from PyQt5.QtCore import QPersistentModelIndex, Qt
from ncadquery import Workplane

from OCP.TDataStd import TDataStd_Name
from OCP.TPrsStd import TPrsStd_AISPresentation
from ncadquery.occ_impl.shapes import Shape
from OCP.AIS import AIS_InteractiveObject, AIS_ColoredShape
from OCP.TNaming import TNaming_Builder, TNaming_NamedShape
from nales.NDS.NOCAF import Application
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.TDF import TDF_Label, TDF_TagSource
from OCP.TCollection import TCollection_ExtendedString
from OCP.TopoDS import TopoDS_Shape
from OCP.Quantity import Quantity_NameOfColor
import typeguard

from nales.nales_cq_impl import (
    NALES_TYPES,
    CQMethodCall,
    NalesCompound,
    NalesEdge,
    NalesFace,
    NalesShape,
    NalesSolid,
    NalesVertex,
    NalesWire,
    Part,
)

from nales.widgets.msg_boxs import StdErrorMsgBox


class NNode:
    def __init__(self, name=None, parent=None):
        self._parent = parent
        self._columns_nb = 1
        self._childs = []

        if parent:
            self._row = len(parent._childs)
            parent._childs.append(self)
            parent._columns_nb = max(self.column, parent.column)
            self._label = TDF_TagSource.NewChild_s(parent._label)
            self._name = name
            TDataStd_Name.Set_s(self._label, TCollection_ExtendedString(name))
        else:
            self._label = TDF_Label()
            self._name = "root"
            self._row = 0

    def walk(self, node: "NNode" = None) -> "NNode":
        """
        Walks all the node starting from 'node'
        If 'node' is None, starts from the called node
        """
        base_node = node if node else self

        yield base_node

        for child in base_node.childs:
            yield from self.walk(child)

    def find(self, node_name: str, node_type=None) -> "NNode" or None:
        for node in self.walk():
            if node.name == node_name:
                if node_type:
                    if isinstance(node, node_type):
                        return node
                else:
                    return node

    def data(self, column):
        if column >= 0 and column < len(self._data):
            return self._data[column]

    @property
    def column(self):
        return self._columns_nb

    def child_count(self):
        return len(self._childs)

    def child(self, row) -> "NNode":
        if row >= 0 and row < self.child_count():
            return self._childs[row]

    def has_children(self):
        if len(self._childs) != 0:
            return True
        else:
            return False

    @property
    def parent(self):
        return self._parent

    @property
    def childs(self):
        return self._childs

    @childs.setter
    def childs(self, new_childs):
        self._childs = new_childs

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def root_node(self):
        root = self.parent
        while True:
            if root.parent:
                root = root.parent
            else:
                return root

    @property
    def row(self):
        return self._row


class NPart(NNode):
    def __init__(self, name: str, part: Workplane, parent):
        super().__init__(name, parent=parent)
        self.visible = True
        self._solid = TopoDS_Shape()
        self._active_shape = None

        self.display()

    @property
    def part(self):
        return self.childs[-1].part_obj

    def _update_display_shapes(self):
        try:
            solid = self.part._findSolid().wrapped
        except ValueError:
            solid = TopoDS_Shape()

        self._solid = solid

        if active_shape := self.part._val().wrapped is solid:
            self._active_shape = None
        else:
            self._active_shape = active_shape

    def hide(self):

        self.visible = False
        self.ais_shape.Erase(remove=True)
        self.root_node._viewer.Update()

    def display(self, update=False):
        """
        Builds the display object and attach it to the OCAF tree
        """

        if update:
            self.ais_shape.Erase(remove=True)
            self._update_display_shapes()
            self.root_node._viewer.Update()

        self.bldr = TNaming_Builder(self._label)  # _label is  TDF_Label
        self.bldr.Generated(self._solid)

        named_shape = self.bldr.NamedShape()
        self.ais_shape = TPrsStd_AISPresentation.Set_s(named_shape)

        self.ais_shape.Display(update=True)
        self.root_node._viewer.Update()

        self.visible = True

    def update(self):
        """
        When called this method rebuild the entire Part, by calling each child Operation
        """
        child_ops = self.childs
        for pos, child_op in enumerate(child_ops):
            child_op.update(pos)

    def remove_operation(self, row: int):
        """
        Remove an operation from the operation tree
        """

        ops: List[NOperation] = self.childs
        ops.pop(row)
        ops[row - 1].update_from_node()


class NShape(NNode):
    def __init__(self, name, cq_shape, parent: NNode):

        self._occt_shape = shape = cq_shape.wrapped
        self.shape = cq_shape
        self.visible = True
        super().__init__(name, parent=parent)

        self.bldr = TNaming_Builder(self._label)  # _label is  TDF_Label
        self.bldr.Generated(shape)

        named_shape = self.bldr.NamedShape()
        self._label.FindAttribute(TNaming_NamedShape.GetID_s(), named_shape)

        self.ais_shape = TPrsStd_AISPresentation.Set_s(named_shape)
        self.ais_shape.SetTransparency(0.5)
        self.ais_shape.SetColor(Quantity_NameOfColor.Quantity_NOC_ALICEBLUE)
        self.ais_shape.Display(update=True)

    def hide(self):
        self.visible = False
        self.ais_shape.Erase()
        self.root_node._viewer.Update()

    def display(self, update=False):
        """
        Builds the display object and attach it to the OCAF tree
        """
        if update:
            self.ais_shape.Erase(remove=True)
            self.root_node._viewer.Update()
        self.bldr = TNaming_Builder(self._label)  # _label is  TDF_Label
        self.bldr.Generated(self._occt_shape)

        named_shape = self.bldr.NamedShape()
        self._label.FindAttribute(TNaming_NamedShape.GetID_s(), named_shape)

        self.ais_shape = TPrsStd_AISPresentation.Set_s(named_shape)
        self.ais_shape.SetTransparency(0.5)
        self.ais_shape.SetColor(Quantity_NameOfColor.Quantity_NOC_ALICEBLUE)
        self.ais_shape.Display(update=True)
        self.root_node._viewer.Update()

        self.visible = True

    def update(self):
        """
        Update the shape object
        """
        self._occt_shape = self.shape.wrapped
        self.display(True)


class NShapeOperation(NNode):
    def __init__(self, maker_method: Callable, shape_class, parent=None):
        super().__init__(maker_method.__name__, parent)
        self.maker_method = maker_method
        self.shape_class = shape_class

    def update(self) -> None:
        args = [child.value for child in self.childs]
        self.parent.shape = self.maker_method(self.shape_class, *args)
        self.parent.update()


class NOperation(NNode):
    def __init__(
        self, method_name: str, part_obj: Part, parent: NNode, operation: CQMethodCall
    ):
        super().__init__(method_name, parent=parent)
        self.part_obj = part_obj
        self.operation = operation
        self.method = getattr(part_obj, method_name).__func__

        if method_name == "Workplane":
            self._root_operation = True
        else:
            self._root_operation = False

    def update_from_node(self):
        """
        Update the Part from this node
        It recomputes every operation from this node to the end
        """
        ops: List[NOperation] = self.parent.childs[self.row :]
        for op in ops:
            op.update()
        self.parent.display(update=True)

    def _update_init_part(self):
        """
        This method is called when the user try to update __init__ method arguments
        There is a special handling because it is a bit different from the regular methods
        """
        args = [
            child.value if not child.is_linked("obj") else child.linked_obj
            for child in self.childs
        ]
        try:
            self.method(self.part_obj, *args, internal_call=True)
        except Exception as exc:
            StdErrorMsgBox(repr(exc))

    def update(self) -> bool:
        """
        Update the CQ objects stack from param modification in the GUI view
        """
        # Special handling of __init__ method
        if self.row == 0:
            self._update_init_part()
            return True

        previous_operations: List[NOperation] = self.parent.childs[: self.row]
        old_part_obj = previous_operations[-1].part_obj

        args = [
            child.value if not child.is_linked("obj") else child.linked_obj
            for child in self.childs
        ]

        try:

            self.part_obj = self.method(old_part_obj, *args, internal_call=True)
            return True
        except ValueError as exc:  # we update parent operations until pending wires have reset
            if exc.args[0] == "No pending wires present":
                tried_updates = [self]
                # recursively call parent ops and store all the failed updates to update them again afterwards
                while (tried_update := previous_operations[-1].update()) is False:
                    tried_updates.append(tried_update)
                for tried_update in tried_updates:
                    tried_update.update()

            else:
                StdErrorMsgBox(repr(exc))
            return False
        except Exception as exc:
            StdErrorMsgBox(repr(exc))
            return False

    def _restore_pending_wires(self):
        index = 2
        previous_ops = self.parent.childs[: self._row]
        while len(self.parent.part.ctx.pendingWires) == 0:
            op = previous_ops[-index]
            op.update(len(previous_ops) - op._row)
            index += 1


class NShapeArgument(NNode):
    def __init__(self, name=None, parent=None):
        super().__init__(name, parent)


class NArgument(NNode):
    """
    The underlying data of an Argument is as follow :
    name : cq argument name
    value : value
    linked_param : the name of the parameter linked to this arg, None if not connected to any
    type: value type : a voir si je garde ca
    If the Argument is linked to a Parameter, the Parameter name is displayed
    """

    def __init__(self, arg_name: str, value, arg_type, parent: NNode, kwarg=False):
        super().__init__(arg_name, parent=parent)

        self._name = arg_name
        if type(value) == str and (value in self.root_node.console_namespace.keys()):
            self._type = arg_type
            self._value = self.root_node.console_namespace[value]
        else:
            self._type = arg_type
            self._value = value

        self._typechecker = TypeChecker(arg_type)

        self._kwarg = kwarg  # Boolean indicating if the arg is a kwarg or not

        self._linked_param = None
        self._linked_nobj_idx: QPersistentModelIndex = None

        self._param_name_pidx = None
        self._param_value_pidx = None

    def link(
        self, by: Literal["param", "obj"], value: Union[Tuple, QPersistentModelIndex]
    ):
        """
        Link this parameter to an object in available in the data model
        """

        if by == "param":
            raw_val = value[1]

            if not self.is_type_compatible(raw_val):
                raise TypeError("Couldn't link the param")

            self._linked_param = value[0]
            self._value = value[1]
            self._param_name_pidx = value[2]
            self._param_value_pidx = value[3]
        else:
            self._linked_nobj_idx = value

    def unlink(self):
        self._linked_nobj_idx = None
        self._linked_param = None
        self._param_name_pidx = None
        self._param_value_pidx = None

    def is_kwarg(self):
        return self._kwarg

    def is_linked(self, by: str = None):
        if by == "obj":
            return True if self._linked_nobj_idx else False
        elif by == "param":
            return True if self._linked_param else False

        elif by is None:
            if self._linked_param or self._linked_nobj_idx:
                return True
            else:
                return False
        else:
            raise ValueError("Argument 'by' must be either 'obj' or 'param'")

    def is_optional_type(self) -> bool:
        """
        Indicates if the NArgument is optional, i.e the function signature looks something like :
        method(nargument:Union[float,None] = None) or method(nargument:Optional[float] = None)
        """
        if self.is_kwarg():
            origin = typing.get_origin(self._type)
            if origin == Optional:
                return True
            if origin == Union:
                for allowed_type in typing.get_args(self._type):
                    if allowed_type == type(None):
                        return True
                return False
            else:
                return False
        else:
            return False

    def is_literal_type(self) -> bool:
        origin = typing.get_origin(self.type)
        if self.type == str or origin == Literal:
            return True
        if origin == Union:
            possible_types = typing.get_args(self.type)
            for possible_type in possible_types:
                if possible_type == str or possible_type == Literal:
                    return True
        return False

    def is_type_compatible(self, value: str) -> bool:
        return self._typechecker.check(value)

    def _cast(self, value: Any):

        if type(value) == self._type:
            return value
        return self._typechecker.cast(value)

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def linked_param(self):
        if self.is_linked():
            return self._linked_param
        else:
            raise ValueError("This argument is not linked to a param")

    @property
    def linked_obj(self):
        if self.is_linked(by="obj"):
            linked_node = self._linked_nobj_idx.data(Qt.EditRole)
            if hasattr(linked_node, "part"):
                return linked_node.part
            elif hasattr(linked_node, "shape"):
                return linked_node.shape
            else:
                raise NotImplementedError(
                    "This argument is linked to a object that is not supported yet"
                )

        else:
            raise ValueError("This argument is not linked to an object")

    @property
    def columns_nb(self):
        return 1

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def value(self):
        if self.is_optional_type() and self._value is None:
            return None
        if self.is_linked(by="param"):
            return self._cast(self._param_value_pidx.data())
        elif self.is_linked(by="obj"):
            return self._linked_nobj_idx.data(Qt.EditRole).name
        else:
            return self._cast(self._value)

    @value.setter
    def value(self, value):
        self._value = value

    @property
    def linked_param(self):
        return self._linked_param

