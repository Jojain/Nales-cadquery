# This file has been generated automatically by Nales
# Don't modify this file unless you know what you are doing
import cadquery as cq

#Paramsdef>> 0

#Partdef>> test_part 5 False
test_part = cq.Workplane(inPlane = "XY", origin = (0, 0, 0), obj = None)
test_part = test_part.box(length = 10, width = 10, height = 10, centered = True, combine = True, clean = True)
test_part = test_part.faces(selector = ">Z", tag = None)
test_part = test_part.workplane(offset = 0.0, invert = False, centerOption = "ProjectedOrigin", origin = None)
test_part = test_part.hole(diameter = 1.5, depth = None, clean = True)

