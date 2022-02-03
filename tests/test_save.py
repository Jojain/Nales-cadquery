# This file has been generated automatically by Nales
# Don't modify this file unless you know what you are doing
import cadquery as cq

#Paramdef>> 2param1 = 1
ouioui = 10
#Partdef>> Part1 4 False
Part1 = cq.Workplane()
Part1 = Part1.box(length = 10,width = 5,height = 5,centered = True,combine = True,clean = True)
Part1 = Part1.rect(xLen = 2,yLen = 1,centered = True,forConstruction = False)
Part1 = Part1.extrude(distance = 15,combine = True,clean = True,both = False,taper = None)

