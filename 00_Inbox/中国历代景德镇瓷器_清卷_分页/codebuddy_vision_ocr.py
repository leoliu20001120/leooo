#!/usr/bin/env python3
"""
通过 CodeBuddy API 网关调用混元视觉模型，对瓷器图册 PNG 进行 OCR 识别。

API 网关: https://copilot.tencent.com/v2/chat/completions
模型: hunyuan-2.0-instruct (唯一支持视觉/图片输入的模型)
认证: Bearer ck_xxx (CodeBuddy API Key)

后处理: 用 deepseek-v3 做繁简转换和质量修正
"""

import json
import base64
import os
import sys
import time
import urllib.request
import ssl
import glob
import re

# ============ 配置 ============
API_KEY = "ck_fihf3pjaejgg.ju4LGgCQyGb2OzrALgmiIsf3Gc2vlS5kMPiSnY-oT4c"
API_URL = "https://copilot.tencent.com/v2/chat/completions"
MODEL = "hunyuan-2.0-instruct"
MAX_TOKENS = 2000

# 工作目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PNG_DIR = os.path.join(SCRIPT_DIR, "png_pages")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "vision_ocr_batches")

# OCR 提示词
OCR_PROMPT = """你是一个专业的瓷器图册OCR识别助手。请仔细识别这张图片中的所有文字内容。

这是一本关于中国历代景德镇瓷器（清卷）的图册页面。请提取以下信息：

1. **瓷器编号**（页面上的数字编号，如 015、016 等）
2. **瓷器名称**（中文名称）
3. **英文名称**（如有）
4. **朝代**（如 清·顺治、清·康熙 等）
5. **尺寸**（如有）
6. **收藏机构**（如有）
7. **瓷器介绍/描述**（完整的文字描述）

如果这个页面只有图片没有文字描述，请标注为"纯图片页"。

**重要**：所有输出必须使用简体中文（不要用繁体中文）。

请以JSON格式输出，格式如下：
{
    "number": "编号",
    "name": "瓷器名称（简体中文）",
    "english_name": "英文名称",
    "dynasty": "朝代",
    "dimensions": "尺寸",
    "collection": "收藏机构",
    "description": "完整的瓷器介绍（简体中文）",
    "is_image_only": false
}

如果是纯图片页（没有文字描述），则：
{
    "number": "编号（如有）",
    "name": "瓷器名称（根据图片判断，简体中文）",
    "english_name": "",
    "dynasty": "",
    "dimensions": "",
    "collection": "",
    "description": "",
    "is_image_only": true
}

只输出JSON，不要输出其他内容。"""

SSL_CTX = ssl.create_default_context()


def call_vision_api(image_path: str, retry: int = 2) -> dict:
    """调用 CodeBuddy API 网关的混元视觉能力"""
    # 读取图片并编码
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    
    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                {"type": "text", "text": OCR_PROMPT}
            ]
        }],
        "max_tokens": MAX_TOKENS,
        "stream": True,
        "temperature": 0.1  # 低温度，更精确
    }
    
    data = json.dumps(payload).encode()
    
    for attempt in range(retry):
        try:
            req = urllib.request.Request(API_URL, data=data, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            })
            resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=120)
            
            # 解析 SSE 流
            full_text = ""
            for line in resp:
                line = line.decode().strip()
                if line.startswith("data: "):
                    payload_str = line[6:]
                    if payload_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_text += content
                    except json.JSONDecodeError:
                        pass
            
            return {"success": True, "text": full_text}
        
        except Exception as e:
            err_body = ""
            if hasattr(e, "read"):
                err_body = e.read().decode()[:300]
            print(f"  [重试 {attempt+1}/{retry}] 错误: {e} | {err_body}")
            if attempt < retry - 1:
                time.sleep(3)
    
    return {"success": False, "text": "", "error": str(e)}


def parse_json_response(text: str) -> dict:
    """从模型响应中提取 JSON"""
    # 尝试直接解析
    text = text.strip()
    
    # 移除可能的 markdown 代码块标记
    if text.startswith("```"):
        # 找到第一个换行
        first_nl = text.index("\n")
        last_backtick = text.rfind("```")
        if last_backtick > first_nl:
            text = text[first_nl+1:last_backtick].strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试找 JSON 对象
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    
    return {"raw_text": text, "parse_error": True}


def get_png_files(directory: str) -> list:
    """获取排序后的 PNG 文件列表"""
    files = glob.glob(os.path.join(directory, "第*页.png"))
    # 按页码排序
    def sort_key(f):
        match = re.search(r'第(\d+)页', os.path.basename(f))
        return int(match.group(1)) if match else 0
    return sorted(files, key=sort_key)


def main():
    # 参数解析
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0  # 0 = 全部
    start_page = int(sys.argv[2]) if len(sys.argv) > 2 else 0  # 从第几页开始
    
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 获取文件列表
    png_files = get_png_files(PNG_DIR)
    
    if not png_files:
        print("❌ 未找到 PNG 文件！")
        return
    
    print(f"📂 找到 {len(png_files)} 个 PNG 文件")
    
    # 过滤起始页
    if start_page > 0:
        png_files = [f for f in png_files if int(re.search(r'第(\d+)页', os.path.basename(f)).group(1)) >= start_page]
        print(f"📌 从第 {start_page} 页开始，剩余 {len(png_files)} 个文件")
    
    # 限制数量
    if limit > 0:
        png_files = png_files[:limit]
        print(f"🔢 本次处理前 {limit} 个文件")
    
    # 加载已有结果（断点续传）
    all_results_file = os.path.join(SCRIPT_DIR, "codebuddy_ocr_results.json")
    existing_results = {}
    if os.path.exists(all_results_file):
        with open(all_results_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                existing_results[item.get("page")] = item
        print(f"📋 已有 {len(existing_results)} 条历史结果")
    
    results = []
    total = len(png_files)
    
    for i, png_file in enumerate(png_files):
        page_name = os.path.basename(png_file)
        page_num = int(re.search(r'第(\d+)页', page_name).group(1))
        
        # 检查是否已处理
        if page_name in existing_results:
            print(f"[{i+1}/{total}] ⏭️  {page_name} - 已有结果，跳过")
            results.append(existing_results[page_name])
            continue
        
        print(f"[{i+1}/{total}] 🔍 处理 {page_name}...", end=" ", flush=True)
        
        # 调用 API
        start_time = time.time()
        response = call_vision_api(png_file)
        elapsed = time.time() - start_time
        
        if response["success"]:
            parsed = parse_json_response(response["text"])
            result = {
                "page": page_name,
                "page_number": page_num,
                **parsed
            }
            results.append(result)
            
            name = parsed.get("name", "")
            is_img_only = parsed.get("is_image_only", False)
            status = "📷 纯图片页" if is_img_only else f"✅ {name}"
            print(f"{status} ({elapsed:.1f}s)")
        else:
            result = {
                "page": page_name,
                "page_number": page_num,
                "error": response.get("error", "unknown"),
                "is_image_only": False
            }
            results.append(result)
            print(f"❌ 失败: {response.get('error', '')} ({elapsed:.1f}s)")
        
        # 每处理一个就保存（防止中断丢数据）
        # 合并已有结果
        merged = dict(existing_results)
        for r in results:
            merged[r["page"]] = r
        
        all_results = sorted(merged.values(), key=lambda x: x.get("page_number", 0))
        with open(all_results_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        # 避免 API 限流
        time.sleep(1)
    
    # 最终统计
    print(f"\n{'='*50}")
    print(f"✅ 完成！共处理 {len(results)} 页")
    
    success_count = sum(1 for r in results if "error" not in r)
    image_only = sum(1 for r in results if r.get("is_image_only", False))
    with_desc = sum(1 for r in results if not r.get("is_image_only", False) and "error" not in r)
    
    print(f"  成功: {success_count}")
    print(f"  有描述: {with_desc}")
    print(f"  纯图片: {image_only}")
    print(f"  失败: {len(results) - success_count}")
    print(f"\n📄 结果保存至: {all_results_file}")


if __name__ == "__main__":
    main()
