import os
from PIL import Image

# ================= 配置区域 =================
# 你的图片文件夹路径 (根据你的实际情况修改)
TARGET_FOLDER = 'static' 

# 压缩质量 (1-100)，建议 60-75。
# 60 是 "瘦身极限"，肉眼几乎看不出区别，但体积会极其小。
QUALITY = 60 
# ===========================================

def compress_images(directory):
    total_saved = 0
    count = 0
    
    print(f"🚀 开始在 [{directory}] 及其子文件夹中压缩图片...")
    
    # 遍历所有文件夹和子文件夹
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = file.lower().split('.')[-1]
            
            # 只处理 jpg, jpeg, png
            if file_ext in ['jpg', 'jpeg', 'png']:
                try:
                    # 1. 获取原始大小
                    original_size = os.path.getsize(file_path)
                    
                    # 2. 打开图片
                    with Image.open(file_path) as img:
                        # 如果是 PNG，检查是否需要转 JPG (PNG体积很大，如果不需要透明背景，转JPG能小几倍)
                        # 这里为了安全，我们只压缩，不改格式，避免代码报错
                        
                        # 3. 压缩并覆盖保存
                        # optimize=True 会自动去除多余元数据
                        if file_ext == 'png':
                            # PNG 压缩比较特殊
                            img.save(file_path, optimize=True, quality=QUALITY)
                        else:
                            # JPG/JPEG 压缩
                            img.save(file_path, optimize=True, quality=QUALITY)
                    
                    # 4. 计算节省了多少
                    new_size = os.path.getsize(file_path)
                    saved = original_size - new_size
                    if saved > 0:
                        total_saved += saved
                        print(f"✅ 已压缩: {file} | 节省: {saved/1024:.2f} KB")
                        count += 1
                    else:
                        print(f"➖ 跳过 (已是最优): {file}")
                        
                except Exception as e:
                    print(f"❌ 处理出错: {file} - {e}")

    print("="*30)
    print(f"🎉 处理完成！共压缩 {count} 张图片。")
    print(f"📉 总共为你节省了空间: {total_saved / 1024 / 1024:.2f} MB")
    print("="*30)

if __name__ == '__main__':
    compress_images(TARGET_FOLDER)