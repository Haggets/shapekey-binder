import bpy
from bpy.app.handlers import persistent

bl_info = {
    "name": "Shapekey Binder",
    "author": "Haggets",
    "version": (1, 0, 1),
    "blender": (4, 1, 0),
    "description": "Allows shapekeys of other objects to closely match the active object's shapekeys",
    "category": "System",
}


class SP_parameters(bpy.types.PropertyGroup):
    full_mirror: bpy.props.BoolProperty(
        name="Full Shapekey Mirroring",
        description="Deletes shapekeys from the binded object if they aren't in the active object",
        default=True,
    )


@persistent
def bind_update(self, context):
    binded_objects = bpy.context.scene.get("sp_binded_objects")
    if not binded_objects:
        return

    removed_objects = []
    for object_name in binded_objects:
        object = bpy.data.objects.get(object_name)

        if not object:
            removed_objects.append(object_name)
            continue
        if bpy.context.object == object:
            continue

        if not getattr(object.data, "shape_keys"):
            object.shape_key_add(name="Basis", from_mix=False)

        base_object = object.get("sp_binded_object")
        object.show_only_shape_key = base_object.show_only_shape_key
        object.active_shape_key_index = object.data.shape_keys.key_blocks.find(
            base_object.active_shape_key.name
        )
        SPPARAMETERS = base_object.data.spparameters

        base_shape_keys = base_object.data.shape_keys
        binded_shape_keys = object.data.shape_keys

        # Creates new shapekeys from the base object onto the binded object
        for base_key in base_object.data.shape_keys.key_blocks:
            if not (binded_key := object.data.shape_keys.key_blocks.get(base_key.name)):
                binded_key = object.shape_key_add(name=base_key.name, from_mix=False)

            if not getattr(binded_shape_keys, "animation_data"):
                binded_shape_keys.animation_data_create()

            # Links the shapekey to a driver if no driver is found
            if binded_shape_keys.animation_data.drivers.find(
                'key_blocks["{}"].value'.format(binded_key.name)
            ):
                continue

            driver = binded_key.driver_add("value").driver
            driver.expression = "sb_bind"
            if var := driver.variables.get("sb_bind"):
                driver.variables.remove(var)

            var = driver.variables.new()
            var.name = "sb_bind"
            target = var.targets[0]
            target.id_type = "KEY"
            target.id = base_shape_keys
            target.data_path = 'key_blocks["{}"].value'.format(binded_key.name)

        # Remove shapekeys that no longer exist in the base object
        for binded_key in object.data.shape_keys.key_blocks:
            if not getattr(binded_shape_keys, "animation_data"):
                binded_shape_keys.animation_data_create()

            if SPPARAMETERS.full_mirror:
                if not base_object.data.shape_keys.key_blocks.get(binded_key.name):
                    object.shape_key_remove(binded_key)
            else:
                if not base_object.data.shape_keys.key_blocks.get(
                    binded_key.name
                ) and binded_shape_keys.animation_data.drivers.find(
                    'key_blocks["{}"].value'.format(binded_key.name)
                ):
                    object.shape_key_remove(binded_key)

    for object in removed_objects:
        binded_objects.remove(object)


class OSB_OT_bind(bpy.types.Operator):
    """Binds the selected meshes to the active one"""

    @classmethod
    def poll(cls, context):
        has_poll = True

        if len(bpy.context.selected_objects) <= 1:
            cls.poll_message_set("Select more than one object.") if has_poll else None
            return

        return True

    bl_idname = "osb.bind"
    bl_label = "Bind Selected to Active"
    bl_description = "Binds the selected meshes to the active one"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        binded_objects = bpy.context.scene.get("sp_binded_objects") or []
        selected_meshes = [item for item in bpy.context.selected_objects]
        active_mesh = bpy.context.object

        for object in selected_meshes:
            if object == active_mesh:
                continue

            object["sp_binded_object"] = active_mesh
            if binded_objects.count(object.name):
                continue

            binded_objects.append(object.name)

        bpy.context.scene["sp_binded_objects"] = binded_objects

        bind_update(self, context)

        return {"FINISHED"}


class OSB_OT_unbind(bpy.types.Operator):
    """Unbinds the selected meshes"""

    bl_idname = "osb.unbind"
    bl_label = "Unbind Selected Objects"
    bl_description = "Unbinds the selected meshes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        selected_meshes = [item for item in bpy.context.selected_objects]

        binded_objects = bpy.context.scene.get("sp_binded_objects") or []
        for object in selected_meshes:
            if not object.get("sp_binded_object"):
                continue

            del object["sp_binded_object"]

            try:
                binded_objects.remove(object.name)
            except ValueError:
                pass

            binded_shape_keys = object.data.shape_keys

            for binded_key in binded_shape_keys.key_blocks:
                if not (
                    driver := binded_shape_keys.animation_data.drivers.find(
                        'key_blocks["{}"].value'.format(binded_key.name)
                    )
                ):
                    continue

                if var := driver.driver.variables.get("sb_bind"):
                    driver.driver.variables.remove(var)

                if not len(driver.driver.variables):
                    binded_shape_keys.animation_data.drivers.remove(driver)

        bpy.context.scene["sp_binded_objects"] = binded_objects

        if not len(bpy.context.scene["sp_binded_objects"]):
            del bpy.context.scene["sp_binded_objects"]

        return {"FINISHED"}


class OSB_PT_mainpanel(bpy.types.Panel):
    """"""

    bl_label = "Shapekey Binder"
    bl_description = ""
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        object = bpy.context.object
        col = layout.column()
        col.operator("osb.bind")
        col.operator("osb.unbind")

        if object and object.type == "MESH":
            col.prop(object.data.spparameters, "full_mirror")


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
