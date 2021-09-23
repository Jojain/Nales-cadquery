from NOCAF import *

from interfaces import Part

app = Application(binary=False)

app.document.main_label = 199

part1 = Part(app.document.main_label)

app.save_as("test2")
