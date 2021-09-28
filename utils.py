#%%
from cadquery import Workplane
from inspect import signature

def get_Workplane_operations() -> dict:
    """
    This function retrieve all the 'operations' of the Workplane
    object that can be display in the gui
    """
    
    # For now it just gives all the public method of the class
    # but it the future we want to not take in accout things like
    # workplane, transformed, selectors, etc.

    operations = dict((func,getattr(Workplane,func)) for func in dir(Workplane) if callable(getattr(Workplane, func)) and not func.startswith("_"))

    return operations



if __name__ == "__main__":
    print(get_Workplane_operations())