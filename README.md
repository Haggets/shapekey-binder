# What it Does

It mirrors and links shapekeys between objects, so they're always in sync.

In other words:

- If the target object doesn't have shapekeys the source object has, it'll create them for the target object and automatically link them through drivers.
- If shapekeys are deleted in the source object, they'll also be deleted in the target objects.
- If the target objects have additional shapekeys that are not in the active object, they'll be deleted when binded (Otherwise they can kept by untoggling "Full Shapekey Mirror")

# Where to Find it

Properties > Object Properties (Green triangle) > Shapekey Binder

# Caveats

This plugin was mainly made for myself, so it may have some issues. Here's some stuff i'm aware of:

- There may be a bit of slowdown when creating new shapekeys on the active object.
