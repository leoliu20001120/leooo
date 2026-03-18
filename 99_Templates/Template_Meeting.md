---
created: <% tp.file.creation_date("YYYY-MM-DD HH:mm") %>
type: meeting
tags:
  - meeting
  - status/pending
participants: 
---

# 📅 会议: <% tp.file.title %>

## ℹ️ 基本信息
- **时间**: <% tp.date.now("HH:mm") %>
- **参会人**: <% tp.file.cursor(1) %>

## 🎯 会议目标
<% tp.file.cursor(2) %>

## 📝 讨论记录
- <% tp.file.cursor(3) %>


## ✅ 待办事项 (Action Items)
- [ ] **谁**: 任务内容 (截止: )
- [ ] **谁**: 任务内容 (截止: )

## 💡 AI 总结 (留空)