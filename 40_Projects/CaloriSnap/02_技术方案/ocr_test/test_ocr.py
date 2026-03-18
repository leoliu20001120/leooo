#!/usr/bin/env python3
"""
CaloriSnap — OCR 识别测试脚本
测试不同 OCR 方案对奶茶/咖啡标签的识别效果

使用方法:
    python test_ocr.py --image sample_labels/test1.jpg
    python test_ocr.py --dir sample_labels/ --report results/ocr_report.json
"""

import os
import sys
import json
import base64
import time
from pathlib import Path
from typing import Optional

import click
from PIL import Image

# ============================================================
# 方案 A: 腾讯云 通用印刷体 OCR
# ============================================================

def ocr_tencent_cloud(image_path: str) -> dict:
    """调用腾讯云通用印刷体 OCR"""
    try:
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.ocr.v20181119 import ocr_client, models
    except ImportError:
        return {"error": "请安装: pip install tencentcloud-sdk-python"}

    secret_id = os.environ.get("TENCENT_SECRET_ID")
    secret_key = os.environ.get("TENCENT_SECRET_KEY")
    if not secret_id or not secret_key:
        return {"error": "请设置环境变量 TENCENT_SECRET_ID 和 TENCENT_SECRET_KEY"}

    # 读取图片并编码
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    cred = credential.Credential(secret_id, secret_key)
    httpProfile = HttpProfile()
    httpProfile.endpoint = "ocr.tencentcloudapi.com"
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    client = ocr_client.OcrClient(cred, "ap-guangzhou", clientProfile)

    req = models.GeneralBasicOCRRequest()
    req.ImageBase64 = image_base64

    start = time.time()
    resp = client.GeneralBasicOCR(req)
    elapsed = time.time() - start

    # 解析结果
    result = json.loads(resp.to_json_string())
    text_lines = []
    for item in result.get("TextDetections", []):
        text_lines.append({
            "text": item["DetectedText"],
            "confidence": item["Confidence"],
            "location": item.get("ItemPolygon", {})
        })

    full_text = "\n".join([t["text"] for t in text_lines])

    return {
        "provider": "tencent_cloud",
        "image": image_path,
        "elapsed_seconds": round(elapsed, 3),
        "text_lines": text_lines,
        "full_text": full_text,
        "line_count": len(text_lines),
        "avg_confidence": round(
            sum(t["confidence"] for t in text_lines) / max(len(text_lines), 1), 2
        ),
    }


# ============================================================
# 方案 B: 多模态大模型直接识别 (OpenAI 兼容)
# ============================================================

def ocr_multimodal_llm(image_path: str, api_key: Optional[str] = None,
                       base_url: Optional[str] = None,
                       model: str = "gpt-4o") -> dict:
    """
    用多模态大模型直接识别标签并输出结构化结果
    支持 OpenAI / DeepSeek / 混元 等兼容 API
    """
    try:
        from openai import OpenAI
    except ImportError:
        return {"error": "请安装: pip install openai"}

    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    base_url = base_url or os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("LLM_MODEL", model)

    if not api_key:
        return {"error": "请设置环境变量 OPENAI_API_KEY"}

    # 读取图片并编码
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    # 检测图片格式
    ext = Path(image_path).suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    prompt = """你是一个奶茶/咖啡标签识别助手。请仔细看这张杯身标签照片，提取以下信息并以 JSON 格式返回：

{
    "brand": "品牌名（如：瑞幸咖啡、喜茶、星巴克、霸王茶姬等）",
    "drink_name": "饮品名称",
    "size": "杯型（中杯/大杯/超大杯）",
    "sugar_level": "糖度（正常糖/少糖/半糖/微糖/无糖/不另外加糖）",
    "temperature": "温度（冰/热/去冰/少冰/常温）",
    "toppings": ["加料1", "加料2"],
    "order_number": "单号（如有）",
    "raw_text": "标签上的完整原始文字",
    "confidence": "识别置信度（high/medium/low）",
    "notes": "其他备注"
}

注意：
- 如果某个字段无法识别，填 null
- toppings 如果没有加料，返回空数组 []
- 品牌名请标准化（如 "luckin" → "瑞幸咖啡"）
- 只返回 JSON，不要其他文字"""

    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ],
        max_tokens=1000,
        temperature=0.1,
    )
    elapsed = time.time() - start

    raw_content = response.choices[0].message.content.strip()

    # 尝试解析 JSON（可能被 markdown 代码块包裹）
    json_str = raw_content
    if "```json" in json_str:
        json_str = json_str.split("```json")[1].split("```")[0].strip()
    elif "```" in json_str:
        json_str = json_str.split("```")[1].split("```")[0].strip()

    try:
        extracted = json.loads(json_str)
    except json.JSONDecodeError:
        extracted = {"raw_response": raw_content, "parse_error": True}

    return {
        "provider": f"multimodal_llm ({model})",
        "image": image_path,
        "elapsed_seconds": round(elapsed, 3),
        "extracted": extracted,
        "raw_response": raw_content,
        "tokens_used": {
            "prompt": response.usage.prompt_tokens if response.usage else None,
            "completion": response.usage.completion_tokens if response.usage else None,
        }
    }


# ============================================================
# 测试主入口
# ============================================================

def print_result(result: dict, verbose: bool = False):
    """打印测试结果"""
    print(f"\n{'='*60}")
    print(f"📷 图片: {result.get('image', 'N/A')}")
    print(f"🔧 方案: {result.get('provider', 'N/A')}")
    print(f"⏱️  耗时: {result.get('elapsed_seconds', 'N/A')}s")

    if "error" in result:
        print(f"❌ 错误: {result['error']}")
        return

    if "full_text" in result:
        print(f"📝 识别文字 ({result['line_count']} 行, 平均置信度 {result['avg_confidence']}%):")
        print(f"   {result['full_text']}")

    if "extracted" in result:
        extracted = result["extracted"]
        if isinstance(extracted, dict) and not extracted.get("parse_error"):
            print(f"🏷️ 品牌: {extracted.get('brand', '?')}")
            print(f"🥤 饮品: {extracted.get('drink_name', '?')}")
            print(f"📏 杯型: {extracted.get('size', '?')}")
            print(f"🍬 糖度: {extracted.get('sugar_level', '?')}")
            print(f"🧊 温度: {extracted.get('temperature', '?')}")
            print(f"🍡 加料: {extracted.get('toppings', [])}")
            print(f"📋 原文: {extracted.get('raw_text', '?')}")
            print(f"🎯 置信: {extracted.get('confidence', '?')}")

    if verbose:
        print(f"\n📄 完整结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    print(f"{'='*60}")


@click.command()
@click.option("--image", "-i", type=click.Path(exists=True), help="单张图片路径")
@click.option("--dir", "-d", "directory", type=click.Path(exists=True), help="图片目录（批量测试）")
@click.option("--method", "-m",
              type=click.Choice(["tencent", "llm", "both"]),
              default="both", help="测试方案")
@click.option("--report", "-r", type=click.Path(), help="输出报告路径 (JSON)")
@click.option("--verbose", "-v", is_flag=True, help="详细输出")
def main(image, directory, method, report, verbose):
    """CaloriSnap OCR 测试工具"""
    
    if not image and not directory:
        # 没有提供图片，用模拟数据演示
        print("⚠️  未提供图片，使用模拟文本演示 LLM 结构化提取能力")
        print("   用法: python test_ocr.py --image <图片路径>")
        print("   或:   python test_ocr.py --dir <图片目录>")
        print()
        demo_text_extract()
        return

    # 收集要测试的图片
    images = []
    if image:
        images.append(image)
    if directory:
        exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        images.extend(
            str(p) for p in Path(directory).iterdir()
            if p.suffix.lower() in exts
        )

    if not images:
        print("❌ 未找到任何图片文件")
        return

    print(f"🚀 CaloriSnap OCR 测试")
    print(f"   图片数量: {len(images)}")
    print(f"   测试方案: {method}")
    print()

    all_results = []
    for img_path in images:
        if method in ("tencent", "both"):
            result = ocr_tencent_cloud(img_path)
            print_result(result, verbose)
            all_results.append(result)

        if method in ("llm", "both"):
            result = ocr_multimodal_llm(img_path)
            print_result(result, verbose)
            all_results.append(result)

    # 输出报告
    if report:
        Path(report).parent.mkdir(parents=True, exist_ok=True)
        with open(report, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n📊 报告已保存到: {report}")

    # 打印汇总
    print(f"\n{'='*60}")
    print(f"📊 测试汇总")
    print(f"   总测试数: {len(all_results)}")
    errors = [r for r in all_results if "error" in r]
    print(f"   成功: {len(all_results) - len(errors)}")
    print(f"   失败: {len(errors)}")
    if all_results:
        times = [r["elapsed_seconds"] for r in all_results if "elapsed_seconds" in r and "error" not in r]
        if times:
            print(f"   平均耗时: {sum(times)/len(times):.2f}s")
    print(f"{'='*60}")


def demo_text_extract():
    """没有图片时的文本演示"""
    sample_labels = [
        "瑞幸咖啡\n生椰拿铁\n大杯 半糖 冰\n+珍珠\n#086 14:35",
        "HEYTEA 喜茶\n多肉葡萄\n中杯\n少少甜(三分甜) 少冰\n+芋圆啵啵\n#A023",
        "霸王茶姬 CHAGEE\n伯牙绝弦\n大杯\n不另外加糖\n冰\n#168",
        "Starbucks\n焦糖玛奇朵\nGrande\nIced\n2% Milk\n#2847",
        "茶百道\n招牌芋圆奶茶\n大杯 七分糖 正常冰\n+椰果 +布丁",
    ]

    print("📋 模拟标签文本 → 结构化提取演示:\n")
    for i, label in enumerate(sample_labels, 1):
        print(f"--- 样本 {i} ---")
        print(f"原始文本:\n{label}\n")
        # 这里展示的是预期的提取逻辑（实际调用时走 LLM）
        print(f"→ 这段文字将被发送给 LLM 进行结构化提取")
        print()


if __name__ == "__main__":
    main()
