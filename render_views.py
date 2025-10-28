import bpy
import math
import os
from mathutils import Vector

# === 配置 ===
MODEL_PATH = "/home/frank/data/gitlab/blender_pro/data/QR0001_rotate.obj"
OUTPUT_DIR = "/home/frank/data/gitlab/blender_pro/output"
N_VIEWS = 12
CAMERA_DISTANCE = 0.5  # ✅ 相机距离模型中心（米为单位）

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 清空场景
bpy.ops.wm.read_factory_settings(use_empty=True)

# 导入模型
bpy.ops.import_scene.obj(filepath=MODEL_PATH)



# === 把模型从毫米缩放为米 ===
for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        obj.scale = (0.001, 0.001, 0.001)  # 缩小 1000 倍
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

# === 添加光照 ===
bpy.ops.object.light_add(type='SUN', radius=1.0, location=(2, 2, 2))

# === 添加相机 ===
bpy.ops.object.camera_add(location=(0, -CAMERA_DISTANCE, 0))
camera = bpy.context.object
bpy.context.scene.camera = camera

# 相机指向模型中心
direction = center - camera.location
camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# === 渲染循环 ===
for i in range(N_VIEWS):
    angle = i * 2 * math.pi / N_VIEWS
    x = center.x + CAMERA_DISTANCE * math.cos(angle)
    y = center.y + CAMERA_DISTANCE * math.sin(angle)
    z = center.z + max_dim * 0.3  # 略高拍摄

    camera.location = (x, y, z)
    direction = center - camera.location
    camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    # 保存图像
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.filepath = os.path.join(OUTPUT_DIR, f"view_{i:03d}.png")
    bpy.ops.render.render(write_still=True)

    # 输出相机位姿
    print(f"View {i}:\n{camera.matrix_world}")
