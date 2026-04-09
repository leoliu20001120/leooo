#!/usr/bin/env python3
"""
合并所有 OCR 来源的结果，生成最终版 final_ocr_results_v2.json

优先级（同一页面有多个来源时）:
1. claude_vision_ocr_results.json (Claude 金标准，简体中文)
2. codebuddy_ocr_results.json (混元 Vision，简体中文)  
3. final_ocr_results.json 中 source=vision 的条目（混元 Vision 早期，繁体中文）
4. final_ocr_results.json 中 source=tesseract 的条目（传统 OCR，质量最差）

合并规则：
- 有 Claude 结果的页面，直接用 Claude 结果
- 有混元 Vision 结果的页面，用混元结果（已经是简体中文）
- 只有旧 vision 结果的页面，保留但标记需人工校对
- 只有 tesseract 结果的页面，保留但标记需人工校对
"""

import json
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def normalize_page_key(item):
    """统一 page 为整数"""
    page = item.get("page")
    if isinstance(page, int):
        return page
    if isinstance(page, str):
        match = re.search(r'(\d+)', page)
        if match:
            return int(match.group(1))
    return 0


def load_json(filename):
    """安全加载 JSON 文件"""
    filepath = os.path.join(SCRIPT_DIR, filename)
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def main():
    # 加载各来源
    claude_data = load_json("claude_vision_ocr_results.json")
    hunyuan_data = load_json("codebuddy_ocr_results.json")
    final_data = load_json("final_ocr_results.json")
    
    print(f"Claude 结果: {len(claude_data)} 条")
    print(f"混元 Vision 结果: {len(hunyuan_data)} 条")
    print(f"旧 Final 结果: {len(final_data)} 条")
    
    # 按 page 建索引
    merged = {}
    
    # 第4优先级: tesseract
    for item in final_data:
        page = normalize_page_key(item)
        if page > 0 and item.get("source") == "tesseract":
            item["page"] = page
            item["quality_tier"] = "low"
            merged[page] = item
    
    # 第3优先级: 旧 vision
    for item in final_data:
        page = normalize_page_key(item)
        if page > 0 and item.get("source") == "vision":
            item["page"] = page
            item["quality_tier"] = "medium"
            merged[page] = item
    
    # 第2优先级: 混元 Vision (新跑)
    for item in hunyuan_data:
        page = normalize_page_key(item)
        if page > 0:
            # 标准化字段名
            normalized = {
                "page": page,
                "page_number": item.get("number", item.get("page_number", "")),
                "title": item.get("name", item.get("title", "")),
                "dynasty": item.get("dynasty", ""),
                "dimensions": item.get("dimensions", ""),
                "collection": item.get("collection", ""),
                "description": item.get("description", ""),
                "english": item.get("english_name", item.get("english", "")),
                "is_image_only": item.get("is_image_only", False),
                "source": "hunyuan_vision",
                "quality_tier": "high"
            }
            merged[page] = normalized
    
    # 第1优先级: Claude 金标准
    for item in claude_data:
        page = normalize_page_key(item)
        if page > 0:
            item["page"] = page
            if "quality_tier" not in item:
                item["quality_tier"] = "gold"
            if "source" not in item:
                item["source"] = "claude"
            merged[page] = item
    
    # 排序输出
    all_sorted = sorted(merged.values(), key=lambda x: x.get("page", 0))
    
    output_file = os.path.join(SCRIPT_DIR, "final_ocr_results_v2.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_sorted, f, ensure_ascii=False, indent=2)
    
    # 统计
    tier_counts = {}
    source_counts = {}
    for r in all_sorted:
        t = r.get("quality_tier", "unknown")
        s = r.get("source", "unknown")
        tier_counts[t] = tier_counts.get(t, 0) + 1
        source_counts[s] = source_counts.get(s, 0) + 1
    
    has_desc = sum(1 for r in all_sorted if r.get("description") and len(r.get("description", "")) > 10)
    has_title = sum(1 for r in all_sorted if r.get("title"))
    has_dynasty = sum(1 for r in all_sorted if r.get("dynasty"))
    
    print(f"\n{'='*50}")
    print(f"✅ 合并完成！共 {len(all_sorted)} 条")
    print(f"\n质量分布: {tier_counts}")
    print(f"来源分布: {source_counts}")
    print(f"\n有标题: {has_title}")
    print(f"有朝代: {has_dynasty}")
    print(f"有描述(>10字): {has_desc}")
    print(f"\n📄 保存至: {output_file}")


if __name__ == "__main__":
    main()
