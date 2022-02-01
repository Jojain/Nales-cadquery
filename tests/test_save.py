# This file has been generated automatically by Nales
# Don't modify this file unless you know what you are doing
import cadquery as cq
Part1 = cq.Workplane()
Part1 = Part1.box(length = 10,width = 5,height = 5,centered = True,combine = True,clean = True)
Part1 = Part1.circle(radius = 1,forConstruction = False)
Part1 = Part1.cutThruAll(clean = True,taper = 0)

