# This file has been generated automatically by Nales
# Don't modify this file unless you know what you are doing
import cadquery as cq

#Paramsdef>> 3
param1 = 3 # int
param2 = 1 # int
param3 = "toto" # str

#Partdef>> Part1 3 True
Part1 = cq.Workplane(inPlane = "XY", origin = (0, 0, 0), obj = None)
Part1 = Part1.box(length = param1, width = 10, height = 10, centered = True, combine = True, clean = True)

#Partdef>> Part2 3 False
Part2 = cq.Workplane(inPlane = "XY", origin = (0, 0, 0), obj = None)
Part2 = Part2.box(length = 1, width = 10, height = 1, centered = True, combine = True, clean = True)

#Partdef>> Part3 3 False
Part3 = cq.Workplane(inPlane = "XY", origin = (0, 0, 0), obj = None)
Part3 = Part3.sphere(radius = 3, direct = (0, 0, 1), angle1 = -90, angle2 = 90, angle3 = 360, centered = True, combine = True, clean = True)

#Partdef>> Part6 3 False
Part6 = cq.Workplane(inPlane = "XY", origin = (0, 0, 0), obj = None)
Part6 = Part6.sphere(radius = 2, direct = (0, 0, 1), angle1 = -90, angle2 = 90, angle3 = 360, centered = True, combine = True, clean = True)

#Partdef>> Part4 4 True
Part4 = cq.Workplane(inPlane = "XY", origin = (0, 0, 0), obj = None)
Part4 = Part4.box(length = 1, width = 1, height = 10, centered = True, combine = True, clean = True)
Part4 = Part4.union(toUnion = Part3, clean = True, glue = False, tol = None)

#Partdef>> Part5 4 True
Part5 = cq.Workplane(inPlane = "XY", origin = (0, 0, 0), obj = None)
Part5 = Part5.box(length = 20, width = 1, height = 20, centered = True, combine = True, clean = True)
Part5 = Part5.cut(toCut = Part4, clean = True)

#Partdef>> Part7 4 True
Part7 = cq.Workplane(inPlane = "XY", origin = (0, 0, 0), obj = None)
Part7 = Part7.box(length = 1, width = 1, height = 1, centered = True, combine = True, clean = True)
Part7 = Part7.cut(toCut = Part4, clean = True)

