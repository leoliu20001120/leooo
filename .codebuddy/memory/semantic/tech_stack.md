# 🔧 语义记忆：技术栈偏好与约定

> 用户的技术偏好、编码风格、工具选择
> 标签: #memory/semantic #tech

---

## 语言偏好
- **首选**: Python（后端、脚本、数据处理）
- **前端**: HTML/CSS/JS（原型），微信小程序（产品）
- **文档**: Markdown（Obsidian 生态）
- **数据**: Excel (.xlsx)、JSON、SQL

## 工具链
| 用途 | 工具 | 备注 |
|------|------|------|
| 知识管理 | Obsidian | 核心工作流 |
| 代码编辑 | CodeBuddy IDE | AI 辅助 |
| 版本控制 | Git + GitHub | SSH 认证 |
| 数据库 | Supabase (PostgreSQL) | CaloriSnap 选型 |
| 云服务 | 腾讯云 | OCR 等 |
| 设计原型 | HTML prototype | 直接写 HTML 而非 Figma |

## 编码约定
- 文件命名：中文名可接受（Obsidian 笔记），代码文件用英文 + 下划线
- 注释语言：中文
- 输出格式：默认 Markdown，表格偏好使用 Markdown 表格
- Excel 操作：使用 openpyxl（Python）

## Obsidian 约定
- 目录下放 `_README.md` 作为目录说明
- 使用 `[[双向链接]]` 关联文档
- 根目录 `_INDEX.md` 是全局导航入口
- 模板在 `99_Templates/`

## AI 协作偏好
- 输出语言：中文
- 代码直接写入文件，不要只输出代码块
- 创建新文件优先，避免覆盖已有文件
- 大任务先拆分 TODO 再执行
- 喜欢详细的表格总结
