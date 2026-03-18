#!/usr/bin/env python3
"""
CaloriSnap — LLM 结构化提取测试
测试从 OCR 文字中提取品牌/品名/杯型/糖度/加料等信息

使用方法:
    python test_llm_extract.py --ocr-text "生椰拿铁 大杯 半糖 +珍珠"
    python test_llm_extract.py --demo  # 使用内置样本测试
"""

import os
import sys
import json
import time
from typing import Optional

import click

# LLM 提取的目标 Schema
DRINK_SCHEMA = {
    "type": "object",
    "properties": {
        "brand": {"type": ["string", "null"], "description": "品牌名"},
        "drink_name": {"type": ["string", "null"], "description": "饮品名称"},
        "size": {"type": ["string", "null"], "description": "杯型"},
        "sugar_level": {"type": ["string", "null"], "description": "糖度"},
        "temperature": {"type": ["string", "null"], "description": "温度"},
        "toppings": {"type": "array", "items": {"type": "string"}, "description": "加料"},
    },
    "required": ["brand", "drink_name", "size", "sugar_level", "temperature", "toppings"]
}

# 内置测试样本（模拟 OCR 输出）
DEMO_SAMPLES = [
    {
        "id": "luckin_01",
        "ocr_text": "瑞幸咖啡\n生椰拿铁\n大杯 半糖 冰\n+珍珠\n#086 14:35",
        "expected": {
            "brand": "瑞幸咖啡", "drink_name": "生椰拿铁",
            "size": "大杯", "sugar_level": "半糖",
            "temperature": "冰", "toppings": ["珍珠"]
        }
    },
    {
        "id": "heytea_01",
        "ocr_text": "HEYTEA 喜茶\n多肉葡萄\n中杯\n少少甜(三分甜) 少冰\n+芋圆啵啵\n#A023",
        "expected": {
            "brand": "喜茶", "drink_name": "多肉葡萄",
            "size": "中杯", "sugar_level": "三分甜",
            "temperature": "少冰", "toppings": ["芋圆啵啵"]
        }
    },
    {
        "id": "chagee_01",
        "ocr_text": "霸王茶姬 CHAGEE\n伯牙绝弦\n大杯\n不另外加糖\n冰\n#168",
        "expected": {
            "brand": "霸王茶姬", "drink_name": "伯牙绝弦",
            "size": "大杯", "sugar_level": "不另外加糖",
            "temperature": "冰", "toppings": []
        }
    },
    {
        "id": "starbucks_01",
        "ocr_text": "Starbucks\n焦糖玛奇朵\nGrande\nIced\n2% Milk\n#2847",
        "expected": {
            "brand": "星巴克", "drink_name": "焦糖玛奇朵",
            "size": "大杯", "sugar_level": "标准",
            "temperature": "冰", "toppings": []
        }
    },
    {
        "id": "chabaidao_01",
        "ocr_text": "茶百道\n招牌芋圆奶茶\n大杯 七分糖 正常冰\n+椰果 +布丁",
        "expected": {
            "brand": "茶百道", "drink_name": "招牌芋圆奶茶",
            "size": "大杯", "sugar_level": "七分糖",
            "temperature": "正常冰", "toppings": ["椰果", "布丁"]
        }
    },
    {
        "id": "nayuki_01",
        "ocr_text": "奈雪的茶 Nayuki\n霸气草莓\n大杯 少甜 少冰\n+脆波波",
        "expected": {
            "brand": "奈雪的茶", "drink_name": "霸气草莓",
            "size": "大杯", "sugar_level": "少甜",
            "temperature": "少冰", "toppings": ["脆波波"]
        }
    },
    {
        "id": "mixue_01",
        "ocr_text": "蜜雪冰城\n珍珠奶茶\n中杯 标准糖 正常冰",
        "expected": {
            "brand": "蜜雪冰城", "drink_name": "珍珠奶茶",
            "size": "中杯", "sugar_level": "标准糖",
            "temperature": "正常冰", "toppings": []
        }
    },
    {
        "id": "edge_case_01",
        "ocr_text": "luckin coffee\n抹茶瑞纳冰\n大杯\n#107 15:22",
        "expected": {
            "brand": "瑞幸咖啡", "drink_name": "抹茶瑞纳冰",
            "size": "大杯", "sugar_level": None,
            "temperature": None, "toppings": []
        }
    },
]


def extract_with_llm(ocr_text: str, api_key: Optional[str] = None,
                     base_url: Optional[str] = None,
                     model: Optional[str] = None) -> dict:
    """用 LLM 从 OCR 文字中提取结构化饮品信息"""
    try:
        from openai import OpenAI
    except ImportError:
        return {"error": "请安装: pip install openai"}

    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    base_url = base_url or os.environ.get("OPENAI_BASE_URL")
    model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")

    if not api_key:
        return {"error": "请设置环境变量 OPENAI_API_KEY"}

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    prompt = f"""你是一个奶茶/咖啡标签解析器。以下是 OCR 从杯身标签识别出的文字，请提取结构化信息。

OCR 文字:
---
{ocr_text}
---

请以 JSON 格式返回以下字段：
{{
    "brand": "品牌名（标准化中文名，如 luckin→瑞幸咖啡, Starbucks→星巴克, HEYTEA→喜茶, CHAGEE→霸王茶姬）",
    "drink_name": "饮品名称",
    "size": "杯型（中杯/大杯/超大杯，Grande→大杯, Tall→中杯, Venti→超大杯）",
    "sugar_level": "糖度（无糖/微糖/少糖/半糖/正常糖/全糖/不另外加糖 等原始描述）",
    "temperature": "温度（冰/热/去冰/少冰/常温/Iced→冰/Hot→热）",
    "toppings": ["加料列表，去掉 + 号前缀"],
    "raw_fields": {{}} // 其他识别出但不属于以上字段的信息
}}

规则：
1. 无法识别的字段填 null
2. toppings 无加料时填 []
3. 品牌名做标准化处理
4. 杯型做标准化处理（英文→中文）
5. 只返回 JSON"""

    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.0,
    )
    elapsed = time.time() - start

    raw = response.choices[0].message.content.strip()

    # 解析 JSON
    json_str = raw
    if "```json" in json_str:
        json_str = json_str.split("```json")[1].split("```")[0].strip()
    elif "```" in json_str:
        json_str = json_str.split("```")[1].split("```")[0].strip()

    try:
        extracted = json.loads(json_str)
    except json.JSONDecodeError:
        extracted = {"raw_response": raw, "parse_error": True}

    return {
        "extracted": extracted,
        "elapsed_seconds": round(elapsed, 3),
        "model": model,
        "tokens": {
            "prompt": response.usage.prompt_tokens if response.usage else None,
            "completion": response.usage.completion_tokens if response.usage else None,
        }
    }


def evaluate_extraction(extracted: dict, expected: dict) -> dict:
    """评估提取结果与预期的匹配度"""
    fields = ["brand", "drink_name", "size", "sugar_level", "temperature"]
    correct = 0
    total = 0
    details = {}

    for field in fields:
        exp_val = expected.get(field)
        ext_val = extracted.get(field)

        if exp_val is None:
            # 预期为 null，跳过评估
            details[field] = {"status": "skip", "expected": None, "got": ext_val}
            continue

        total += 1
        # 简单字符串匹配（忽略空格和括号内容）
        exp_normalized = str(exp_val).strip().lower()
        ext_normalized = str(ext_val).strip().lower() if ext_val else ""

        if exp_normalized in ext_normalized or ext_normalized in exp_normalized:
            correct += 1
            details[field] = {"status": "✅", "expected": exp_val, "got": ext_val}
        else:
            details[field] = {"status": "❌", "expected": exp_val, "got": ext_val}

    # 检查 toppings
    exp_toppings = set(expected.get("toppings", []))
    ext_toppings = set(extracted.get("toppings", []))
    total += 1
    if exp_toppings == ext_toppings:
        correct += 1
        details["toppings"] = {"status": "✅", "expected": list(exp_toppings), "got": list(ext_toppings)}
    elif exp_toppings.issubset(ext_toppings) or ext_toppings.issubset(exp_toppings):
        correct += 0.5  # 部分匹配
        details["toppings"] = {"status": "🟡", "expected": list(exp_toppings), "got": list(ext_toppings)}
    else:
        details["toppings"] = {"status": "❌", "expected": list(exp_toppings), "got": list(ext_toppings)}

    accuracy = correct / total if total > 0 else 0
    return {
        "accuracy": round(accuracy, 2),
        "correct": correct,
        "total": total,
        "details": details,
    }


@click.command()
@click.option("--ocr-text", "-t", type=str, help="OCR 识别出的文字")
@click.option("--demo", is_flag=True, help="使用内置样本测试")
@click.option("--report", "-r", type=click.Path(), help="输出报告路径 (JSON)")
@click.option("--offline", is_flag=True, help="离线模式（不调用 API，仅展示样本）")
def main(ocr_text, demo, report, offline):
    """CaloriSnap LLM 结构化提取测试"""

    if not ocr_text and not demo:
        demo = True  # 默认使用 demo 模式

    if ocr_text:
        print(f"📝 输入文字:\n{ocr_text}\n")
        if offline:
            print("⚠️ 离线模式，跳过 API 调用")
            return
        result = extract_with_llm(ocr_text)
        if "error" in result:
            print(f"❌ {result['error']}")
            return
        print(f"🔧 模型: {result['model']}")
        print(f"⏱️  耗时: {result['elapsed_seconds']}s")
        print(f"📦 提取结果:")
        print(json.dumps(result["extracted"], ensure_ascii=False, indent=2))
        return

    if demo:
        print("🧪 CaloriSnap LLM 结构化提取测试")
        print(f"   样本数量: {len(DEMO_SAMPLES)}")
        print(f"   模式: {'离线展示' if offline else '在线测试'}")
        print()

        all_results = []
        total_accuracy = 0

        for sample in DEMO_SAMPLES:
            print(f"--- [{sample['id']}] ---")
            print(f"OCR文字: {sample['ocr_text']}")

            if offline:
                print(f"预期结果: {json.dumps(sample['expected'], ensure_ascii=False)}")
                print()
                continue

            result = extract_with_llm(sample["ocr_text"])
            if "error" in result:
                print(f"❌ {result['error']}")
                continue

            extracted = result["extracted"]
            eval_result = evaluate_extraction(extracted, sample["expected"])

            print(f"提取结果: {json.dumps(extracted, ensure_ascii=False)}")
            print(f"准确率:   {eval_result['accuracy']*100:.0f}% ({eval_result['correct']}/{eval_result['total']})")
            for field, detail in eval_result["details"].items():
                print(f"  {detail['status']} {field}: 预期={detail['expected']} → 实际={detail.get('got', 'N/A')}")
            print(f"耗时: {result['elapsed_seconds']}s")
            print()

            total_accuracy += eval_result["accuracy"]
            all_results.append({
                "sample_id": sample["id"],
                "extracted": extracted,
                "expected": sample["expected"],
                "evaluation": eval_result,
                "elapsed": result["elapsed_seconds"],
            })

        if all_results:
            avg_accuracy = total_accuracy / len(all_results)
            print(f"\n{'='*60}")
            print(f"📊 汇总")
            print(f"   测试样本: {len(all_results)}")
            print(f"   平均准确率: {avg_accuracy*100:.1f}%")
            print(f"   达标线: 90%  {'✅ 达标' if avg_accuracy >= 0.9 else '❌ 未达标'}")
            print(f"{'='*60}")

            if report:
                from pathlib import Path as P
                P(report).parent.mkdir(parents=True, exist_ok=True)
                with open(report, "w", encoding="utf-8") as f:
                    json.dump({
                        "summary": {"avg_accuracy": avg_accuracy, "sample_count": len(all_results)},
                        "results": all_results
                    }, f, ensure_ascii=False, indent=2)
                print(f"📄 报告已保存: {report}")


if __name__ == "__main__":
    main()
