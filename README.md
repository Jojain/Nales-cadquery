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

:warning: **Nales is currently barely usable, expect a lot of issues/crash so beware of what you are doing**

## Roadmap

There is a lot of things planned but not so much time to develop, however here is a list of what is expected to be in Nales in the near future:

- Support for Sketch and Assemblies
- Allow function creation/edition through the GUI
- Allow editing of color / alpha for all shapes displayed in the viewer
- Clipping planes
- Measurements tools
- Code synthesis through the GUI (Selector synthesis, Assembly constraint synthesis, etc)
- And much more (you can propose improvements you would like to see)

Roadmap is allowed to evolve as the project takes shape, any idea or contribution is welcome.

## Installation 

You will need Anaconda (or miniconda) to install Nales 
([Miniconda installation guide](https://docs.conda.io/en/latest/miniconda.html)).

First create a conda env and activate it

```
conda create -n nales
conda activate nales
```

Clone this repo somewhere.


Then in the top level repo run (it will install all the needed dependencies required to run Nales): 

```
conda env update --file environment.yml -n nales
```

Then install nales
```
python setup.py install
```

You should now be able to launch nales by running the `run_nales.py` script available in the scripts folder

```
python run_nales.py
```

## How to use Nales ?

You can type cadquery code in the console and that will directly populate the tree view on the left.

Note that you don't have to import any Cadquery related libraries, everything is already available in the Nales console. For now the console comes loaded with these classes :

- Shape
- Vertex
- Edge
- Wire 
- Face 
- Solid
- Compound
- Part 
- nales

All the topological classes are wrappers around the Cadquery ones, so you can use them as you would use Cadquery ones.

The `Part` class is a wrapper around the Workplane class of Cadquery that handles GUI stuff. (There is also `Workplane` available which is an alias for `Part`)

Finally the `nales` namespace provide an API of nales internals, even if it not really the case yet, the goal is to make all the GUI actions available from code within the `nales` namespace. 
Type `help(nales)` to view all the actions already available.

You can also try out  and load the [Examples](./examples/). (which are borrowed from the CQ repo):


## Shortcuts

There is already some shortcuts available for you to use :
- ctrl+z / ctrl+y -> undo / redo
- f -> fit the view of the viewer to the shape (click in the tree view to loose console focus)
