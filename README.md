# What it Does
It mirrors and links the shapekeys between 2 objects, so they're always in sync.

In other words:
* If the binded object doesn't have shapekeys the active object has, it'll create shapekeys for the binded object and automatically link them through drivers.
* If shapekeys are deleted, they'll also be deleted in the binded objects.
* If the binded objects have additional shapekeys that are not in the active object, they'll be deleted by default (But there is a toggle to keep them)

# Where to Find it
Properties > Object Properties (Green triangle) > Shapekey Binder

# Caveats
This plugin was mainly made for myself, so keep in mind it might break fairly easily. Here's some stuff i'm aware of:
* Renaming the binded objects could cause problems, so unbind before renaming.
* There may be a bit of slowdown when creating new shapekeys on the active object.
