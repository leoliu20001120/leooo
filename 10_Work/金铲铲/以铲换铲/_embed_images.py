#!/usr/bin/env python3
"""
将 review_20pct_webui.html 中引用的图片压缩后转为 Base64 内嵌，
生成一个完全自包含的 HTML 文件，可以发给任何人直接打开。
"""

import os
import re
import base64
from io import BytesIO
from PIL import Image

# 配置
INPUT_HTML = "review_20pct_webui.html"
OUTPUT_HTML = "review_20pct_standalone.html"
MAX_WIDTH = 800
JPEG_QUALITY = 55

def compress_image_to_base64(img_path, max_width=MAX_WIDTH, quality=JPEG_QUALITY):
    """压缩图片并返回 base64 data URI"""
    try:
        with Image.open(img_path) as img:
            # 转为 RGB（处理 RGBA/P 等模式）
            if img.mode in ('RGBA', 'P', 'LA'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 缩放
            w, h = img.size
            if w > max_width:
                ratio = max_width / w
                new_h = int(h * ratio)
                img = img.resize((max_width, new_h), Image.LANCZOS)
            
            # 压缩为 JPEG
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            b64 = base64.b64encode(buffer.getvalue()).decode('ascii')
            
            size_kb = len(buffer.getvalue()) / 1024
            print(f"  ✓ {os.path.basename(img_path)}: {w}x{h} → {img.size[0]}x{img.size[1]}, {size_kb:.0f}KB")
            return f"data:image/jpeg;base64,{b64}"
    except Exception as e:
        print(f"  ✗ 失败: {img_path} - {e}")
        return None

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"📖 读取 {INPUT_HTML}...")
    with open(INPUT_HTML, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 提取所有图片条目的 path 和 file
    entries = re.findall(r'file:\s*"([^"]+)"[^}]*?path:\s*"([^"]+)"', html, re.DOTALL)
    if not entries:
        # 尝试反过来匹配
        entries_alt = re.findall(r'path:\s*"([^"]+)"[^}]*?file:\s*"([^"]+)"', html, re.DOTALL)
        # 转换为 (file, path) 格式
        entries = [(f, p) for p, f in entries_alt]
    
    print(f"🔍 找到 {len(entries)} 个图片条目")
    
    # 构建 file -> base64 映射
    b64_map = {}
    total_size = 0
    
    for filename, path in entries:
        # 尝试 _converted.jpg 版本
        base_name = os.path.splitext(filename)[0]
        converted = os.path.join(path, base_name + '_converted.jpg')
        original = os.path.join(path, filename)
        
        if os.path.exists(converted):
            img_path = converted
        elif os.path.exists(original):
            img_path = original
        else:
            print(f"  ⚠ 找不到: {original}")
            continue
        
        b64_data = compress_image_to_base64(img_path)
        if b64_data:
            b64_map[filename] = b64_data
            total_size += len(b64_data)
    
    print(f"\n📦 共处理 {len(b64_map)} 张图片，Base64 总大小: {total_size/1024/1024:.1f}MB")
    
    # 修改 HTML：
    # 1. 将 getImagePath 函数替换为从内嵌映射中获取
    # 2. 注入 base64 映射数据
    
    # 构建映射 JS 对象
    b64_js_entries = []
    for filename, b64_data in b64_map.items():
        # 转义文件名中的特殊字符
        safe_name = filename.replace('\\', '\\\\').replace('"', '\\"')
        b64_js_entries.append(f'  "{safe_name}": "{b64_data}"')
    
    b64_js = "const imageBase64Map = {\n" + ",\n".join(b64_js_entries) + "\n};"
    
    # 替换 getImagePath 函数
    new_getImagePath = """function getImagePath(item) {
  // 自包含版本：从内嵌 Base64 数据中获取图片
  if (imageBase64Map[item.file]) {
    return imageBase64Map[item.file];
  }
  // fallback：原始路径
  return encodeURI(item.path + "/" + item.file);
}"""
    
    # 在 reviewData 定义之前注入 base64 映射
    html = html.replace(
        "const reviewData = [",
        b64_js + "\n\nconst reviewData = ["
    )
    
    # 替换 getImagePath 函数
    old_func = """function getImagePath(item) {
  return encodeURI(item.path + "/" + item.file);
}"""
    html = html.replace(old_func, new_getImagePath)
    
    # 更新标题，标记为独立版本
    html = html.replace(
        "🔍 VLM（视觉语言模型）逐张看图评审 · 所有图片均为原图展示",
        "🔍 VLM 逐张看图评审 · 图片已内嵌（自包含版本，可离线查看）"
    )
    
    # 写入
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    
    output_size = os.path.getsize(OUTPUT_HTML) / 1024 / 1024
    print(f"\n✅ 生成完成: {OUTPUT_HTML}")
    print(f"📏 文件大小: {output_size:.1f}MB")
    print(f"🌐 可直接发送给任何人，用浏览器打开即可查看！")

if __name__ == "__main__":
    main()
