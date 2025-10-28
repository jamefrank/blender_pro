import bpy
import math
import os
from mathutils import Vector, Euler

# === 配置 ===
MODEL_PATH = "/home/frank/data/gitlab/blender_pro/data/QR0001_rotate.obj"
OUTPUT_DIR = "/home/frank/data/gitlab/blender_pro/output"
N_VIEWS = 12
CAMERA_DISTANCE = 0.5  # 相机距离模型中心（米）
ROLL_ANGLES = [0, 30, 60, 90, 120, 150]
PITCH_ANGLES = [0, 15, 30, 45, 60, 75, 90]  # 物体俯仰角（度）
YAW_ANGLES = [0, 30, 60, 90, 120, 150]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# === 清空场景 ===
bpy.ops.wm.read_factory_settings(use_empty=True)

# === 导入模型 ===
bpy.ops.import_scene.obj(filepath=MODEL_PATH)

# === 缩放模型从毫米到米 ===
for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        obj.scale = (0.001, 0.001, 0.001)
bpy.ops.object.transform_apply(scale=True)

# 选中所有物体
objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']

# === 计算模型中心和尺寸 ===
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

# === 添加相机（固定位置） ===
cam_z = center.z + max_dim * 0.3  # 略高拍摄
camera = bpy.data.cameras.new("Camera")
cam_obj = bpy.data.objects.new("Camera", camera)
bpy.context.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj
cam_obj.location = (center.x, center.y - CAMERA_DISTANCE, cam_z)

# 相机朝向模型中心
direction = center - cam_obj.location
cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# === 添加光照（固定，沿相机方向） ===
bpy.ops.object.light_add(type='SUN')
light = bpy.context.object
light.data.energy = 4.0
offset = 0.1
light.location = cam_obj.matrix_world.translation - cam_obj.matrix_world.to_quaternion() @ Vector((0, 0, offset))
light.rotation_euler = cam_obj.rotation_euler

# === 环境光 ===
if bpy.context.scene.world is None:
    bpy.context.scene.world = bpy.data.worlds.new("World")
bpy.context.scene.world.use_nodes = True
bg = bpy.context.scene.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (1, 1, 1, 1)  # 白色
bg.inputs[1].default_value = 0.1           # 环境光强度

# === 曝光调整 ===
bpy.context.scene.view_settings.exposure = 1.0
bpy.context.scene.view_settings.gamma = 1.0

# === 渲染循环：固定相机 + 模型旋转 ===
cnt = 0
for roll_deg in ROLL_ANGLES:
    roll_rad = math.radians(roll_deg)
    for pitch_deg in PITCH_ANGLES:
        pitch_rad = math.radians(pitch_deg)
        for yaw_deg in YAW_ANGLES:
            yaw_rad = math.radians(yaw_deg)

            # 模型旋转：俯仰 + Z轴旋转（代替相机环绕）
            for obj in objs:
                obj.rotation_euler = Euler((pitch_rad, 0, yaw_rad), 'XYZ')

            # 渲染
            bpy.context.scene.render.image_settings.file_format = 'PNG'
            filename = f"view_{cnt:03d}.png"
            bpy.context.scene.render.filepath = os.path.join(OUTPUT_DIR, filename)
            bpy.ops.render.render(write_still=True)

            print(f"Rendered {filename}")
            
            cnt += 1
