# sapiens-blender

Blender addon for [Sapiens](https://store.steampowered.com/app/1060230/Sapiens/). Join [the discord](https://discord.gg/WnN8hj2Fyg) for support.

## Model Format

Sapiens requires models to be setup in a very specific way. This addon helps you achieve that. You can read [detailed documentation](https://wiki.sapiens.dev/docs/models/model-format.html) here.

## Getting Started / Installation

`Edit -> Preferences -> Add-Ons -> (top right dropdown) Install from Disk -> select sapiens-blend.py`

After installing, you may need to enable the addon (checkbox). Once enabled, a new `[Sapiens]` button will appear in the context-menu of the main scene. The default shortcut to open this menu is `n`, and then you can navigate from `tool` or `view` to `sapiens`.

## Importing GLTF Files

Sapiens ships with all of their models in GLTF format. After importing into Blender, you will notice some information has been lost. This addon comes with two buttons to help with you with that:
- `Apply Scale`: Sets empty display size to 1. This is always correct. Dimensions of empties are set via their scale, not display size. Since this information is lost during GLTF import/export, this button allowed restoring it.
- `Apply Shape`: Automatically sets `Display Type` for all empties, based on some heuristics. For example `staticBox_1` would be switched to `Cube` display type, instead of `Axes`.

## Creating a new Buildable

This addon comes with two helpers for crafting new buildables.

- `Add Camera`: This adds a new camera into the scene, named correctly, using the correct aspect ration, and placed at a convenient default location. A camera is required for rendering the icon correctly.
- `Add Buildables`: This option adds all the required non-mesh empties. For example a `staticBox`. All empties have correct scale and display type applied.

# Exporting

This addon assumes that you model is located directly in a folder called `blends` (not nested). The export buttons allows you to export your model in a few different ways, without needing to manually export the GLTF file. The resulting meshes will be placed into a `models` folder, side-by-side with your blends. From this folder, Sapiens will read the models.

There is also a mesh naming convention. The convention is: `meshName_resourceType.whatever`

 - `meshName` is the name of the model. For example if you're creating a chair, `chairBack` and `chairLeg` are reasonable mesh names.
 - `resourceType` should match a resource in Sapiens. Either self-created, or vanilla.
 - `whatever` Everything after the `.` is ignored. Usually this will be an identifier from blender when duplicating meshes (e.g., `cube_branch.003`)

## Simply Export

The first button, `Export`, simply exports the model, with no changes. This is equivalent to manually exporting.

## Export Empties

This option allows you to export a version of your model, with all of the meshes replaced by like-named empties. If you followed the naming convention from above, then the empties will also have the correct names and indexes. For example if your model had four `chairLeg_branch.000x` models, the resulting mesh would have `branch_1`, `branch_2`, etc. This is the format Blender needs.

## Export Parts

This option is intended to be used alongside of `Export Empties`. In principle is just does the reverse: It will export all of the meshes in the model into individual GLTF files, with their transform zeroed out. For example for a `chair.blend` with back, seat, and 4 legs (e.g., `chairLeg_branch.003`), then three GLTF files will be created: `models/chair/leg.glb`, `models/chair/chairBack.glb`, and `models/chair/chairSeat.glb`.

Even though we had 4 chair legs in our model, only one is exported. This single model will be reused for all chair legs within Sapiens.

# Development

You can help develop the addon by installing [this extension](https://marketplace.visualstudio.com/items?itemName=JacquesLucke.blender-development), and following the instructions there. PRs and issues welcome.

# Version History

## 1.2.0

BREAKING CHANGE: Models now require index. Example: modelName_resourceName_1.

It's also possible to do this, to avoid the PART from being exported (will still appear in the Empties): `modelName_resourceName_1_noexport`.

## 1.1.0

Adds buttons to hide/show empties.

## 1.0.0

Initial release, providing the basic support for sapiens models.