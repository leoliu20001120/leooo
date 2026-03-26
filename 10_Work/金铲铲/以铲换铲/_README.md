# 🃏 以铲换X — AI 图片评分活动

> **项目**: 金铲铲之战「以铲换X」AI 图片评分活动  
> **状态**: 需求评估完成，VLM 验证通过，待动态 Demo  
> **更新**: 2026-03-26  
> **路径**: `10_Work/金铲铲/以铲换铲/`

---

## 📊 项目概述

用户制作金铲铲手工艺品 → 拍照上传 → AI（VLM）评分 + 生成点评 → 排行榜竞赛。

核心验证结论：
- **大类准确率**: 100%
- **精确评分**: ≥96%
- **评语质量**: 4.2/5
- **P0 风险**: 评分一致性、3小时高并发、合规兜底

---

## 📁 目录结构

```
以铲换铲/
├── _README.md                              ← 你在这里
│
├── 📝 需求 & 评估文档
│   ├── 需求评估_以铲换X.md                   ← AI 需求评估文档（Markdown 版）
│   ├── 金铲铲 以铲换X活动 - AI需求评估文档.docx ← AI 需求评估（Word 版）
│   ├── 以铲换X.docx                         ← 原始需求文档
│   └── 以铲换X项目组讨论纪要.md               ← 项目组讨论纪要
│
├── 🔬 VLM 验证
│   ├── claude_vlm_验证报告.html              ← VLM 验证报告（交互式）
│   ├── review_webui.html                    ← 50% 分层抽样 Review WebUI
│   ├── review_20pct_webui.html              ← 20% 看图 Review WebUI
│   ├── review_20pct_standalone.html         ← 20% 自包含版（可脱机使用）
│   └── sampled_images.json                  ← 抽样图片数据
│
├── 🔧 脚本
│   ├── demo.py                              ← VLM 评分 Demo
│   ├── sample_images.py                     ← 图片抽样脚本
│   ├── embed_images.py                      ← 图片嵌入脚本
│   ├── embed_images_compressed.py           ← 压缩版嵌入
│   ├── _check_images.py                     ← 图片检查工具
│   └── _embed_images.py                     ← 图片嵌入工具
│
└── 📸 金铲铲的图片 3/                        ← 用户上传图片素材（138张）
    ├── *.jpg (78)
    ├── *.png (36)
    ├── *.webp (15)
    └── *.avif (9)
```

---

## 🔑 关键文件速查

| 想做什么 | 看这个 |
|---------|--------|
| 了解需求全貌 | `需求评估_以铲换X.md` |
| 看 VLM 验证结果 | `claude_vlm_验证报告.html` |
| 看项目讨论结论 | `以铲换X项目组讨论纪要.md` |
| 跑 VLM Demo | `demo.py` |
| Review 抽样结果 | `review_20pct_standalone.html`（推荐，自包含版） |

---

## 🔄 验证工作流（已完成）

```
快验(10张) → 50%分层抽样(review_webui) → 20%看图(review_20pct) → 混淆矩阵 → Prompt迭代
```

---

[[金铲铲/_README|← 返回金铲铲项目]]
