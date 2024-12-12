import bpy
from bpy.app.handlers import persistent
from bpy.types import FCurve, Key, Object, ShapeKey

bl_info = {
    "name": "Shapekey Binder",
    "author": "Haggets",
    "version": (1, 0, 1),
    "blender": (4, 1, 0),
    "description": "Allows shapekeys of other objects to closely match the active object's shapekeys",
    "category": "System",
}


# region Parameters
class SP_parameters(bpy.types.PropertyGroup):
    full_mirror: bpy.props.BoolProperty(
        name="Full Shapekey Mirroring",
        description="Deletes shapekeys from the binded object if they aren't in the active object",
        default=True,
    )


# endregion


# region Main Function
@persistent
def bind_update(self, context):
    if not (binded_objects := get_binded_objects()):
        return

    active_object = bpy.context.object

    for target_object in binded_objects:
        if active_object == target_object:
            continue
        source_object: Object = target_object.data.get("sp_binded_object")
        if not source_object:
            continue

        if not getattr(source_object.data, "shape_keys"):
            continue
        # Adds a shapekey if one doesn't exist already
        if not getattr(target_object.data, "shape_keys"):
            target_object.shape_key_add(name="Basis", from_mix=False)

        mirror_shape_keys(source_object, target_object)
        remove_leftover_shape_keys(source_object, target_object)
        mirror_shape_key_positions(source_object, target_object)
        mirror_shape_key_parameters(source_object, target_object)


# endregion


# region Utilities
def get_binded_objects() -> list[Object]:
    binded_objects = []
    for object in bpy.data.objects:
        if not object.data:
            continue
        if not object.data.get("sp_binded_object"):
            continue
        if binded_objects.count(object):
            continue

        binded_objects.append(object)

    return binded_objects


def get_active_shape_key_index(source_object: Object, target_object: Object):
    index = target_object.data.shape_keys.key_blocks.find(
        source_object.active_shape_key.name
    )
    return index


def mirror_shape_key_parameters(source_object: Object, target_object: Object):
    target_object.show_only_shape_key = source_object.show_only_shape_key
    target_object.active_shape_key_index = get_active_shape_key_index(
        source_object, target_object
    )


def mirror_shape_keys(source_object: Object, target_object: Object):
    source_shape_keys = source_object.data.shape_keys
    target_shape_keys = target_object.data.shape_keys
    target_drivers = target_shape_keys.animation_data.drivers

    # Creates new shapekeys from the base object onto the binded object
    for base_key in source_shape_keys.key_blocks:
        if not (binded_key := target_shape_keys.key_blocks.get(base_key.name)):
            binded_key = target_object.shape_key_add(name=base_key.name, from_mix=False)

        if not getattr(target_shape_keys, "animation_data"):
            target_shape_keys.animation_data_create()

        # Links the shapekey to a driver if no driver is found
        if target_drivers.find(f'key_blocks["{binded_key.name}"].value'):
            continue

        driver = binded_key.driver_add("value").driver
        driver.expression = "sb_bind"
        if var := driver.variables.get("sb_bind"):
            driver.variables.remove(var)

        var = driver.variables.new()
        var.name = "sb_bind"
        target = var.targets[0]
        target.id_type = "KEY"
        target.id = source_shape_keys
        target.data_path = 'key_blocks["{}"].value'.format(binded_key.name)


def remove_leftover_shape_keys(source_object: Object, target_object: Object):
    SPPARAMETERS = source_object.data.spparameters
    source_shape_keys = source_object.data.shape_keys
    target_shape_keys = target_object.data.shape_keys
    target_drivers = target_shape_keys.animation_data.drivers

    # Remove shapekeys that no longer exist in the base object
    for binded_key in target_object.data.shape_keys.key_blocks:
        if not getattr(target_shape_keys, "animation_data"):
            target_shape_keys.animation_data_create()

        if not source_shape_keys.key_blocks.get(binded_key.name):
            if SPPARAMETERS.full_mirror:
                target_object.shape_key_remove(binded_key)

            elif driver := target_drivers.find(
                f'key_blocks["{binded_key.name}"].value'
            ):
                remove_driver(target_shape_keys, driver)


def mirror_shape_key_positions(source_object: Object, target_object: Object):
    source_shape_keys = source_object.data.shape_keys.key_blocks
    target_shape_keys = target_object.data.shape_keys.key_blocks
    for target_key in target_shape_keys[1:]:
        if not (source_key := source_shape_keys.get(target_key.name)):
            continue

        target_index = target_shape_keys.find(target_key.name)
        source_index = source_shape_keys.find(source_key.name)
        if source_index != target_index:
            move_shape_key(target_object, target_key, source_index)


# Thanks to Cirno, extremely intelligent approach (that i don't understand)
# https://blenderartists.org/t/reorder-bpy-prop-collection-data-shape-keys-key-blocks/1215584
def move_shape_key(object: Object, shape_key: ShapeKey, target_index: int):
    index_shape_key = object.data.shape_keys.key_blocks[target_index]

    shape_key_data = [vertex.co.copy() for vertex in shape_key.data]
    index_data = [vertex.co.copy() for vertex in index_shape_key.data]

    for index, vertex in enumerate(shape_key.data):
        vertex.co = index_data[index]
    for index, vertex in enumerate(index_shape_key.data):
        vertex.co = shape_key_data[index]

    shape_key_name = shape_key.name
    index_shape_key_name = index_shape_key.name
    index_shape_key.name = "_temp_name"

    shape_key.name = index_shape_key_name
    index_shape_key.name = shape_key_name


def remove_driver(target_shape_keys: Key, driver: FCurve):
    if var := driver.driver.variables.get("sb_bind"):
        driver.driver.variables.remove(var)

    if not len(driver.driver.variables):
        target_shape_keys.animation_data.drivers.remove(driver)


# endregion


# region Operators
class OSB_OT_bind(bpy.types.Operator):
    """Binds the selected meshes to the active one"""

    @classmethod
    def poll(cls, context):
        if len(bpy.context.selected_objects) <= 1:
            cls.poll_message_set("Select more than one object.")
            return

        return True

    bl_idname = "osb.bind"
    bl_label = "Bind Selected to Active"
    bl_description = "Binds the selected meshes to the active one"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        active_mesh = bpy.context.object
        selected_meshes = bpy.context.selected_objects

        for object in selected_meshes:
            if not object.data:
                continue
            if object == active_mesh:
                continue

            object.data["sp_binded_object"] = active_mesh

        bind_update(self, context)

        return {"FINISHED"}


class OSB_OT_unbind(bpy.types.Operator):
    """Unbinds the selected meshes"""

    bl_idname = "osb.unbind"
    bl_label = "Unbind Selected Objects"
    bl_description = "Unbinds the selected meshes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        selected_meshes = bpy.context.selected_objects

        for object in selected_meshes:
            if not object.data:
                continue
            if not object.data.get("sp_binded_object"):
                continue

            del object.data["sp_binded_object"]

            # Clears shapekey drivers
            target_shape_keys = object.data.shape_keys
            target_drivers = target_shape_keys.animation_data.drivers
            for binded_key in target_shape_keys.key_blocks:
                if not (
                    driver := target_drivers.find(
                        f'key_blocks["{binded_key.name}"].value'
                    )
                ):
                    continue

                remove_driver(target_shape_keys, driver)

        return {"FINISHED"}


# endregion


# region UI
class OSB_PT_mainpanel(bpy.types.Panel):
    bl_label = "Shapekey Binder"
    bl_description = ""
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        object = bpy.context.object
        col = layout.column(align=True)
        col.operator("osb.bind")
        col.operator("osb.unbind")
        col.prop(object.data.spparameters, "full_mirror")


# endregion


# region Registration
def register():
    bpy.utils.register_class(SP_parameters)
    bpy.utils.register_class(OSB_OT_bind)
    bpy.utils.register_class(OSB_OT_unbind)
    bpy.utils.register_class(OSB_PT_mainpanel)

    bpy.app.handlers.depsgraph_update_post.append(bind_update)

    bpy.types.Mesh.spparameters = bpy.props.PointerProperty(
        type=SP_parameters, override={"LIBRARY_OVERRIDABLE"}
    )


def unregister():
    del bpy.types.Mesh.spparameters

    bpy.app.handlers.depsgraph_update_post.remove(bind_update)
    bpy.utils.unregister_class(SP_parameters)
    bpy.utils.unregister_class(OSB_OT_bind)
    bpy.utils.unregister_class(OSB_OT_unbind)
    bpy.utils.unregister_class(OSB_PT_mainpanel)


if __name__ == "__main__":
    register()
# endregion
