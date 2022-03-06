# This file has been generated automatically by Nales
# Don't modify this file unless you know what you are doing
import cadquery as cq

#Paramsdef>> 0

#Partdef>> Part1 10 False
Part1 = cq.Workplane(inPlane = "XY", origin = (0, 0, 0), obj = None)
Part1 = Part1.box(length = 30.0, width = 40.0, height = 10.0, centered = True, combine = True, clean = True)
Part1 = Part1.faces(selector = ">Z", tag = None)
Part1 = Part1.workplane(offset = 0.0, invert = False, centerOption = "ProjectedOrigin", origin = None)
Part1 = Part1.hole(diameter = 22.0, depth = None, clean = True)
Part1 = Part1.faces(selector = ">Z", tag = None)
Part1 = Part1.workplane(offset = 0.0, invert = False, centerOption = "ProjectedOrigin", origin = None)
Part1 = Part1.rect(xLen = 22.0, yLen = 32.0, centered = True, forConstruction = True)
Part1 = Part1.vertices(selector = None, tag = None)
Part1 = Part1.cboreHole(diameter = 2.4, cboreDiameter = 4.4, cboreDepth = 2.1, depth = None, clean = True)

