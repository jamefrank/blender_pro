# -*- encoding: utf-8 -*-
#@File    :   render_depth_rgb.py
#@Time    :   2026/02/10 14:51:43
#@Author  :   frank 
#@Email:
#@Description: 同时渲染出来深度图和RGB图

import bpy
import math
import os
import json
import numpy as np
import bmesh
from mathutils import Vector, Euler

# 配置输入输出
workpiece_name = "QR0010"
output_dir = "/home/frank/data/gitlab/blender_pro/output_sim"

# === 配置相机内参 ===
fx = 1815.0500318867137
fy = 1815.6071098689097
cx = 616.5651758986305
cy = 498.4238074205292
img_w = 1280
img_h = 1024

# 配置仿真位姿采样参数
CAMERA_DISTANCE = 0.6  # 相机距离模型中心（米）
ROLL_ANGLES = [0, 30, 60, 90, 120, 150] # du
PITCH_ANGLES = [0, 15, 30, 45, 60, 75, 90] # du
YAW_ANGLES = [0, 30, 60, 90, 120, 150] # du
X_TRANS = [0.0, 0.04, -0.04, 0.08, -0.08] # 物体在图像中左右移动
Y_TRANS = [0.0, 0.04, -0.04] # 图像放大缩小
Z_TRANS = [0.0, 0.04, -0.04] #  物体在图像中上下移动


# 创建仿真场景
# === 清空场景 ===
bpy.ops.wm.read_factory_settings(use_empty=True)

# === 导入模型 ===
BASE_DIR = "/home/frank/data/gitlab/blender_pro/QR"
MODEL_PATH = f"{BASE_DIR}/{workpiece_name}/{workpiece_name}_rotate.obj"
bpy.ops.import_scene.obj(filepath=MODEL_PATH)
# bpy.ops.import_scene.obj(filepath=MODEL_PATH, axis_forward='Y', axis_up='Z')

# #
# obj = bpy.context.selected_objects[0]
# obj.select_set(True)
# bpy.context.view_layer.objects.active = obj
# mesh = obj.data
# bm = bmesh.new()
# bm.from_mesh(mesh)
# bm.transform(obj.matrix_world)  # 转换到世界坐标（如果需要）
# bm.to_mesh(mesh)
# bm.free()
# points = np.array([v.co for v in mesh.vertices])
# POINTCLOUD_PATH = "./pointcloud.xyz"
# np.savetxt(POINTCLOUD_PATH, points, fmt="%.6f")
# print(f"✅ 点云已保存: {POINTCLOUD_PATH}")

# 选中所有的物体
objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
assert(len(objs) == 1)

# === 缩放模型从毫米到米 ===
for obj in objs:
    obj.scale = (0.001, 0.001, 0.001)
bpy.ops.object.transform_apply(scale=True)

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


# 打印物体初始位姿
bpy.context.view_layer.update() 
print("Workpiece Initial Pose:")
print(f"{center}")
bpy.context.view_layer.update() 
for obj in objs:
    print(f"{obj.name}")
    print(f"{obj.matrix_world}")

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

# 打印相机位姿
print("Camera Initial Pose:")
bpy.context.view_layer.update() 
print(cam_obj.matrix_world)
print(type(cam_obj.matrix_world))

# 启用深度通道
scene = bpy.context.scene
if len(scene.view_layers) == 0:
    view_layer = scene.view_layers.new(name="Main")
else:
    view_layer = scene.view_layers[0]
view_layer.use_pass_z = True

# 启用合成器
scene.use_nodes = True
tree = scene.node_tree
tree.nodes.clear()  # 清空默认节点

# 创建节点
rlayer = tree.nodes.new("CompositorNodeRLayers")
composite = tree.nodes.new("CompositorNodeComposite")  # 用于 RGB 输出
depth_output = tree.nodes.new("CompositorNodeOutputFile")

# 配置深度输出格式
depth_output.format.file_format = 'OPEN_EXR'
depth_output.format.color_mode = 'RGB'      # 单通道
depth_output.format.color_depth = '32'     # 32位浮点（保留真实深度值）
depth_output.format.exr_codec = 'NONE'

# 连接节点
tree.links.new(rlayer.outputs['Image'], composite.inputs['Image'])   # RGB → 默认输出
tree.links.new(rlayer.outputs['Depth'], depth_output.inputs[0])    # Depth → TIFF 输出


# 1️⃣ 设定渲染分辨率
scene = bpy.context.scene
scene.render.resolution_x = img_w
scene.render.resolution_y = img_h
scene.render.resolution_percentage = 100

# === 添加光照（固定，沿相机方向） ===
bpy.ops.object.light_add(type='SUN')
light = bpy.context.object
light.data.energy = 16.0
offset = 0.1
light.location = cam_obj.matrix_world.translation - cam_obj.matrix_world.to_quaternion() @ Vector((0, 0, offset))
light.rotation_euler = cam_obj.rotation_euler

# === 环境光 ===   整个场景被一个极微弱的白色“天光”均匀照亮，没有任何方向性，也不会产生阴影
if bpy.context.scene.world is None:
    bpy.context.scene.world = bpy.data.worlds.new("World")
bpy.context.scene.world.use_nodes = True
bg = bpy.context.scene.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (1, 1, 1, 1)
bg.inputs[1].default_value = 0.1

# === 曝光调整 ===  后期P图处理
bpy.context.scene.view_settings.exposure = 1.0
bpy.context.scene.view_settings.gamma = 1.0

# === 渲染循环：固定相机 + 模型旋转 + 平移 ===
all_poses = []

scene_cnt = 0
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

                        # # 渲染输出
                        scene_output_dir = os.path.join(output_dir, f"{scene_cnt:08d}")
                        # os.makedirs(scene_output_dir, exist_ok=True)
                        # bpy.context.scene.render.image_settings.file_format = 'PNG'
                        # bpy.context.scene.render.filepath = os.path.join(scene_output_dir, "mech_eye_image_2d.png")
                        
                        # depth_output.base_path = scene_output_dir + "/"
                        # depth_output.file_slots[0].path = "mech_eye_depth_"  # → 生成 mech_eye_depth_0000.exr
                        
                        # # 渲染
                        # bpy.context.scene.frame_set(0)
                        # bpy.ops.render.render(write_still=True)
                        
                        # 保存位姿
                        bpy.context.view_layer.update() 
                        print(f"{obj.matrix_world}")
                        print(np.linalg.inv(np.array(cam_obj.matrix_world)))
                        gl2cv = np.array([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]])
                        obj_rt = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]])
                        workpiece_to_frame = gl2cv @ np.linalg.inv(np.array(cam_obj.matrix_world)) @ np.array(obj.matrix_world) @ np.linalg.inv(obj_rt)
                        workpiece_to_frame[:3, 3] *= 1000
                        json_data = {
                            "camera_infos": {
                                "fx": fx,
                                "fy": fy,
                                "cx": cx,
                                "cy": cy,
                                "width": img_w,
                                "height": img_h,
                                "distortion_coefficients": [
                                    0.0,
                                    0.0,
                                    0.0,
                                    0.0,
                                    0.0
                                ]
                            },
                            "annotations": [
                                {
                                    "workpiece_name": workpiece_name,
                                    "workpiece_to_frame": workpiece_to_frame.tolist()
                                }
                            ]
                        }
                        
                        json_output_path = os.path.join(scene_output_dir, "annotations.json")
                        with open(json_output_path, 'w') as f:
                            json.dump(json_data, f, indent=2)
                        
                        print(f"✅ Pose {scene_cnt:08d} saved to: {json_output_path}")
                        # exit(0)
                        
                        scene_cnt += 1



# print(f"\n✅ All {len(all_poses)} poses saved to: {json_output_path}")