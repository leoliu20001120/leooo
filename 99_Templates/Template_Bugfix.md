---
created: <% tp.file.creation_date("YYYY-MM-DD HH:mm") %>
updated: <% tp.file.last_modified_date("YYYY-MM-DD HH:mm") %>
type: troubleshooting
status: 🔴 未解决
priority: P1
tags:
  - bugfix
  - error-log
related_project: [[<% tp.file.cursor(1) %>]]
---

# 🛠️ Issue: <% tp.file.title %>

## 🚨 问题描述 (Symptoms)
- **触发场景**: <% tp.file.cursor(2) %>
- **环境信息**: (例如: Python 3.9, Mac M1, Prod/Dev环境)
- **影响范围**: 
- **首次发现时间**: <% tp.date.now("YYYY-MM-DD HH:mm") %>

### 错误日志 (Error Log)
```text
<% tp.file.cursor(3) %>
```

---

## 🔍 排查过程 (Investigation)

### 假设 1: 
- [ ] 检查步骤
- [ ] 结果: 

### 假设 2: 
- [ ] 检查步骤
- [ ] 结果: 

---

## ✅ 解决方案 (Solution)

> [!TIP] 最终解决方案
> (待填写)

### 修复步骤
1. 
2. 
3. 

### 相关代码/配置修改
```
(代码或配置变更)
```

---

## 📝 经验总结 (Lessons Learned)

> [!IMPORTANT] 
> - 关键经验1
> - 关键经验2

### 预防措施
- [ ] 添加监控/告警
- [ ] 完善文档
- [ ] 其他

---

## 🔗 相关资料
- 相关文档: 
- 参考链接: 