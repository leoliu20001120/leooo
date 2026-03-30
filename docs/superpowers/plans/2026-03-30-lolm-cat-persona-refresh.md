# LOLM 峡谷猫格人格表达重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `demo/index.html` 从显式 `MBTI` 话术改为峡谷原创人格语言，同时保留现有答题、匹配、结果、PK 主流程。

**Architecture:** 保留单文件 HTML 结构与现有加权匹配逻辑，只替换题目维度命名、结果表达层和诊断文案层。底层仍由四个连续维度驱动猫种匹配，前台统一展示为峡谷行为气质与作答标签。

**Tech Stack:** 原生 HTML / CSS / JavaScript，单文件 Canvas 雷达图。

---

### Task 1: 重命名人格维度并改写题目文案

**Files:**
- Modify: `10_Work/lolm峡谷猫格/demo/index.html`

- [ ] **Step 1: 将 `QUESTIONS` 的四个维度从 `EI/SN/TF/JP` 改为原创维度**
- [ ] **Step 2: 调整每个选项的 `shortLabel` 与分值语义，使其服务于峡谷场景表达**
- [ ] **Step 3: 清理 `mbtiHint` 等前台会暴露心理测评术语的字段**

### Task 2: 重写猫种元数据与诊断表达

**Files:**
- Modify: `10_Work/lolm峡谷猫格/demo/index.html`

- [ ] **Step 1: 将 `CAT_TYPES` 中的 `mbti` / `mbtiLabel` 改成原创气质字段**
- [ ] **Step 2: 重写 `buildDiagnosis()`，改成“行为倾向 + 数据梗 + 猫种映射”结构**
- [ ] **Step 3: 重写 `buildComment()`，确保点评也不再使用 `MBTI` 术语**

### Task 3: 重构加载态与结果页呈现

**Files:**
- Modify: `10_Work/lolm峡谷猫格/demo/index.html`

- [ ] **Step 1: 改写 `startLoading()` 文案，保留“作答 × 对局数据”逻辑但去掉字母人格预判**
- [ ] **Step 2: 改写 `renderResult()` 顶部卡片，展示答题标签与峡谷气质摘要**
- [ ] **Step 3: 保留雷达图与 CTA，不改动整体交互节奏**

### Task 4: 验证与收尾

**Files:**
- Modify: `10_Work/lolm峡谷猫格/demo/index.html`
- Update: `.codebuddy/memory/episodic/2026-03-30.md`

- [ ] **Step 1: 运行脚本语法检查，确认内联 JS 可执行**
- [ ] **Step 2: 搜索 `MBTI` 与 `E/I/S/N/T/F/J/P` 直露文案，确认前台已清理**
- [ ] **Step 3: 追加今日日志，记录这轮人格表达重构结果**
