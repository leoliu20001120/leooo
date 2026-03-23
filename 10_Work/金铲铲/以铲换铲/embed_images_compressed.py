#!/usr/bin/env python3
"""
将图片压缩后转 Base64 内嵌到 HTML 中。
大图会被缩放到最大 1200px 宽度，JPEG 质量 75。
"""
import os
import base64
import json
import io

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_WIDTH = 1200
JPEG_QUALITY = 75

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[WARN] Pillow 未安装，尝试安装...")
    import subprocess
    subprocess.check_call(['pip3', 'install', 'Pillow', '-q'])
    from PIL import Image
    HAS_PIL = True

images_info = [
    {"path": "金铲铲的图片 3/不是铲子", "file": "544a26e7-2833-40d0-9cae-6bab2d18aec3.jpg"},
    {"path": "金铲铲的图片 3/不是铲子", "file": "9_2.jpg"},
    {"path": "金铲铲的图片 3/不是铲子", "file": "剖析狗狗常見疾病.jpg"},
    {"path": "金铲铲的图片 3/不是铲子", "file": "id14568797-shutterstock_2472092589.jpg"},
    {"path": "金铲铲的图片 3/是铲子但不符合金铲铲", "file": "20250117499e6f84b1694f86bd6c854b0a467e69_20250116bb7bc736ae2e499fb7f90c4747eaf55e.jpg"},
    {"path": "金铲铲的图片 3/是铲子但不符合金铲铲", "file": "647b3dff2d211f7102e9d2d802ee02ee-750-750C.jpg"},
    {"path": "金铲铲的图片 3/是铲子但不符合金铲铲", "file": "d04cf8aa6f4dbbdc.jpg"},
    {"path": "金铲铲的图片 3/是铲子但不符合金铲铲", "file": "Entrenching_tool_(AM_2007.55.1-5).jpg"},
    {"path": "金铲铲的图片 3/是铲子但不符合金铲铲", "file": "fClUdLEsXI.jpg"},
    {"path": "金铲铲的图片 3/是铲子但不符合金铲铲", "file": "gozney-acacia-wood-pizza-peel-erver-14-environment.jpg"},
    {"path": "金铲铲的图片 3/是铲子但不符合金铲铲", "file": "Pjc4XdNEkKdyBtQI4udnqg.jpg"},
    {"path": "金铲铲的图片 3/是铲子但不符合金铲铲", "file": "wKgAWGmNc_iAFFaGAA04Eu0oPWo848.jpg"},
    {"path": "金铲铲的图片 3/符合金铲铲/是金铲铲（无手工痕迹）", "file": "download.jpg"},
    {"path": "金铲铲的图片 3/符合金铲铲/是金铲铲（无手工痕迹）", "file": "images.jpg"},
    {"path": "金铲铲的图片 3/符合金铲铲/较优秀金铲铲（有手工痕迹）", "file": "04dd9d6d33423564deef21318a8f9fd.png"},
    {"path": "金铲铲的图片 3/符合金铲铲/较优秀金铲铲（有手工痕迹）", "file": "0e1ab4a4cdb7adc732d707d3c27d3dc.jpg"},
    {"path": "金铲铲的图片 3/符合金铲铲/较优秀金铲铲（有手工痕迹）", "file": "576a9497985bd7c5cab260797b347b8.jpg"},
    {"path": "金铲铲的图片 3/符合金铲铲/优秀金铲铲（强手工痕迹及创意）", "file": "02546eaf-603e-4d2b-a0fc-65bae37677d2.jpg"},
    {"path": "金铲铲的图片 3/符合金铲铲/优秀金铲铲（强手工痕迹及创意）", "file": "286acca8-ecbd-4a5e-91be-c5e0204f2493.jpg"},
    {"path": "金铲铲的图片 3/符合金铲铲/优秀金铲铲（强手工痕迹及创意）", "file": "35b8008e-eeb8-44d8-831e-80da4b5e4fa8.jpg"},
    {"path": "金铲铲的图片 3/符合金铲铲/优秀金铲铲（强手工痕迹及创意）", "file": "52b6d634-a146-49b5-abd1-76cccdc6bc4e.jpg"},
    {"path": "金铲铲的图片 3/符合金铲铲/优秀金铲铲（强手工痕迹及创意）", "file": "8720fb28c1d5a24230437bbf133d0c9.jpg"},
    {"path": "金铲铲的图片 3/符合金铲铲/优秀金铲铲（强手工痕迹及创意）", "file": "97edf1d9-f97a-4b57-ac6b-da06f021fd13.jpg"},
    {"path": "金铲铲的图片 3/符合金铲铲/优秀金铲铲（强手工痕迹及创意）", "file": "b16a5dcb-d41c-47d3-99e7-18fcc513a399.jpg"},
    {"path": "金铲铲的图片 3/符合金铲铲/优秀金铲铲（强手工痕迹及创意）", "file": "da9a0f0d-c9c2-49fe-972a-85f96729d55a.jpg"},
]

def compress_and_encode(filepath):
    """读取图片，压缩后转 base64 data URI"""
    orig_size = os.path.getsize(filepath) / 1024
    
    img = Image.open(filepath)
    
    # 处理 RGBA -> RGB
    if img.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = bg
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 缩放大图
    w, h = img.size
    if w > MAX_WIDTH:
        ratio = MAX_WIDTH / w
        new_h = int(h * ratio)
        img = img.resize((MAX_WIDTH, new_h), Image.LANCZOS)
    
    # 输出为 JPEG
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=JPEG_QUALITY, optimize=True)
    data = buf.getvalue()
    new_size = len(data) / 1024
    
    b64 = base64.b64encode(data).decode('utf-8')
    ratio_pct = new_size / orig_size * 100 if orig_size > 0 else 100
    
    print(f"  {os.path.basename(filepath)[:40]:40s} {orig_size:8.0f} KB → {new_size:6.0f} KB ({ratio_pct:.0f}%)")
    
    return f"data:image/jpeg;base64,{b64}"

def main():
    print("=" * 70)
    print("🔄 压缩图片并转 Base64 内嵌...")
    print(f"   最大宽度: {MAX_WIDTH}px, JPEG质量: {JPEG_QUALITY}")
    print("=" * 70)
    
    img_map = {}
    total_orig = 0
    total_new = 0
    
    for info in images_info:
        filepath = os.path.join(BASE_DIR, info['path'], info['file'])
        if not os.path.exists(filepath):
            name, ext = os.path.splitext(info['file'])
            converted = os.path.join(BASE_DIR, info['path'], f"{name}_converted.jpg")
            if os.path.exists(converted):
                filepath = converted
            else:
                print(f"  [WARN] 找不到: {info['file']}")
                continue
        
        key = info['path'] + '/' + info['file']
        try:
            orig_size = os.path.getsize(filepath) / 1024
            total_orig += orig_size
            
            img_map[key] = compress_and_encode(filepath)
            
            # 计算压缩后大小
            b64_data = img_map[key].split(',', 1)[1]
            new_size = len(base64.b64decode(b64_data)) / 1024
            total_new += new_size
        except Exception as e:
            print(f"  [ERR] {info['file']}: {e}")
    
    print(f"\n✅ 成功: {len(img_map)}/{len(images_info)} 张")
    print(f"📊 原始总大小: {total_orig/1024:.1f} MB → 压缩后: {total_new/1024:.1f} MB ({total_new/total_orig*100:.0f}%)")
    
    # 读取原始 HTML
    html_path = os.path.join(BASE_DIR, 'review_20pct_webui.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 构建 JS 映射
    b64_map_js = "const imageBase64Map = {\n"
    for key, val in img_map.items():
        b64_map_js += f"  {json.dumps(key)}: {json.dumps(val)},\n"
    b64_map_js += "};\n"
    
    new_get_image_path = """function getImagePath(item) {
  const key = item.path + "/" + item.file;
  if (imageBase64Map[key]) return imageBase64Map[key];
  return encodeURI(key);
}"""
    
    html = html.replace(
        'function getImagePath(item) {\n  return encodeURI(item.path + "/" + item.file);\n}',
        new_get_image_path
    )
    
    html = html.replace(
        '// ======== 渲染 ========',
        f'// ======== Base64 图片数据（压缩版）========\n{b64_map_js}\n// ======== 渲染 ========'
    )
    
    # 写入
    output_path = os.path.join(BASE_DIR, 'review_20pct_standalone.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    output_size = os.path.getsize(output_path) / 1024 / 1024
    print(f"\n📦 输出: review_20pct_standalone.html ({output_size:.1f} MB)")
    print(f"🎉 完成！发给任何人都能直接看到图片。")

if __name__ == '__main__':
    main()
