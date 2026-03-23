#!/usr/bin/env python3
"""
将 review_20pct_webui.html 中的图片相对路径替换为 Base64 内嵌数据，
生成一个自包含的 HTML 文件，发给任何人都能直接看到图片。
"""
import os
import base64
import json
import re
import mimetypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 25张抽样图片的信息（路径相对于 BASE_DIR）
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

def get_mime_type(filename):
    """根据文件扩展名获取 MIME 类型"""
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.avif': 'image/avif',
        '.bmp': 'image/bmp',
        '.svg': 'image/svg+xml',
    }
    return mime_map.get(ext, 'image/jpeg')

def image_to_base64(filepath):
    """读取图片文件，转成 base64 data URI"""
    mime = get_mime_type(filepath)
    with open(filepath, 'rb') as f:
        data = base64.b64encode(f.read()).decode('utf-8')
    return f"data:{mime};base64,{data}"

def build_image_map():
    """构建 path/file -> base64 data URI 的映射"""
    img_map = {}
    for info in images_info:
        filepath = os.path.join(BASE_DIR, info['path'], info['file'])
        # 有些特殊格式可能有 _converted.jpg 版本
        if not os.path.exists(filepath):
            # 尝试 _converted.jpg
            name, ext = os.path.splitext(info['file'])
            converted = os.path.join(BASE_DIR, info['path'], f"{name}_converted.jpg")
            if os.path.exists(converted):
                filepath = converted
            else:
                print(f"[WARN] 找不到文件: {filepath}")
                continue
        
        key = info['path'] + '/' + info['file']
        try:
            img_map[key] = image_to_base64(filepath)
            size_kb = os.path.getsize(filepath) / 1024
            print(f"[OK] {info['file'][:40]:40s} ({size_kb:.0f} KB)")
        except Exception as e:
            print(f"[ERR] {info['file']}: {e}")
    
    return img_map

def main():
    print("=" * 60)
    print("🔄 开始转换图片为 Base64 内嵌...")
    print("=" * 60)
    
    # 1. 构建图片映射
    img_map = build_image_map()
    print(f"\n✅ 成功转换 {len(img_map)}/{len(images_info)} 张图片")
    
    # 2. 读取原始 HTML
    html_path = os.path.join(BASE_DIR, 'review_20pct_webui.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 3. 修改 HTML：将 getImagePath 函数改为返回 base64 数据
    # 策略：在 reviewData 的每个 item 中添加 base64_img 字段，
    # 然后修改 getImagePath 函数使用它
    
    # 构建 base64 数据的 JS 映射
    b64_js_map = {}
    for info in images_info:
        key = info['path'] + '/' + info['file']
        if key in img_map:
            b64_js_map[key] = img_map[key]
    
    # 在 reviewData 之后插入 base64 映射
    b64_map_js = "const imageBase64Map = {\n"
    for key, val in b64_js_map.items():
        # 用 JSON 转义 key
        b64_map_js += f"  {json.dumps(key)}: {json.dumps(val)},\n"
    b64_map_js += "};\n"
    
    # 替换 getImagePath 函数
    new_get_image_path = """function getImagePath(item) {
  const key = item.path + "/" + item.file;
  if (imageBase64Map[key]) return imageBase64Map[key];
  return encodeURI(key);
}"""
    
    # 在 reviewData 定义结束后插入 base64 映射
    html = html.replace(
        'function getImagePath(item) {\n  return encodeURI(item.path + "/" + item.file);\n}',
        new_get_image_path
    )
    
    # 在 "// ======== 渲染 ========" 前插入 base64 映射
    html = html.replace(
        '// ======== 渲染 ========',
        f'// ======== Base64 图片数据 ========\n{b64_map_js}\n// ======== 渲染 ========'
    )
    
    # 4. 写入新 HTML
    output_path = os.path.join(BASE_DIR, 'review_20pct_standalone.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    output_size = os.path.getsize(output_path)
    print(f"\n📦 输出文件: review_20pct_standalone.html")
    print(f"📏 文件大小: {output_size / 1024 / 1024:.1f} MB")
    print(f"\n🎉 完成！这个 HTML 文件可以直接发送给任何人查看。")

if __name__ == '__main__':
    main()
