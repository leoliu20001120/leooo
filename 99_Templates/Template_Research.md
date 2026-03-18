---
type: template
name: Research Note Template
created: 2025-12-05
---

# 研究笔记模板

> 复制此模板用于研究类笔记的创建

---

```markdown
---
created: <% tp.file.creation_date("YYYY-MM-DD HH:mm") %>
type: research
tags:
  - research
  - <% tp.file.cursor(1) %>
topic: 
status: 🔍 进行中
---

# 📚 研究: <% tp.file.title %>

## 🎯 研究目标

> **核心问题**: <% tp.file.cursor(2) %>

---

## 📋 背景与动机

<% tp.file.cursor(3) %>

---

## 🔍 研究内容

### 关键发现

1. **发现1**: 
2. **发现2**: 
3. **发现3**: 

### 数据与证据

| 来源 | 内容 | 可信度 |
|:---|:---|:---:|
| {来源1} | {内容摘要} | ⭐⭐⭐⭐⭐ |

---

## 💡 分析与思考

### 核心观点

> [!IMPORTANT]
> {核心结论}

### 开放问题

- [ ] 问题1？
- [ ] 问题2？

---

## 📎 参考资料

1. [资料名称](链接)
2. [[相关笔记]]

---

## 🔄 更新记录

| 日期 | 更新内容 |
|:---|:---|
| <% tp.date.now("YYYY-MM-DD") %> | 初稿 |
```
