'''
Author: fanjin fanjin
Date: 2025-11-07 10:59:46
LastEditors: fanjin fanjin
LastEditTime: 2026-01-16 18:03:17
FilePath: /blender_pro/share_view.py
Description: 

验证存在公共视角，同时验证转换矩阵计算单应性矩阵的正确性

Copyright (c) 2025 by Frank, All Rights Reserved. 
'''


import json


import numpy as np
from scipy.spatial.transform import Rotation as R

def pose_dict_to_matrix(pose_dict, euler_order='XYZ'):
    """
    将包含位置和欧拉角（度）的字典转换为 4x4 齐次变换矩阵。

    参数:
        pose_dict (dict): 包含以下键的字典：
            - 'location': [x, y, z] （单位：米）
            - 'rotation_euler_deg': [rx, ry, rz] （单位：度）
        euler_order (str): 欧拉角旋转顺序，默认 'XYZ'（与 Blender 一致）

    返回:
        np.ndarray: 4x4 变换矩阵 (dtype=float64)
    """
    # 提取平移向量
    t = np.asarray(pose_dict['location'], dtype=np.float64)
    if t.shape != (3,):
        raise ValueError("Location must be a list/tuple/array of length 3.")

    # 提取欧拉角（度）
    euler_deg = np.asarray(pose_dict['rotation_euler_deg'], dtype=np.float64)
    if euler_deg.shape != (3,):
        raise ValueError("rotation_euler_deg must be a list/tuple/array of length 3.")

    # 转换为旋转矩阵
    rotation = R.from_euler(euler_order, euler_deg, degrees=True)
    R_mat = rotation.as_matrix()  # 3x3

    # 构建 4x4 齐次矩阵
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = R_mat
    T[:3, 3] = t

    return T



JSON_PATH = "/home/frank/data/gitlab/blender_pro/output/QR0001_rotate_all_poses.json"
with open(JSON_PATH, 'r') as f:
    data = json.load(f)
    
total_nums = len(data)

for i in range(total_nums):
    for j in range(i+1, total_nums):
        frame_i = data[i]
        frame_j = data[j]
        T_wc_i = pose_dict_to_matrix(frame_i["camera"])
        T_wc_j = pose_dict_to_matrix(frame_j["camera"])
        T_wo_i = pose_dict_to_matrix(frame_i["object"])
        T_wo_j = pose_dict_to_matrix(frame_j["object"])
        
        T_co_i = np.linalg.inv(T_wc_i) @ T_wo_i
        T_co_j = np.linalg.inv(T_wc_j) @ T_wo_j
        
        exit(0)
