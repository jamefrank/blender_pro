# convert_exr_to_tiff.py
import os
import glob
import OpenEXR
import Imath
import numpy as np
import tifffile

output_root = "/home/frank/data/gitlab/blender_pro/output_sim"
for exr_path in glob.glob(os.path.join(output_root, "**/mech_eye_depth_0000.exr"), recursive=True):
    tiff_path = exr_path.replace("_0000.exr", "_map.tiff")
    # 读取 Z 通道...
    # 写出 tiff...
    
    import sys
    try:
        import OpenEXR
        import Imath
        import tifffile
        import numpy as np
    except ImportError as e:
        print(f"❌ 缺少依赖库: {e}")
        print("请安装: pip install OpenEXR tifffile numpy")
        sys.exit(1)
        
    if not os.path.exists(exr_path):
        print(f"⚠️ 警告: EXR 文件不存在: {exr_path}")
    else:
        # 读取 EXR 的 Z 通道
        exr_file = OpenEXR.InputFile(exr_path)
        header = exr_file.header()
        dw = header['dataWindow']
        w = dw.max.x - dw.min.x + 1
        h = dw.max.y - dw.min.y + 1

        if 'R' not in header['channels']:
            raise ValueError("EXR 文件中没有 'Z' 深度通道！")

        z_bytes = exr_file.channel('R', Imath.PixelType(Imath.PixelType.FLOAT))
        depth = np.frombuffer(z_bytes, dtype=np.float32).reshape(h, w)*1000

        # 写出 float32 TIFF
        tifffile.imwrite(
            tiff_path,
            depth,
            photometric='minisblack',
            planarconfig='contig'
        )
        print(f"✅ 已保存 float32 深度图: {tiff_path}")
    
    print(f"Converted: {tiff_path}")