import bpy
import math
import os
import json
from mathutils import Vector, Euler

# === 配置 ===
MODEL_PATH = "/home/frank/data/gitlab/blender_pro/data/QR0001_rotate.obj"
OUTPUT_DIR = "/home/frank/data/gitlab/blender_pro/output"
CAMERA_DISTANCE = 0.5  # 相机距离模型中心（米）

ROLL_ANGLES = [0, 30, 60, 90, 120, 150]
PITCH_ANGLES = [0, 15, 30, 45, 60, 75, 90]
YAW_ANGLES = [0, 30, 60, 90, 120, 150]
X_TRANS = [0.0, 0.02, -0.02, 0.04, -0.04, 0.06, -0.06, 0.08, -0.08] # 物体在图像中左右移动
Y_TRANS = [0.0, 0.02, -0.02] # 图像放大缩小
Z_TRANS = [0.0, 0.02, -0.02, 0.04, -0.04] #  物体在图像中上下移动


model_basename = os.path.basename(MODEL_PATH)
model_name_without_ext = os.path.splitext(model_basename)[0]

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
assert(len(objs) == 1)

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

# === 配置相机内参 ===
fx = 1815.0500318867137
fy = 1815.6071098689097
cx = 616.5651758986305
cy = 498.4238074205292
img_w = 1280
img_h = 1024

# 1️⃣ 设定渲染分辨率
scene = bpy.context.scene
scene.render.resolution_x = img_w
scene.render.resolution_y = img_h
scene.render.resolution_percentage = 100

# 2️⃣ 设置相机的光学参数（近似 MechEye NANO）
camera.lens_unit = 'MILLIMETERS'
camera.sensor_width = 3.68  # mm
camera.sensor_height = camera.sensor_width * img_h / img_w

# 3️⃣ 计算对应焦距（从 fx 转为 Blender 焦距）
f_in_mm = fx * camera.sensor_width / img_w
camera.lens = f_in_mm  # 约 5.2 mm

# 4️⃣ 设置主点偏移
camera.shift_x = -(cx - img_w / 2) / img_w
camera.shift_y = (cy - img_h / 2) / img_h

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
bg.inputs[0].default_value = (1, 1, 1, 1)
bg.inputs[1].default_value = 0.1

# === 曝光调整 ===
bpy.context.scene.view_settings.exposure = 1.0
bpy.context.scene.view_settings.gamma = 1.0

# === 渲染循环：固定相机 + 模型旋转 + 平移 ===
all_poses = []

cnt = 0
for roll_deg in ROLL_ANGLES:
    roll_rad = math.radians(roll_deg)
    for pitch_deg in PITCH_ANGLES:
        pitch_rad = math.radians(pitch_deg)
        for yaw_deg in YAW_ANGLES:
            yaw_rad = math.radians(yaw_deg)
            for tx in X_TRANS:
                for ty in Y_TRANS:
                    for tz in Z_TRANS:
                        # 模型旋转
                        for obj in objs:
                            obj.rotation_euler = Euler((pitch_rad, roll_rad, yaw_rad), 'XYZ')
                            obj.location = Vector((tx, ty, tz)) + center  # 平移后位置

                        # 渲染输出
                        bpy.context.scene.render.image_settings.file_format = 'PNG'
                        filename = f"{model_name_without_ext}_{cnt:05d}.png"
                        bpy.context.scene.render.filepath = os.path.join(OUTPUT_DIR, filename)
                        bpy.ops.render.render(write_still=True)
                        
                        
                        frame_data = {
                            "frame_index": cnt,
                            "image_file": filename,
                            "roll_deg": roll_deg,
                            "pitch_deg": pitch_deg,
                            "yaw_deg": yaw_deg,
                            "translation": [tx, ty, tz],
                            "camera": {
                                "location": [round(cam_obj.location.x, 6),
                                             round(cam_obj.location.y, 6),
                                             round(cam_obj.location.z, 6)],
                                "rotation_euler_deg": [round(math.degrees(a), 4) for a in cam_obj.rotation_euler]
                            },
                            "object": {
                                "name": objs[0].name,
                                "location": [round(objs[0].location.x, 6),
                                             round(objs[0].location.y, 6),
                                             round(objs[0].location.z, 6)],
                                "rotation_euler_deg": [round(math.degrees(a), 4) for a in objs[0].rotation_euler]
                            }
                        }

                        # 添加到总列表
                        all_poses.append(frame_data)    
                        
                        cnt += 1

json_output_path = os.path.join(OUTPUT_DIR, f"{model_name_without_ext}_all_poses.json")
with open(json_output_path, 'w') as f:
    json.dump(all_poses, f, indent=2)

print(f"\n✅ All {len(all_poses)} poses saved to: {json_output_path}")