#!/usr/bin/env python3
"""
使用 Claude Vision API 对《中国历代景德镇瓷器·清卷》PNG 图片进行 OCR 识别。
提取瓷器名称和介绍，输出简体中文。
"""

import anthropic
import base64
import json
import os
import sys
import time
from pathlib import Path

# ========== 配置 ==========
API_KEY = "ck_fihf3pjaejgg.ju4LGgCQyGb2OzrALgmiIsf3Gc2vlS5kMPiSnY-oT4c"
MODEL = "claude-sonnet-4-20250514"
PNG_DIR = Path(__file__).parent / "png_pages"
OUTPUT_FILE = Path(__file__).parent / "claude_vision_ocr_results.json"

# ========== 核心函数 ==========

def encode_image(image_path: str) -> str:
    """将图片编码为 base64"""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def ocr_single_page(client: anthropic.Anthropic, image_path: str, page_num: int) -> dict:
    """用 Claude Vision 识别单页图片"""
    
    b64_image = encode_image(image_path)
    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
    
    prompt = """你是一位中国古代瓷器专家，正在阅读《中国历代景德镇瓷器》清卷的一页。

请仔细观察这张图片，识别并提取以下信息：

1. **瓷器名称**（中文名称，如"青花山水图象腿瓶"）
2. **瓷器介绍**（包括朝代、尺寸、收藏机构、器型描述、纹饰特征等所有文字描述）
3. **图片编号**（页面上标注的编号，如 "015"、"016" 等）
4. **英文名称**（如果页面上有英文翻译的话）

重要规则：
- 所有输出必须使用**简体中文**，不要使用繁体中文
- 如果页面只是瓷器的图片（没有文字描述），只需提取能看到的信息（如编号、英文名）
- 如果有多件瓷器，分别列出
- 尺寸信息请完整保留（高、口径、底径等）

请以 JSON 格式返回，结构如下：
```json
{
  "page": 页码数字,
  "items": [
    {
      "name": "瓷器名称（简体中文）",
      "description": "完整的瓷器介绍文字（简体中文）",
      "dynasty": "朝代（如：清·顺治）",
      "dimensions": "尺寸信息",
      "collection": "收藏机构",
      "image_number": "图片编号",
      "english_name": "英文名称"
    }
  ],
  "is_image_only": true/false,
  "notes": "其他备注"
}
```

如果页面上没有任何文字信息（纯图片页），设 is_image_only 为 true。
只返回 JSON，不要其他内容。"""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )
        
        # 解析响应
        raw_text = response.content[0].text
        
        # 提取 JSON（可能被 markdown 代码块包裹）
        json_text = raw_text
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0]
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0]
        
        result = json.loads(json_text.strip())
        result["page"] = page_num
        result["source_file"] = os.path.basename(image_path)
        result["file_size_mb"] = round(file_size_mb, 2)
        
        # 用量统计
        result["usage"] = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        
        return result
        
    except json.JSONDecodeError as e:
        return {
            "page": page_num,
            "source_file": os.path.basename(image_path),
            "error": f"JSON 解析失败: {str(e)}",
            "raw_response": raw_text[:500] if 'raw_text' in dir() else "无响应",
        }
    except Exception as e:
        return {
            "page": page_num,
            "source_file": os.path.basename(image_path),
            "error": str(e),
        }


def get_png_files(directory: Path, limit: int = None) -> list:
    """获取排序后的 PNG 文件列表"""
    files = sorted(directory.glob("第*页.png"))
    if limit:
        files = files[:limit]
    return files


def main():
    # 参数处理
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    
    print(f"=" * 60)
    print(f"《中国历代景德镇瓷器·清卷》Claude Vision OCR")
    print(f"=" * 60)
    
    # 初始化客户端
    client = anthropic.Anthropic(api_key=API_KEY)
    
    # 获取文件列表
    png_files = get_png_files(PNG_DIR, limit=limit)
    total = len(png_files)
    
    print(f"找到 {total} 个 PNG 文件待处理")
    print(f"模型: {MODEL}")
    print(f"-" * 60)
    
    results = []
    total_input_tokens = 0
    total_output_tokens = 0
    
    for i, png_file in enumerate(png_files, 1):
        # 从文件名提取页码
        page_num = int(png_file.stem.replace("第", "").replace("页", ""))
        
        print(f"[{i}/{total}] 处理 {png_file.name} (页码 {page_num})...", end=" ", flush=True)
        
        result = ocr_single_page(client, str(png_file), page_num)
        results.append(result)
        
        if "error" in result:
            print(f"❌ 错误: {result['error'][:50]}")
        else:
            items = result.get("items", [])
            name = items[0].get("name", "未识别") if items else "无内容"
            tokens_in = result.get("usage", {}).get("input_tokens", 0)
            tokens_out = result.get("usage", {}).get("output_tokens", 0)
            total_input_tokens += tokens_in
            total_output_tokens += tokens_out
            print(f"✅ {name} (tokens: {tokens_in}+{tokens_out})")
        
        # 避免速率限制
        if i < total:
            time.sleep(1)
    
    # 保存结果
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"处理完成！共 {total} 页")
    print(f"总 Token 用量: 输入 {total_input_tokens}, 输出 {total_output_tokens}")
    print(f"结果保存到: {OUTPUT_FILE}")
    print(f"{'=' * 60}")
    
    # 打印摘要
    print(f"\n📋 识别结果摘要:")
    print(f"-" * 60)
    for r in results:
        page = r.get("page", "?")
        if "error" in r:
            print(f"  第{page:03d}页: ❌ {r['error'][:60]}")
        else:
            items = r.get("items", [])
            if items:
                for item in items:
                    name = item.get("name", "未识别")
                    desc_len = len(item.get("description", "") or "")
                    print(f"  第{page:03d}页: {name} (描述{desc_len}字)")
            else:
                img_only = r.get("is_image_only", False)
                print(f"  第{page:03d}页: {'[纯图片页]' if img_only else '[无内容]'}")


if __name__ == "__main__":
    main()
