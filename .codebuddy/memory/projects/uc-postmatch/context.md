# UC 对局复盘

> 更新: 2026-03-28

## 项目信息
- **类型**: 工作项目 | **路径**: `10_Work/uc对局复盘/`
- **状态**: 迭代调优中
- **后端仓库**: `ucgit/go_ai_yr_postmatch_analysis_svr/`（git.woa.com, master分支）
- **核心文件**: `analysis.go`（Go语言，复盘分析逻辑，~739行）
- **测试接口**: `http://30.189.253.210:8080/fight/report`
- **测试工具**: `upload_and_report.py`（批量46个JSON→POST→result.xlsx）

## 数据分析产出
| 文件 | 内容 |
|------|------|
| analysis_report.py/.html | Plotly交互式报告（五维雷达+趋势+角色进步+短板诊断） |
| label_distribution_有待提升.html | 8种label分布，脱出反打43.5%+防御反击34.8% |

## 关键发现
- 「有待提升」label高度集中：脱出后反打(43.5%) + 防御反击(34.8%) = 78.3%
- 指标数字覆盖率仅6.5%（3/46带数字），93.5%模板化无数字
- 子维度ID映射：27/28/29/30 → 41/42/43/44
- subdim_behId修复后，5个case的label_id从None→29（正确命中配置）

## 近期代码修改
- jPoints跳转点调整（多条规则第二个值10→9，规则6单独改回10）
- barchart_behId → subdim_behId（id41-44）
