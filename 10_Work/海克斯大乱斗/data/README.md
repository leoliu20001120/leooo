# SQL取数结果 - 数据占位文件说明

## 使用方法

1. 跑完SQL后，将结果导出为CSV放到这个目录
2. 文件名和列名必须严格匹配以下格式
3. 如果某个文件不存在，系统会自动回退使用Excel知识库中的数据

## 文件格式

### step1_1_augment_stats.csv — 单个符文全局胜率 & 选取率
| 列名 | 类型 | 说明 |
|------|------|------|
| player_augment | int | 符文ID |
| augment_name | string | 符文中文名（映射自符文ID与中文名对照.xlsx） |
| win_rate | float | 胜率，小数形式（如0.6739代表67.39%） |
| show_rate | float | 选取率/展示率，小数形式（如0.0208代表2.08%） |

### step1_2_champion_augment_stats.csv — 英雄×符文胜率 & 选取率
| 列名 | 类型 | 说明 |
|------|------|------|
| championid | int | 英雄ID |
| champion_name | string | 英雄中文名（映射自英雄id定位表.xlsx） |
| player_augment | int | 符文ID |
| augment_name | string | 符文中文名 |
| win_rate | float | 该英雄选该符文的胜率 |
| show_rate | float | 该英雄选该符文的选取率 |

> ⚠️ 原始数据中 championid 和 player_augment 列搞反了，已修正。

### step1_3_champion_pick_rate.csv — 英雄出场率
| 列名 | 类型 | 说明 |
|------|------|------|
| championid | int | 英雄ID |
| champion_name | string | 英雄中文名 |
| pick_rate | float | 出场率 |

### step1_4_pair_stats.csv — 符文×符文组合胜率
| 列名 | 类型 | 说明 |
|------|------|------|
| aug_a | int | 符文A ID |
| aug_a_name | string | 符文A中文名 |
| aug_b | int | 符文B ID |
| aug_b_name | string | 符文B中文名 |
| pair_win_rate | float | 组合胜率 |
| pair_show_rate | float | 组合选取率 |

### step1_5_champion_pair_stats.csv — 英雄×符文×符文组合胜率
| 列名 | 类型 | 说明 |
|------|------|------|
| championid | int | 英雄ID |
| champion_name | string | 英雄中文名 |
| aug_a | int | 符文A ID |
| aug_a_name | string | 符文A中文名 |
| aug_b | int | 符文B ID |
| aug_b_name | string | 符文B中文名 |
| pair_win_rate | float | 组合胜率 |
| pair_show_rate | float | 组合选取率 |

## 注意事项

- win_rate/show_rate 全部用 **小数** 格式（0.67 而非 67%），加载时代码会自动×100转为百分比
- 目前占位文件里各有1行示例数据，你可以直接**覆盖**整个文件
- 如果SQL还没跑好，系统会自动用Excel知识库中的全局胜率/选取率进行兜底
