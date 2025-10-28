import bpy
import math
import os
from mathutils import Vector, Euler

# === 配置 ===
MODEL_PATH = "/home/frank/data/gitlab/blender_pro/data/QR0001_rotate.obj"
OUTPUT_DIR = "/home/frank/data/gitlab/blender_pro/output"
N_VIEWS = 12
CAMERA_DISTANCE = 0.5  # 相机距离模型中心（米为单位）
PITCH_ANGLES = [0, 15, 30, 45, 60, 75, 90]  # 物体俯仰角（度）

os.makedirs(OUTPUT_DIR, exist_ok=True)

# === 清空场景 ===
bpy.ops.wm.read_factory_settings(use_empty=True)

# === 导入模型 ===
bpy.ops.import_scene.obj(filepath=MODEL_PATH)

# === 把模型从毫米缩放为米 ===
for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        obj.scale = (0.001, 0.001, 0.001)
bpy.ops.object.transform_apply(scale=True)

# 选中所有物体
objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']

# === 计算模型包围盒 ===
min_corner = Vector((float('inf'), float('inf'), float('inf')))
max_corner = Vector((float('-inf'), float('-inf'), float('-inf')))
for obj in objs:
    for v in obj.bound_box:
        world_v = obj.matrix_world @ Vector(v)
        min_corner = Vector((min(min_corner[i], world_v[i]) for i in range(3)))
        max_corner = Vector((max(max_corner[i], world_v[i]) for i in range(3)))

center = (min_corner + max_corner) / 2.0
size = max_corner - min_corner
max_dim = max(size)

# === 添加相机 ===
bpy.ops.object.camera_add(location=(0, -CAMERA_DISTANCE, 0))
camera = bpy.context.object
bpy.context.scene.camera = camera

# 相机指向模型中心
direction = center - camera.location
camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# === 添加光照（沿相机方向） ===
bpy.ops.object.light_add(type='SUN')
light = bpy.context.object
light.data.energy = 4.0
offset = 0.1
light.location = camera.matrix_world.translation - camera.matrix_world.to_quaternion() @ Vector((0, 0, offset))
light.rotation_euler = camera.rotation_euler

# === 环境光 ===
if bpy.context.scene.world is None:
    bpy.context.scene.world = bpy.data.worlds.new("World")
bpy.context.scene.world.use_nodes = True
bg = bpy.context.scene.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (1, 1, 1, 1)
bg.inputs[1].default_value = 0.1

# === 曝光调整 ===
bpy.context.scene.view_settings.exposure = 1.0
bpy.context.scene.view_settings.gamma = 1.0


# === 外层循环：模型俯仰角 ===
for pitch_deg in PITCH_ANGLES:
    pitch_rad = math.radians(pitch_deg)
    print(f"\n==== 模型俯仰角: {pitch_deg}° ====")

    # 让模型绕X轴旋转
    for obj in objs:
        obj.rotation_euler = Euler((pitch_rad, 0, 0), 'XYZ')

    # === 内层循环：相机绕模型旋转 ===
    for i in range(N_VIEWS):
        angle = i * 2 * math.pi / N_VIEWS
        x = center.x + CAMERA_DISTANCE * math.cos(angle)
        y = center.y + CAMERA_DISTANCE * math.sin(angle)
        z = center.z + max_dim * 0.3  # 略高拍摄

        camera.location = (x, y, z)
        direction = center - camera.location
        camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

        # === 光照更新 ===
        light.location = camera.matrix_world.translation - camera.matrix_world.to_quaternion() @ Vector((0, 0, offset))
        light.rotation_euler = camera.rotation_euler

        # === 渲染输出 ===
        bpy.context.scene.render.image_settings.file_format = 'PNG'
        filename = f"pitch_{pitch_deg:+03d}_view_{i:03d}.png"
        bpy.context.scene.render.filepath = os.path.join(OUTPUT_DIR, filename)
        bpy.ops.render.render(write_still=True)

        print(f"Rendered {filename}")
