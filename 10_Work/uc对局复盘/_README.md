# 🎯 UC 对局复盘 — AI 复盘分析系统

> **项目**: UC 游戏对局 AI 复盘分析  
> **状态**: 迭代调优中  
> **更新**: 2026-03-26  
> **路径**: `10_Work/uc对局复盘/`

---

## 📊 项目概述

基于对局数据的 AI 复盘分析系统，核心能力 = **对局数据解析 → 多维度评分 → 个性化改进建议**。

后端服务分析对局 JSON → 输出五维雷达评分 + 亮点回顾 + 短板诊断 + 改进建议。

---

## 📁 目录结构

```
uc对局复盘/
├── _README.md                          ← 你在这里
│
├── 📂 ucgit/                           ← 后端 Git 仓库
│   └── go_ai_yr_postmatch_analysis_svr/  ← Go 服务（git.woa.com）
│       └── analysis.go                 ← 核心分析逻辑
│
├── 📂 jsontest/                        ← 测试数据 & 分析脚本
│   ├── 1.json ~ 46.json               ← 46 份测试对局数据
│   ├── upload_and_report.py            ← 批量测试：JSON→POST→result.xlsx
│   ├── result.xlsx                     ← 测试输出结果汇总
│   ├── 有待提升_label文案汇总.xlsx       ← Label 文案分析
│   ├── analyze_*.py                    ← 数据分析脚本（3个）
│   ├── calc_score*.py                  ← 评分计算脚本（3个）
│   ├── radar_*.py                      ← 雷达图相关脚本（4个）
│   ├── rule_distribution*.py/html      ← 规则分布分析
│   ├── label_distribution_有待提升.html  ← Label 分布可视化
│   └── peek_structure.py               ← JSON 结构查看工具
│
├── 📊 数据文件
│   ├── PVPAnalysis.xlsx                ← PVP 分析数据
│   ├── highlight_templates.xlsx        ← 亮点模板
│   ├── improvement_templates.xlsx      ← 改进建议模板
│   ├── 对局输出模版.xlsx               ← 对局输出模板
│   ├── 胜负序列模版_结构化.xlsx         ← 胜负序列模板
│   ├── rank_average.xlsx               ← 段位均值数据
│   ├── 工作簿1/2/3.xlsx               ← 工作数据
│   └── 对话详情.csv                    ← 对话详情数据
│
├── 📈 分析报告
│   ├── analysis_report.html            ← 交互式分析报告（Plotly）
│   ├── 上线效果分析报告.html            ← 上线效果分析
│   └── analysis_report.py              ← 报告生成脚本
│
├── 🔧 核心脚本
│   ├── highlights.py                   ← 亮点回顾逻辑
│   ├── improvements.py                 ← 改进建议逻辑
│   ├── radar_interpretation.py         ← 雷达图解读
│   ├── generate_report.py              ← 报告生成
│   └── mock_data.py                    ← Mock 数据生成
│
├── 📋 文案/文本
│   ├── 合并文案.txt                    ← 合并后的文案
│   ├── 合并文案_润色前备份.txt           ← 润色前备份
│   ├── 合并文案_副本.txt               ← 文案副本
│   └── improvement_templates_new.txt    ← 新版改进模板
│
├── 🗂️ 协议/配置
│   ├── fight_analysis.proto            ← 对战分析协议定义
│   ├── radar_chart_detail.proto        ← 雷达图详情协议
│   └── tlog20251127.xml                ← TLog 配置
│
└── 🛠️ 工具脚本（根目录）
    ├── _connector.py                   ← 连接器
    ├── _llm_optimize.py                ← LLM 优化
    └── _restore_cartesian.py           ← 笛卡尔积恢复
```

---

## 🔑 关键文件速查

| 想做什么 | 看这个 |
|---------|--------|
| 了解核心分析逻辑 | `ucgit/go_ai_yr_postmatch_analysis_svr/analysis.go` |
| 跑批量测试 | `jsontest/upload_and_report.py`（46个JSON→POST→result.xlsx） |
| 看测试结果 | `jsontest/result.xlsx` |
| 看交互式分析报告 | `analysis_report.html`（Plotly 五维雷达+趋势+角色进步+短板诊断） |
| 看上线效果 | `上线效果分析报告.html` |
| 改亮点/改进模板 | `highlight_templates.xlsx` / `improvement_templates.xlsx` |
| 查 Label 分布 | `jsontest/label_distribution_有待提升.html` |

---

## 📌 关键数据发现

- **Label 分布**：「有待提升」集中于脱出反打（43.5%）+ 防御反击（34.8%）
- **指标覆盖率**：93.5% 无具体数字（模板化问题，待优化）
- **近期修改**：jPoints 跳转点调整、subdim_behId 修复、子维度 ID 映射（27-30→41-44）

---

## 🔄 工作流

```
修改 analysis.go → commit + push → upload_and_report.py 批量测试 → result.xlsx 对比 → 数据分析
```

---

[[10_Work/_README|← 返回工作项目区]]
