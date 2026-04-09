#!/usr/bin/env python3
"""
OCR 后处理脚本：用 deepseek-v3 将混元 OCR 结果从繁体转简体、修复乱码、格式标准化。

工作流：
1. 读取 codebuddy_ocr_results.json（混元视觉 OCR 原始结果）
2. 读取 claude_vision_ocr_results.json（Claude OCR 金标准，优先使用）
3. 对混元结果逐条调用 deepseek-v3 做后处理
4. 合并 Claude 金标准 + 处理后的混元结果 + 原有 final 结果
5. 输出到 final_ocr_results_v2.json
"""

import json
import os
import sys
import time
import urllib.request
import ssl
import re

# ============ 配置 ============
API_KEY = "ck_fihf3pjaejgg.ju4LGgCQyGb2OzrALgmiIsf3Gc2vlS5kMPiSnY-oT4c"
API_URL = "https://copilot.tencent.com/v2/chat/completions"
MODEL = "deepseek-v3"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SSL_CTX = ssl.create_default_context()

POSTPROCESS_PROMPT = """你是一个专业的中文古陶瓷文献编辑。请对以下 OCR 识别结果进行后处理：

1. **繁体转简体**：将所有繁体中文转为简体中文
2. **修复乱码**：修复 OCR 产生的乱码文字（如 "RASA HRA" 应为具体汉字，"SHO" 可能是"撇口"等）
3. **补全缺失字段**：如果标题中能推断出朝代信息，请补全 dynasty 字段
4. **格式标准化**：统一尺寸格式为 "高XXcm 口径XXcm 底径XXcm"

原始数据（JSON）：
{input_json}

请输出修正后的 JSON，保持相同的字段结构。只输出 JSON，不要输出其他内容。"""


def call_text_api(prompt: str, retry: int = 2) -> str:
    """调用 deepseek-v3 文本模型"""
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
        "stream": True,
        "temperature": 0.1
    }
    
    data = json.dumps(payload).encode()
    
    for attempt in range(retry):
        try:
            req = urllib.request.Request(API_URL, data=data, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            })
            resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=60)
            
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
            
            return full_text
        
        except Exception as e:
            err_body = ""
            if hasattr(e, "read"):
                try:
                    err_body = e.read().decode()[:300]
                except:
                    pass
            print(f"  [重试 {attempt+1}/{retry}] 错误: {e} | {err_body}")
            if attempt < retry - 1:
                time.sleep(3)
    
    return ""


def parse_json_from_text(text: str) -> dict:
    """从模型输出中提取 JSON"""
    text = text.strip()
    
    if text.startswith("```"):
        first_nl = text.index("\n")
        last_backtick = text.rfind("```")
        if last_backtick > first_nl:
            text = text[first_nl+1:last_backtick].strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    
    return None


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    
    # 加载各来源数据
    # 1. Claude 金标准结果
    claude_file = os.path.join(SCRIPT_DIR, "claude_vision_ocr_results.json")
    claude_results = {}
    if os.path.exists(claude_file):
        data = json.load(open(claude_file, "r", encoding="utf-8"))
        for item in data:
            claude_results[item["page"]] = item
        print(f"📋 Claude 金标准: {len(claude_results)} 条")
    
    # 2. 混元视觉 OCR 结果
    hunyuan_file = os.path.join(SCRIPT_DIR, "codebuddy_ocr_results.json")
    hunyuan_results = {}
    if os.path.exists(hunyuan_file):
        data = json.load(open(hunyuan_file, "r", encoding="utf-8"))
        for item in data:
            if isinstance(item.get("page"), str):
                # page 是文件名格式
                match = re.search(r'(\d+)', item["page"])
                if match:
                    page_num = int(match.group(1))
                    hunyuan_results[page_num] = item
            else:
                hunyuan_results[item["page"]] = item
        print(f"📋 混元 OCR: {len(hunyuan_results)} 条")
    
    # 3. 现有 final 结果（tesseract + vision 混合）
    final_file = os.path.join(SCRIPT_DIR, "final_ocr_results.json")
    final_results = {}
    if os.path.exists(final_file):
        data = json.load(open(final_file, "r", encoding="utf-8"))
        for item in data:
            final_results[item["page"]] = item
        print(f"📋 现有 Final: {len(final_results)} 条")
    
    # 4. 已处理的后处理结果（断点续传）
    output_file = os.path.join(SCRIPT_DIR, "final_ocr_results_v2.json")
    processed_results = {}
    if os.path.exists(output_file):
        data = json.load(open(output_file, "r", encoding="utf-8"))
        for item in data:
            processed_results[item["page"]] = item
        print(f"📋 已后处理: {len(processed_results)} 条")
    
    # 确定需要处理的页面
    # 优先级: Claude > 混元(需后处理) > 原有vision > 原有tesseract(需后处理)
    all_pages = sorted(set(list(final_results.keys()) + list(hunyuan_results.keys()) + list(claude_results.keys())))
    
    # Claude 结果直接使用，不需要后处理
    for page, item in claude_results.items():
        processed_results[page] = item
    
    # 需要后处理的页面（来自 tesseract 或混元 vision）
    need_postprocess = []
    for page in all_pages:
        if page in processed_results and processed_results[page].get("source") in ("claude", "postprocessed"):
            continue  # 已有高质量结果
        
        # 选择最佳原始数据
        if page in hunyuan_results:
            need_postprocess.append((page, hunyuan_results[page], "hunyuan"))
        elif page in final_results:
            item = final_results[page]
            if item.get("source") == "vision":
                need_postprocess.append((page, item, "vision"))
            else:
                need_postprocess.append((page, item, "tesseract"))
    
    print(f"\n🔄 需要后处理: {len(need_postprocess)} 条")
    
    if limit > 0:
        need_postprocess = need_postprocess[:limit]
        print(f"🔢 本次处理前 {limit} 条")
    
    # 开始后处理
    for i, (page, item, src) in enumerate(need_postprocess):
        print(f"[{i+1}/{len(need_postprocess)}] 📝 第{page:03d}页 ({src})...", end=" ", flush=True)
        
        # 准备输入
        input_json = json.dumps(item, ensure_ascii=False, indent=2)
        prompt = POSTPROCESS_PROMPT.format(input_json=input_json)
        
        start_time = time.time()
        response = call_text_api(prompt)
        elapsed = time.time() - start_time
        
        if response:
            parsed = parse_json_from_text(response)
            if parsed:
                parsed["page"] = page
                parsed["source"] = "postprocessed"
                parsed["original_source"] = src
                processed_results[page] = parsed
                title = parsed.get("title", "")
                print(f"✅ {title} ({elapsed:.1f}s)")
            else:
                # 解析失败，保留原始数据但标记
                item["postprocess_failed"] = True
                processed_results[page] = item
                print(f"⚠️ JSON 解析失败 ({elapsed:.1f}s)")
        else:
            item["postprocess_failed"] = True
            processed_results[page] = item
            print(f"❌ API 调用失败 ({elapsed:.1f}s)")
        
        # 每条都保存（断点续传）
        all_sorted = sorted(processed_results.values(), key=lambda x: x.get("page", 0))
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_sorted, f, ensure_ascii=False, indent=2)
        
        time.sleep(0.5)  # 避免限流
    
    # 最终统计
    all_sorted = sorted(processed_results.values(), key=lambda x: x.get("page", 0))
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_sorted, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✅ 完成！共 {len(all_sorted)} 条记录")
    
    source_counts = {}
    for r in all_sorted:
        s = r.get("source", "unknown")
        source_counts[s] = source_counts.get(s, 0) + 1
    print(f"来源分布: {source_counts}")
    print(f"\n📄 结果保存至: {output_file}")


if __name__ == "__main__":
    main()
