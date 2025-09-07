bl_info = {
    "name": "Render Sequencer",
    "author": "Lex713",
    "version": (1, 3, 0),
    "blender": (4, 0, 0),
    "location": "Properties > Output > Scene Render to Slots",
    "description": "Render multiple scenes of your selection in sequence into sepqrate Image Editor slots with proper names",
    "category": "Render",
}

import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import BoolProperty, PointerProperty


# --- Properties --- #
class SceneSelection(PropertyGroup):
    use: BoolProperty(name="Render", default=False)


# --- Panel --- #
class RENDER_PT_SceneSlotSelector(Panel):
    bl_label = "Scene Render to Slots"
    bl_idname = "RENDER_PT_scene_slot_selector"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Select Scenes to render (still) into slots:")
        col = layout.column(align=True)
        for scene in bpy.data.scenes:
            row = col.row(align=True)
            row.prop(scene.scene_selection, "use", text=scene.name)
        layout.separator()
        layout.operator("render.render_scenes_to_slots", icon='RENDER_STILL')


# --- Queue Manager --- #
class RenderQueueManager:
    def __init__(self, operator, scenes, original_scene):
        self.op = operator
        self.scenes = scenes
        self.original_scene = original_scene
        self.index = 0
        self.img = bpy.data.images.get("Render Result")

    def start(self):
        if self.img is None:
            bpy.ops.render.render()
            self.img = bpy.data.images.get("Render Result")

        self._report("Starting scene render queue...")
        bpy.app.handlers.render_complete.append(self._on_render_complete)

        # Kick off first render
        self._render_current_scene()

    def _render_current_scene(self):
        if self.index >= len(self.scenes):
            self._finish()
            return

        scene = self.scenes[self.index]
        bpy.context.window.scene = scene
        self._report(f"Rendering scene '{scene.name}' ({self.index+1}/{len(self.scenes)})...")

        # Find/create slot
        existing = None
        for i, slot in enumerate(self.img.render_slots):
            if slot.name == scene.name:
                existing = i
                break
        if existing is not None:
            self.img.render_slots.active_index = existing
        else:
            self.img.render_slots.new(name=scene.name)
            self.img.render_slots.active_index = len(self.img.render_slots) - 1

        bpy.ops.render.render('INVOKE_DEFAULT')

    def _on_render_complete(self, scene):
        # One scene finished, go to next
        self.index += 1
        if self.index < len(self.scenes):
            self._render_current_scene()
        else:
            self._finish()

    def _finish(self):
        # Clean up and restore scene
        if self._on_render_complete in bpy.app.handlers.render_complete:
            bpy.app.handlers.render_complete.remove(self._on_render_complete)
        bpy.context.window.scene = self.original_scene
        self._report("Finished rendering all selected scenes ✅")

    def _report(self, msg):
        print(msg)
        self.op.report({'INFO'}, msg)


# --- Operator --- #
class RENDER_OT_RenderScenesToSlots(Operator):
    bl_idname = "render.render_scenes_to_slots"
    bl_label = "Render Selected Scenes to Slots"
    bl_description = "Render one still from each selected scene into its own render slot (named after the scene)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        selected = [s for s in bpy.data.scenes if getattr(s, "scene_selection", None) and s.scene_selection.use]
        if not selected:
            self.report({'WARNING'}, "No scenes selected.")
            return {'CANCELLED'}

        manager = RenderQueueManager(self, selected, context.window.scene)
        manager.start()
        return {'FINISHED'}


# --- Registration --- #
classes = (
    SceneSelection,
    RENDER_PT_SceneSlotSelector,
    RENDER_OT_RenderScenesToSlots,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.scene_selection = PointerProperty(type=SceneSelection)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.scene_selection


if __name__ == "__main__":
    register()
