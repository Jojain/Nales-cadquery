# This file has been generated automatically by Nales
# Don't modify this file unless you know what you are doing
import cadquery as cq

#Paramsdef>> 0

#Partdef>> Part1 15 False
Part1 = cq.Workplane(inPlane = "XY", origin = (0, 0, 0), obj = None)
Part1 = Part1.box(length = 47.8, width = 15.8, height = 3.2, centered = True, combine = True, clean = True)
Part1 = Part1.faces(selector = "<Z", tag = None)
Part1 = Part1.shell(thickness = -1.5, kind = "arc")
Part1 = Part1.faces(selector = ">Z", tag = None)
Part1 = Part1.workplane(offset = 0.0, invert = False, centerOption = "ProjectedOrigin", origin = None)
Part1 = Part1.rarray(xSpacing = 8.0, ySpacing = 8.0, xCount = 6, yCount = 2, center = True)
Part1 = Part1.circle(radius = 2.4, forConstruction = False)
Part1 = Part1.extrude(until = 1.8, combine = True, clean = True, both = False, taper = None)
Part1 = Part1.faces(selector = "<Z", tag = None)
Part1 = Part1.workplane(offset = 0.0, invert = True, centerOption = "ProjectedOrigin", origin = None)
Part1 = Part1.rarray(xSpacing = 8.0, ySpacing = 8.0, xCount = 5, yCount = 1, center = True)
Part1 = Part1.circle(radius = 3.25, forConstruction = False)
Part1 = Part1.circle(radius = 2.4, forConstruction = False)
Part1 = Part1.extrude(until = 1.7000000000000002, combine = True, clean = True, both = False, taper = None)

