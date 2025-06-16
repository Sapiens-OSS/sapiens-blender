import bpy
import math
import json
from pathlib import Path
import tomllib
import re

def get_export_folder(blend_path):
    blend_path = Path(bpy.data.filepath)
    
    if not blend_path.exists():
        return False
        
    blend_dir = blend_path.parent
    export_dir = blend_dir.parent / "models" if blend_dir.name.lower() == "blends" else blend_dir
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir

def get_export_path(blend_path):
    return get_export_folder(blend_path) / Path(blend_path).stem

def get_material_file_path() -> Path:
    blend_path = Path(bpy.data.filepath)
    return blend_path.parent.parent / "hammerstone" / "shared" / "blender_materials.json"
        

def get_extension_version() -> str:
    config_path = Path(__file__).parent / "blender_manifest.toml"
    with open(config_path, "rb") as config:
        return tomllib.load(config).get("version", "Unknown")
    return "Failed"

class SAPIENS_OT_export_parts(bpy.types.Operator):
    bl_idname = "sapiens.export_parts"
    bl_label = "Export Parts"
    bl_description = "Exports every mesh in the model as its own GLTF file."

    def get_model_name(self, mesh_name : str):
        if "."  in mesh_name:
            mesh_name = mesh_name.split(".")[0]
        
        if "_" in mesh_name:
            mesh_name = mesh_name.split("_")[0]
            
        return mesh_name
    
    def execute(self, context):
        blend_path = Path(bpy.data.filepath)
        if not blend_path.exists():
            self.report({'ERROR'}, "File must be saved before exporting.")
            return {'CANCELLED'}

        export_root = get_export_folder(blend_path)
        if not export_root:
            self.report({'ERROR'}, "Failed to resolve export folder.")
            return {'CANCELLED'}

        export_root.mkdir(parents=True, exist_ok=True)

        original_selection = context.selected_objects.copy()
        original_active = context.view_layer.objects.active

        exported_models = []
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue

            model_name = self.get_model_name(obj.name)
            if model_name in exported_models:
                continue
            
            # Deselect all
            bpy.ops.object.select_all(action='DESELECT')

            # Cache transforms
            cached_matrix = obj.matrix_world.copy()
            
            # Select only the target mesh
            obj.select_set(True)
            context.view_layer.objects.active = obj
            
            exported_models.append(model_name)
            
            obj.location = (0.0, 0.0, 0.0)
            obj.rotation_euler = (0.0, 0.0, 0.0)
            obj.scale = (1.0, 1.0, 1.0)

            export_path = export_root / f"{model_name}.glb"
            bpy.ops.export_scene.gltf(
                filepath=str(export_path),
                export_format='GLB',
                use_selection=True,
                export_apply=True,
            )
            
            obj.matrix_world = cached_matrix

        # Restore previous selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selection:
            obj.select_set(True)
        context.view_layer.objects.active = original_active

        self.report({'INFO'}, f"Exported {exported_models} to '{export_path}'")
        return {'FINISHED'}
    
class SAPIENS_OT_add_buildables(bpy.types.Operator):
    bl_idname = "sapiens.add_buildables"
    bl_label = "Add Buildables"
    bl_description = "Adds the empties you need for a buildable."
    
    def execute(self, context):

        bounding_radius = bpy.data.objects.new("bounding_radius", None)
        bounding_radius.empty_display_type = 'SPHERE'
        bpy.context.collection.objects.link(bounding_radius)
        
        attach_box = bpy.data.objects.new("placeAttach_box_1", None)
        attach_box.empty_display_type = 'CUBE'
        bpy.context.collection.objects.link(attach_box)

        static_box = bpy.data.objects.new("static_box", None)
        static_box.empty_display_type = 'CUBE'
        bpy.context.collection.objects.link(static_box)

        self.report({'INFO'}, "Done.")
        return {'FINISHED'}

class MaterialFile():

    """
    Wrapper around Json material file
    """

    def __init__(self, filepath : Path):
        self.filepath = filepath
        self.ensure_file_exists()
        self.index = self.build_index()

    def build_index(self):
        with open(get_material_file_path(), "r") as f:
            data = json.load(f)

        index = {}
        for material in data["hammerstone:global_definitions"]["hs_materials"]:
            index[material["identifier"]] = material
        return index

    @staticmethod
    def get_default_data():
        return json.loads(
"""
{
    "hammerstone:global_definitions": {
        "hs_materials": []
    }
}
"""
        )

    def ensure_file_exists(self):
        if self.filepath.exists():
            return
        
        self.filepath.parent.mkdir(exist_ok=True, parents=True)
        
        with open(self.filepath, "w") as f:
            json.dump(MaterialFile.get_default_data(), f)

    @staticmethod
    def get_default_path() -> Path:
        blend_path = Path(bpy.data.filepath)
        return blend_path.parent.parent / "hammerstone" / "shared" / "blender_materials.json"

    @staticmethod
    def open():
        return MaterialFile(MaterialFile.get_default_path())
    
    def save(self):
        data = MaterialFile.get_default_data()
        print(self.index.values())

        data["hammerstone:global_definitions"]["hs_materials"] = self.get_materials()

        with open(self.filepath, "w") as f:
            json.dump(data, f)
    
    def get_materials(self):
        materials = []
        for material in self.index.values():
            materials.append(material)
        return materials
        
    def write_material(self, material):
        self.index[material.name] = MaterialFile.material_to_json(material)

    @staticmethod
    def material_to_json(material):
        bsdf = None
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    bsdf = node
                    break

        if not bsdf:
            print(f"No Principled BSDF found in material {material.name}")
            return None

        # Extract values
        color = bsdf.inputs['Base Color'].default_value[:3]  # RGB only
        metal = bsdf.inputs['Metallic'].default_value
        roughness = bsdf.inputs['Roughness'].default_value

        # Format data
        mat_data = {
            "identifier": material.name,
            "color": [round(c, 3) for c in color],
            "metal": round(metal, 3),
            "roughness": round(roughness, 3)
        }

        return mat_data
    
    @staticmethod
    def json_to_material(data):
        name = data.get("identifier", "Material")
        color = data.get("color", [1.0, 1.0, 1.0])
        metal = data.get("metal", 0.0)
        roughness = data.get("roughness", 0.5)

        # Get or create the material
        material = bpy.data.materials.get(name)
        if not material:
            material = bpy.data.materials.new(name=name)
            material.use_nodes = True

        # Get the node tree
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Clear existing nodes
        nodes.clear()

        # Create necessary nodes
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        output_node.location = (300, 0)

        bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf_node.location = (0, 0)

        # Set values
        bsdf_node.inputs['Base Color'].default_value = (*color, 1.0)  # RGBA
        bsdf_node.inputs['Metallic'].default_value = metal
        bsdf_node.inputs['Roughness'].default_value = roughness

        # Link BSDF to Output
        links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

        return material


class SAPIENS_OT_import_materials(bpy.types.Operator):
    bl_idname = "sapiens.import_materials"
    bl_label = "Import Materials"
    bl_description = "Imports materials from hammerstone/shared/blender_materials."

    def execute(self, context):
        material_file = MaterialFile.open()

        for material in material_file.get_materials():
            MaterialFile.json_to_material(material)
    
        return {'FINISHED'}
    
class SAPIENS_OT_export_materials(bpy.types.Operator):
    bl_idname = "sapiens.export_materials"
    bl_label = "Export Materials"
    bl_description = "Exports materials from hammerstone/shared/blender_materials."

    def execute(self, context):
        material_file = MaterialFile.open()

        for material in bpy.data.materials:
            material_file.write_material(material)

        material_file.save()

        return {'FINISHED'}
    
class SAPIENS_OT_remove_duplicate_materials(bpy.types.Operator):
    bl_idname = "sapiens.remove_duplicate_materials"
    bl_label = "Remove Duplicates"
    bl_description = "Deletes any materials like 'bone.001' and replaces them with the proper material name (bone)."

    def execute(self, context):
        suffix_pattern = re.compile(r"(.*)\.(\d{3})$")
        renamed_materials = {}

        for mat in list(bpy.data.materials):  # Avoid modifying list during iteration
            match = suffix_pattern.match(mat.name)
            if match:
                base_name = match.group(1)
                base_mat = bpy.data.materials.get(base_name)

                if base_mat:
                    # Replace users of the duplicate material
                    for obj in bpy.data.objects:
                        if obj.type == 'MESH':
                            for slot in obj.material_slots:
                                if slot.material == mat:
                                    slot.material = base_mat
                    renamed_materials[mat.name] = f"Replaced with '{base_name}' and removed"
                    
                    # Remove the duplicate material
                    bpy.data.materials.remove(mat)
                else:
                    if not bpy.data.materials.get(base_name):
                        mat.name = base_name
                        renamed_materials[mat.name] = "Renamed (no original existed)"
                    else:
                        renamed_materials[mat.name] = "Name conflict; not renamed"

        self.report({'INFO'}, f"Processed {len(renamed_materials)} materials.")
        return {'FINISHED'}

class SAPIENS_OT_export_empties(bpy.types.Operator):
    bl_idname = "sapiens.export_empties"
    bl_label = "Export Empties"
    bl_description = "Exports the scene with all meshes replaced by empties."

    def get_empty_name(self, mesh_name: str, model_counts: dict):
        if "." in mesh_name:
            mesh_name = mesh_name.split(".")[0]

        if "_" in mesh_name:
            mesh_name = mesh_name.split("_")[1]

        index = model_counts.get(mesh_name, 0) + 1
        model_counts[mesh_name] = index

        return f"{mesh_name}_{str(index)}"
    
    def execute(self, context):
        export_path = get_export_path(bpy.data.filepath)
        if not export_path:
            return {'CANCELLED'}

        # Track replacements and objects to export
        replacements = []
        new_empties = []

        counts = {}
        # Replace all mesh objects with empties
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                original_name = obj.name
                renamed_name = f"{original_name}_original"
                obj.name = renamed_name

                empty = bpy.data.objects.new(self.get_empty_name(original_name, counts), None)
                empty.empty_display_type = 'PLAIN_AXES'
                empty.empty_display_size = 0.5
                empty.matrix_world = obj.matrix_world
                empty.parent = obj.parent
                empty.hide_viewport = obj.hide_viewport
                empty.hide_render = obj.hide_render

                for collection in obj.users_collection:
                    collection.objects.link(empty)

                replacements.append((obj, empty, original_name))
                new_empties.append(empty)

        # Deselect all
        bpy.ops.object.select_all(action='DESELECT')

        # Select only empties (new and existing) and cameras
        for obj in bpy.data.objects:
            if obj.type in {'EMPTY', 'CAMERA'}:
                obj.select_set(True)

        # Ensure an active object is set (some exporters need it)
        context.view_layer.objects.active = new_empties[0] if new_empties else None

        bpy.ops.export_scene.gltf(
            filepath=str(export_path),
            export_format='GLB',
            use_selection=True,
            export_apply=True,
            export_materials='PLACEHOLDER',
            export_cameras=True
        )

        # Restore scene
        for mesh_obj, empty, original_name in replacements:
            # Remove the empty
            for collection in empty.users_collection:
                collection.objects.unlink(empty)
            bpy.data.objects.remove(empty)

            # Rename mesh back
            mesh_obj.name = original_name

        self.report({'INFO'}, f"Exported to {export_path}")
        return {'FINISHED'}

    
class SAPIENS_OT_export(bpy.types.Operator):
    bl_idname = "sapiens.export"
    bl_label = "Export"
    bl_description = "Exports the model."
    
    def execute(self, context):
        export_path = get_export_path(bpy.data.filepath)
        if not export_path:
            return {'CANCELLED'}

        bpy.ops.export_scene.gltf(filepath=str(export_path), export_format='GLB', use_selection=True)

        self.report({'INFO'}, f"Exported to {export_path}")
        return {'FINISHED'}
    
    
class SAPIENS_OT_add_camera(bpy.types.Operator):
    bl_idname = "sapiens.add_camera"
    bl_label = "Add Camera"
    bl_description = "Adds a sapiens-compatible camera to the scene"
    
    def execute(self, context):

        cam_data = bpy.data.cameras.new(name="icon_camera2")
        cam_data.angle = math.radians(30)

        cam_obj = bpy.data.objects.new(name="icon_camera2", object_data=cam_data)
        context.collection.objects.link(cam_obj)

        context.scene.render.resolution_x = 1080
        context.scene.render.resolution_y = 1080

    
        cam_obj.location = (-1.7204, -1.2657, 0.94239)
        cam_obj.rotation_euler = (
            math.radians(75.683),
            math.radians(-0.000075),
            math.radians(-50.567)
        )
    
        self.report({'INFO'}, "Camera 'icon_camera2' added with 30° FOV and 1080x1080 resolution.")
        return {'FINISHED'}
    
class SAPIENS_OT_scale_empties(bpy.types.Operator):
    bl_idname = "sapiens.scale_empties"
    bl_label = "Apply Scale"
    bl_description = "Sets display scale of empties to 1."
    
    def execute(self, context):
        for obj in context.scene.objects:
            if obj.type == 'EMPTY':
                obj.empty_display_size = 1.0
        
        return {'FINISHED'}
    
class SAPIENS_OT_set_empty_types(bpy.types.Operator):
    bl_idname = "sapiens.set_empty_types"
    bl_label = "Apply Type"
    bl_description = "Sets empty type based on name."
    
    def get_empty_type(self, obj):
        name = obj.name.lower()
        if "box" in name or "cube" in name:
            return "CUBE"
        if "sphere" in name or "seat" in name or "radius" in name:
            return "SPHERE"
        if "store" in name:
            return "PLAIN_AXES"
        
        return obj.empty_display_type
        
        
        
    def execute(self, context):
        for obj in context.scene.objects:
            if obj.type == 'EMPTY':
                obj.empty_display_type = self.get_empty_type(obj)
        
        return {'FINISHED'}


class VIEW3D_PT_sapiens(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    
    bl_label = "Sapiens"
    bl_category = "Sapiens"
    
    def draw(self, context):
        self.layout.label(text=f"Version: {get_extension_version()}")
        self.layout.separator()

        empties_box = self.layout.box()
        empties_box.label(text="Empties")
        empty_row = empties_box.row()
        empty_row.operator("sapiens.scale_empties")
        empty_row.operator("sapiens.set_empty_types")
        
        
        quick_box = self.layout.box()
        quick_box.label(text="Quick Actions")
        quick_row = quick_box.row()
        quick_row.operator("sapiens.add_camera")
        quick_row.operator("sapiens.add_buildables")

        export_box = self.layout.box()
        export_box.label(text="Export")
        export_row = export_box.row()
        export_row.operator("sapiens.export")
        export_row.operator("sapiens.export_empties")
        export_row_2 = export_box.row()
        export_row_2.operator("sapiens.export_parts")

        materials_box = self.layout.box()
        materials_box.label(text="Materials")
        materials_row = materials_box.row()
        materials_row.operator("sapiens.import_materials")
        materials_row.operator("sapiens.export_materials")
        materials_row2 = materials_box.row()
        materials_row2.operator("sapiens.remove_duplicate_materials")

def register():
    bpy.utils.register_class(SAPIENS_OT_scale_empties)
    bpy.utils.register_class(SAPIENS_OT_set_empty_types)
    bpy.utils.register_class(SAPIENS_OT_add_camera)
    bpy.utils.register_class(SAPIENS_OT_add_buildables)
    bpy.utils.register_class(SAPIENS_OT_export)
    bpy.utils.register_class(SAPIENS_OT_export_empties)
    bpy.utils.register_class(SAPIENS_OT_export_parts)
    bpy.utils.register_class(SAPIENS_OT_import_materials)
    bpy.utils.register_class(SAPIENS_OT_export_materials)
    bpy.utils.register_class(SAPIENS_OT_remove_duplicate_materials)
    
    bpy.utils.register_class(VIEW3D_PT_sapiens)

def unregister():
    bpy.utils.unregister_class(SAPIENS_OT_scale_empties)
    bpy.utils.unregister_class(SAPIENS_OT_set_empty_types)
    bpy.utils.unregister_class(SAPIENS_OT_add_camera)
    bpy.utils.unregister_class(SAPIENS_OT_add_buildables)
    bpy.utils.unregister_class(SAPIENS_OT_export)
    bpy.utils.unregister_class(SAPIENS_OT_export_empties)
    bpy.utils.unregister_class(SAPIENS_OT_export_parts)
    bpy.utils.unregister_class(SAPIENS_OT_import_materials)
    bpy.utils.unregister_class(SAPIENS_OT_export_materials)
    bpy.utils.unregister_class(SAPIENS_OT_remove_duplicate_materials)
    
    bpy.utils.unregister_class(VIEW3D_PT_sapiens)

if __name__ == "__main__":
    register()
    
