# -*- coding:utf-8 -*-
import asyncio
import os
import gradio as gr
from volcenginesdkarkruntime import AsyncArk

client = AsyncArk(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key='88fbb74a-9b28-439f-b830-592fc732799c'
)


async def analyze_image(image):
    """分析图片的主函数"""
    if image is None:
        return None, "请先上传图片"
    
    # 保存上传的图片到临时文件
    temp_path = "/tmp/temp_image.jpg"
    image.save(temp_path)
    
    try:
        response = await client.responses.create(
            model="doubao-seed-2-0-lite-260215",
            input=[
                {"role": "user", "content": [
                    {
                        "type": "input_image",
                        "image_url": f"file://{temp_path}"
                    },
                    {
                        "type": "input_text",
                        "text": """### 金铲铲特征定义
金铲铲 = 铲头 + 铲柄 + 铲头上有 3 个孔（或3条纵向开槽）

### 五级评分矩阵

| 等级 | 定义 | 分数区间 |
|------|------|---------|
| L1 非铲子 | 完全不是铲子形态（动物、杯子、电器等） | 0-30 |
| L2 铲子但非金铲铲 | 是铲子但孔数明显不是3（0/1/2/4+孔）| 31-59 |
| L3 金铲铲（无手工） | 铲头+铲柄+3孔，但是购买的现成品，无手工创作痕迹 | 60-74 |
| L4 较优秀（有手工） | 有明显手工创作痕迹（手绘、剪裁、粘贴等），造型完整 | 75-89 |
| L5 非常优秀 | 强手工制作、高创意、高完成度（多材质组合、精细工艺等） | 90-100 |

### 评判要点
1. 先判断是否是"铲子" → 再判断是否有"3孔"特征 → 再判断手工程度
2. 关键阈值：60分通过线，90分优秀线
3. L4 vs L5 的区别：L4 有手工但相对简单；L5 是强手工+强创意+高完成度
4. 评判以"铲子本身的制作水平"为主，附加创意为辅

### 评语要求
- 约 50 字，活泼、游戏化风格
- 必须关联图片中的具体细节
- 禁止提及竞品游戏名称、真实人名、敏感内容

## 输出格式（JSON）
{
  "level": 1-5,
  "score": 0-100,
  "is_shovel": true/false,
  "comment": "≤50字评语",
  "reasoning": "判断依据（内部参考）"
}

请评估玩家上传的这张图片。"""
                    }
                ]},
            ]
        )
        result_text = response.output[1].content[0].text
        return image, result_text
    except Exception as e:
        return image, f"分析失败: {str(e)}"


def sync_analyze_image(image):
    """同步包装函数，供Gradio使用"""
    return asyncio.run(analyze_image(image))


def create_gradio_interface():
    """创建Gradio界面"""
    with gr.Blocks(title="金铲铲图片分析器", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🎮 金铲铲图片分析器")
        gr.Markdown("上传您的金铲铲图片，AI将自动分析其等级和评分！")
        
        with gr.Row():
            with gr.Column():
                image_input = gr.Image(
                    label="上传图片",
                    type="pil",
                    height=300
                )
                analyze_btn = gr.Button("🔍 开始分析", variant="primary")
            
            with gr.Column():
                image_output = gr.Image(
                    label="预览图片",
                    height=300,
                    interactive=False
                )
                result_output = gr.Textbox(
                    label="分析结果",
                    lines=10,
                    max_lines=20,
                    placeholder="分析结果将显示在这里..."
                )
        
        # 绑定事件
        analyze_btn.click(
            fn=sync_analyze_image,
            inputs=image_input,
            outputs=[image_output, result_output]
        )
        
        # 上传图片时自动预览
        image_input.change(
            fn=lambda img: (img, ""),
            inputs=image_input,
            outputs=[image_output, result_output]
        )
        
        gr.Markdown("""
        ### 使用说明
        1. 点击"上传图片"选择您的金铲铲图片
        2. 图片将自动在右侧预览区域显示
        3. 点击"开始分析"按钮进行AI分析
        4. 分析结果将显示在下方文本框中
        
        ### 评分标准
        - L1 (0-30分): 非铲子形态
        - L2 (31-59分): 铲子但孔数不符
        - L3 (60-74分): 金铲铲但无手工痕迹
        - L4 (75-89分): 有明显手工创作
        - L5 (90-100分): 强手工+高创意
        """)
    
    return demo


if __name__ == "__main__":
    # 创建并启动Gradio应用
    demo = create_gradio_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True
    )
