# Python implementation of OCAF library for Nalès

from OCP.TDocStd import TDocStd_Application, TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_Label
import OCP

from OCP.BinDrivers import BinDrivers
from OCP.XmlDrivers import XmlDrivers

from OCP.TDataStd import TDataStd_Integer, TDataStd_Name
from OCP.TDF import TDF_TagSource
from OCP.TPrsStd import TPrsStd_AISViewer, TPrsStd_AISPresentation
from OCP.TNaming import TNaming_NamedShape, TNaming_Builder


# class Document():
#     def __init__(self, binary = True):
#         _storage_format = TCollection_ExtendedString("BinOcaf") if binary is True else TCollection_ExtendedString("XmlOcaf")
#         self._wrapped = TDocStd_Document(_storage_format)
#         self.root_label = self._wrapped.GetData().Root()
#         self.main_label = self._wrapped.Main()


class Application(TDocStd_Application):
    def __init__(self, binary=False):
        super().__init__()
        if binary:
            BinDrivers.DefineFormat_s(self)
            self._file_extension = ".cbf"
            self.doc_format = "BinOcaf"
        else:
            XmlDrivers.DefineFormat_s(self)
            self._file_extension = ".xml"
            self.doc_format = "XmlOcaf"

        self.doc = TDocStd_Document(TCollection_ExtendedString(self.doc_format))

        self.NewDocument(TCollection_ExtendedString(self.doc_format), self.doc)

    def viewer_redraw(self):
        """
        Redraw the viewer (refresh the view even if the user isn't moving the view)
        """
        self._pres_viewer.Update()

    def init_viewer_presentation(self, context: OCP.AIS.AIS_InteractiveContext):
        self._pres_viewer = TPrsStd_AISViewer.New_s(self.doc.GetData().Root(), context)

    def save_as(self, path: str):
        """
        Saves the application document in the specified path.
        The file extension is automatically added by the :Application:
        """
        path += self._file_extension
        status = self.SaveAs(self.doc, TCollection_ExtendedString(path))

        if status != OCP.PCDM.PCDM_SS_OK:
            self.Close(self.doc)
            raise Exception("The document could not be saved !")

    def close(self):
        self.Close(self.document)


# class Label():
#     def __init__(self, parent: "Label" = None, attributes: list = []):
#         if parent :
#             self.wrapped = TDF_TagSource.NewChild_s(parent.wrapped)
#         else:
#             self.wrapped = TDF_Label()

#         self.attributes = attributes

#     def new_child(self):
#         return Label.wrap(TDF_TagSource.NewChild(self))

#     def get_root(self):
#         return Label.wrap(self.wrapped.Root())

#     def find_by_name(self, name: str, first_level = True):
#         """
#         Finds the
#         No labels
#         """
#         pass


#     @property
#     def tag(self):
#         return Label.wrap(self.wrapped.Tag())

#     @property
#     def father(self):
#         return Label.wrap(self.wrapped.Father())

#     # Label attributes

#     @property
#     def name(self):
#         return self._name

#     @name.setter
#     def name(self, value: str):
#         self._name = value
#         TDataStd_Name.Set_s(self.wrapped, TCollection_ExtendedString(value))


#     @classmethod
#     def wrap(self, label: TDF_Label):
#         wrapped_label = Label()
#         wrapped_label.wrapped = label
#         return wrapped_label


# class Part(Label):
#     def __init__(self, parent : Label, shape):
#         super().__init__(parent)
#         self.workplane = None
#         self.name = "part" # name of the label and of the workplane should be the same but are two different entities

#         bldr = TNaming_Builder(self.wrapped)
#         bldr.Generated(shape.wrapped)

#         named_shape = bldr.NamedShape()
#         self.wrapped.FindAttribute(TNaming_NamedShape.GetID_s(), named_shape)

#         self.ais_shape = TPrsStd_AISPresentation.Set_s(named_shape)
#         self.ais_shape.Display(update=True)

#     @property
#     def vshape(self):
#         pass

# class Feature(Label):
#     def __init__(self, parent : Label, shape: Shape):
#         super().__init__(parent)
#         self.name = "feature"

#         bldr = TNaming_Builder(self.wrapped)
#         bldr.Generated(shape.wrapped)

#         named_shape = bldr.NamedShape()
#         self.wrapped.FindAttribute(TNaming_NamedShape.GetID_s(), named_shape)

#         ais_shape = TPrsStd_AISPresentation.Set_s(named_shape)
#         ais_shape.Display(update=True)


# Pour référence :
def make_AIS(obj, options={}):

    shape = None

    if isinstance(obj, cq.Assembly):
        label, shape = toCAF(obj)
        ais = XCAFPrs_AISObject(label)
    elif isinstance(obj, AIS_Shape):
        ais = obj
    else:
        # shape = to_compound(obj)
        ais = AIS_ColoredShape(shape.wrapped)

    if "alpha" in options:
        ais.SetTransparency(options["alpha"])
    if "color" in options:
        ais.SetColor(to_occ_color(options["color"]))
    if "rgba" in options:
        r, g, b, a = options["rgba"]
        ais.SetColor(to_occ_color((r, g, b)))
        ais.SetTransparency(a)

    return ais, shape

