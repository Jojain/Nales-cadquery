# Nales

Nales is a GUI CAD application that aims to bring full interactivity to [CadQuery](https://github.com/CadQuery/cadquery/blob/master/README.md)

It is however still a work in progress and a lot of things are still bugged / not implemented


![Nales](./docs/readme_img_presentation.PNG)

## What does it bring more than plain CadQuery ?

If you have used CadQuery and felt annoyed by :
- The time spent rerendering your whole model when you change a small parameter value
- The lack of visualisation tools, like clipping planes, measurements tools, etc.
- Not having a GUI to display nicely what you are building

Then you might be interested by Nales which aims to solve all of these points and more.

## Roadmap

There is a lot of things planned but not so much time to develop, however here is a list of what is expected to be in Nales in the near future:

- Support for Sketch and Assemblies
- Allow function creation/edition through the GUI
- Allow editing of color / alpha for all shapes displayed in the viewer
- Clipping planes
- Measurements tools
- Code synthesis through the GUI (Selector synthesis, Assembly constraint synthesis, etc)

There is still a lot of idea that could be implemented but giving how the CadQuery is at this moment it may be difficult to implement some of them (like bringing full GUI handling of model creation), roadmap is allowed to evolve as the project takes shape.

## Installation 

To install Nales you have to first install CadQuery :
[CadQuery Installation](https://github.com/CadQuery/cadquery#getting-started) 

Then clone this repo and run 
`python setup.py install`
