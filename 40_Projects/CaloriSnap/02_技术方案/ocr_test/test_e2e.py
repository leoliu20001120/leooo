#!/usr/bin/env python3
"""
CaloriSnap — 端到端测试脚本
完整流程：拍照(图片) → OCR识别 → LLM结构化提取 → 热量计算

使用方法:
    python test_e2e.py --image sample_labels/test1.jpg
    python test_e2e.py --dir sample_labels/ --report results/e2e_report.json
    python test_e2e.py --demo  # 用模拟 OCR 文本测试计算链路
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional

import click

from calori_calculator import CaloriCalculator
from test_ocr import ocr_multimodal_llm, ocr_tencent_cloud
from test_llm_extract import extract_with_llm, DEMO_SAMPLES


def e2e_with_image(image_path: str, method: str = "llm", calculator: Optional[CaloriCalculator] = None) -> dict:
    """
    端到端：图片 → OCR → 结构化提取 → 热量计算
    
    method:
        "llm" — 多模态大模型一步到位（推荐）
        "tencent+llm" — 腾讯云OCR + LLM提取
    """
    start_total = time.time()
    result = {"image": image_path, "method": method, "steps": {}}

    if method == "llm":
        # 路径 B: 多模态大模型直接识别
        step1 = ocr_multimodal_llm(image_path)
        result["steps"]["multimodal_ocr"] = step1

        if "error" in step1:
            result["error"] = step1["error"]
            return result

        extracted = step1.get("extracted", {})

    elif method == "tencent+llm":
        # 路径 A: 腾讯云 OCR → LLM 结构化提取
        step1 = ocr_tencent_cloud(image_path)
        result["steps"]["ocr"] = step1

        if "error" in step1:
            result["error"] = step1["error"]
            return result

        # 用 LLM 从 OCR 文字中提取结构化信息
        step2 = extract_with_llm(step1["full_text"])
        result["steps"]["llm_extract"] = step2

        if "error" in step2:
            result["error"] = step2["error"]
            return result

        extracted = step2.get("extracted", {})

    else:
        result["error"] = f"未知方法: {method}"
        return result

    # 热量计算
    if calculator is None:
        db_path = Path(__file__).parent / "drink_db.json"
        calculator = CaloriCalculator(str(db_path) if db_path.exists() else None)

    calc_result = calculator.calculate(extracted)
    result["steps"]["calculation"] = calc_result
    result["final"] = {
        "brand": calc_result["matched_brand"],
        "drink": calc_result["matched_drink"],
        "total_calories": calc_result["total_calories"],
        "match_type": calc_result["match_type"],
        "equivalents": calc_result["display"]["equivalents"],
    }

    result["total_elapsed"] = round(time.time() - start_total, 3)
    return result


def e2e_with_text(ocr_text: str, calculator: Optional[CaloriCalculator] = None) -> dict:
    """
    简化端到端：OCR文字 → LLM结构化提取 → 热量计算
    用于离线测试计算链路
    """
    start = time.time()

    # 尝试调用 LLM，如果没有 API Key 就用简单规则
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        llm_result = extract_with_llm(ocr_text)
        if "error" not in llm_result:
            extracted = llm_result.get("extracted", {})
        else:
            extracted = simple_rule_extract(ocr_text)
    else:
        extracted = simple_rule_extract(ocr_text)

    if calculator is None:
        db_path = Path(__file__).parent / "drink_db.json"
        calculator = CaloriCalculator(str(db_path) if db_path.exists() else None)

    calc_result = calculator.calculate(extracted)
    elapsed = round(time.time() - start, 3)

    return {
        "ocr_text": ocr_text,
        "extracted": extracted,
        "calculation": calc_result,
        "formatted": calculator.format_result(calc_result),
        "elapsed": elapsed,
    }


def simple_rule_extract(ocr_text: str) -> dict:
    """
    简单规则提取（不调用 LLM 的备选方案）
    用于离线测试和兜底
    """
    lines = [l.strip() for l in ocr_text.strip().split("\n") if l.strip()]
    result = {
        "brand": None, "drink_name": None,
        "size": None, "sugar_level": None,
        "temperature": None, "toppings": []
    }

    # 品牌关键词映射
    brand_keywords = {
        "瑞幸": "瑞幸咖啡", "luckin": "瑞幸咖啡",
        "星巴克": "星巴克", "starbucks": "星巴克",
        "喜茶": "喜茶", "heytea": "喜茶",
        "霸王茶姬": "霸王茶姬", "chagee": "霸王茶姬",
        "茶百道": "茶百道", "chapanda": "茶百道",
        "奈雪": "奈雪的茶", "nayuki": "奈雪的茶",
        "蜜雪": "蜜雪冰城", "mixue": "蜜雪冰城",
        "古茗": "古茗",
    }

    # 杯型关键词
    size_keywords = {
        "小杯": "小杯", "中杯": "中杯", "大杯": "大杯", "超大杯": "超大杯",
        "tall": "中杯", "grande": "大杯", "venti": "超大杯",
    }

    # 糖度关键词
    sugar_keywords = [
        "无糖", "去糖", "不另外加糖", "微糖", "少糖", "半糖",
        "正常糖", "全糖", "标准糖",
        "一分甜", "三分甜", "五分甜", "七分甜", "十分甜",
        "少少少甜", "少少甜", "少甜", "多甜",
    ]

    # 温度关键词
    temp_keywords = {
        "冰": "冰", "热": "热", "少冰": "少冰", "去冰": "去冰",
        "常温": "常温", "正常冰": "正常冰",
        "iced": "冰", "hot": "热",
    }

    full_text = " ".join(lines).lower()

    # 识别品牌
    for kw, brand in brand_keywords.items():
        if kw.lower() in full_text:
            result["brand"] = brand
            break

    # 识别杯型
    for kw, size in size_keywords.items():
        if kw.lower() in full_text:
            result["size"] = size
            break

    # 识别糖度
    for kw in sugar_keywords:
        if kw in full_text:
            result["sugar_level"] = kw
            break

    # 识别温度
    for kw, temp in temp_keywords.items():
        if kw.lower() in full_text:
            result["temperature"] = temp
            break

    # 识别加料（以 + 开头的）
    for line in lines:
        if line.startswith("+"):
            topping = line.lstrip("+").strip()
            if topping:
                result["toppings"].append(topping)

    # 饮品名：去掉品牌行、杯型行、加料行、序号行后的第一行
    skip_keywords = list(brand_keywords.keys()) + list(size_keywords.keys()) + ["#", "+"]
    for line in lines:
        line_lower = line.lower()
        is_skip = any(kw.lower() in line_lower for kw in skip_keywords)
        is_sugar = any(kw in line for kw in sugar_keywords)
        is_temp = any(kw.lower() in line_lower for kw in temp_keywords.keys())
        if not is_skip and not is_sugar and not is_temp and not line.startswith("#") and not line.startswith("+"):
            if not result["drink_name"]:
                result["drink_name"] = line

    return result


@click.command()
@click.option("--image", "-i", type=click.Path(exists=True), help="单张图片路径")
@click.option("--dir", "-d", "directory", type=click.Path(exists=True), help="图片目录")
@click.option("--method", "-m", type=click.Choice(["llm", "tencent+llm"]), default="llm")
@click.option("--demo", is_flag=True, help="使用内置样本演示完整链路")
@click.option("--report", "-r", type=click.Path(), help="输出报告 JSON")
def main(image, directory, method, demo, report):
    """CaloriSnap 端到端测试"""

    db_path = Path(__file__).parent / "drink_db.json"
    calculator = CaloriCalculator(str(db_path) if db_path.exists() else None)

    if demo or (not image and not directory):
        print("🚀 CaloriSnap 端到端演示（使用模拟 OCR 文本）\n")
        all_results = []

        for sample in DEMO_SAMPLES:
            print(f"{'▸'*3} [{sample['id']}]")
            result = e2e_with_text(sample["ocr_text"], calculator)
            print(result["formatted"])
            print()
            all_results.append(result)

        if report:
            Path(report).parent.mkdir(parents=True, exist_ok=True)
            # 移除不可序列化的格式化字符串
            for r in all_results:
                r.pop("formatted", None)
            with open(report, "w", encoding="utf-8") as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
            print(f"📄 报告已保存: {report}")
        return

    # 图片端到端
    images = []
    if image:
        images.append(image)
    if directory:
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        images.extend(str(p) for p in Path(directory).iterdir() if p.suffix.lower() in exts)

    if not images:
        print("❌ 未找到图片")
        return

    print(f"🚀 CaloriSnap 端到端测试")
    print(f"   图片: {len(images)} 张")
    print(f"   方案: {method}\n")

    all_results = []
    for img in images:
        print(f"\n{'='*60}")
        result = e2e_with_image(img, method, calculator)

        if "error" in result:
            print(f"❌ {img}: {result['error']}")
        else:
            final = result["final"]
            print(f"📷 {img}")
            print(f"🏷️ {final['brand']} · {final['drink']}")
            print(f"🔥 {final['total_calories']} kcal ({final['match_type']})")
            for eq in final["equivalents"]:
                print(f"   📊 {eq}")
            print(f"⏱️  总耗时: {result['total_elapsed']}s")

        all_results.append(result)

    if report:
        Path(report).parent.mkdir(parents=True, exist_ok=True)
        with open(report, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n📄 报告已保存: {report}")


if __name__ == "__main__":
    main()
