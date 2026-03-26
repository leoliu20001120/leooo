---
created: 2026-03-26
tags: [AI-Coding, Claude-Code, Codex-CLI, 工具调研, 深度调研]
---

# Claude Code 与 Codex CLI 深度调研报告

> **调研日期**: 2026-03-26
> **调研目的**: 理解 Claude Code 和 Codex CLI 的核心能力、对比差异，并找到融入 AI 产品经理工作流的最佳路径。
> **信息来源**: Anthropic 官方文档、OpenAI 官方文档、知乎/CSDN 评测、内部 CLI Internal 知识库、多篇横评文章（≥5 个独立来源交叉验证）

---

## 📋 结论先行（金字塔摘要）

**核心结论**：Claude Code 是当前最适合你的 CLI AI 编程工具，理由如下：

1. **与现有工具链互补**：你已有 CodeBuddy IDE 处理日常编辑，Claude Code 作为终端 Agent 补充"深度推理 + 自动化"场景
2. **记忆系统天然契合**：Claude Code 的 `CLAUDE.md` + Auto Memory 机制与你在 Obsidian 中已建立的 `.codebuddy/memory/` 记忆体系理念一致
3. **产品经理友好**：不需要深度编程背景，自然语言驱动，Plan Mode 可先规划再执行
4. **司内可用**：腾讯 `Claude Code Internal` 封装版已打通 OA 身份验证，无需翻墙

**Codex CLI 作为补充了解即可**，它更适合已深度嵌入 OpenAI 生态的团队，且订阅门槛（$200/月 Pro）远高于 Claude Code。

---

## 一、Claude Code 深度解析

### 1.1 它是什么

Claude Code 是 Anthropic 推出的 **终端原生 AI 编程代理**。它不是传统的代码补全工具，而是一个能理解整个代码库、跨多文件协作、自主规划和执行开发任务的 Agent。

```
核心定位：AI 驱动的编码助手 × 终端 Agent × 项目级上下文理解
```

### 1.2 核心能力矩阵

| 能力类别 | 具体功能 | 对你的价值 |
|---------|---------|-----------|
| **文件操作** | 读取、编辑、创建、重命名文件 | 批量修改 Prompt 模板、更新知识库文件 |
| **搜索** | 正则搜索、模式查找、代码库探索 | 快速定位 analysis.go 中的逻辑 |
| **执行** | 运行 shell 命令、测试、git 操作 | 自动化 upload_and_report.py 测试流程 |
| **网络** | 搜索文档、查找错误信息 | 调研 API 文档、查找 Bug 解决方案 |
| **Git** | 暂存、提交、分支、PR、合并冲突解决 | 自动生成 commit message、管理分支 |
| **MCP 扩展** | 连接 Jira、Slack、数据库等外部服务 | 可连接 Supabase 操作 CaloriSnap 数据 |
| **多代理** | Subagents 并行处理、Agent Teams 协作 | 类似你现有的 AI 团队评审工作流 |
| **定期任务** | 定时运行 PR 审查、依赖审计等 | 自动化周报素材收集 |

### 1.3 运行平台

| 平台 | 说明 | 推荐度 |
|-----|------|-------|
| **Terminal CLI** | 功能最完整，macOS/Linux/WSL | ⭐⭐⭐⭐⭐ |
| **VS Code 扩展** | 内联 Diff、@-提及 | ⭐⭐⭐⭐ |
| **Desktop App** | 独立应用，可视化 Diff | ⭐⭐⭐⭐ |
| **Web** | 浏览器运行，无需本地安装 | ⭐⭐⭐ |
| **JetBrains** | IntelliJ/PyCharm 等 | ⭐⭐⭐ |

### 1.4 记忆系统（重点）

Claude Code 的记忆系统分两层，与你现有的 Obsidian 记忆体系高度相似：

#### CLAUDE.md（= 你的 MEMORY.md）
- **定位**: 用户手写的持久指令文件
- **加载时机**: 每次会话自动加载
- **作用域层级**:
  - 项目级: `./CLAUDE.md` → 团队共享（类比你的项目 `_README.md`）
  - 用户级: `~/.claude/CLAUDE.md` → 个人偏好（类比你的全局 MEMORY.md）
  - 组织级: 系统目录 → 公司标准
- **最佳实践**: 保持 **200 行以内**，具体可验证的指令

#### Auto Memory（= 你的 episodic 日志）
- **定位**: Claude 自动记录的学习笔记
- **存储**: `~/.claude/projects/<project>/memory/`
- **加载**: 每次会话加载 MEMORY.md 前 200 行
- **内容**: 构建命令、调试模式、架构偏好等

#### 高级规则组织（`.claude/rules/`）

```
your-project/
├── .claude/
│   ├── CLAUDE.md           # 主项目指令
│   └── rules/
│       ├── code-style.md   # 代码风格
│       ├── testing.md      # 测试约定
│       └── security.md     # 安全要求
```

支持 **路径限定规则**，比如只在处理 `src/api/**/*.ts` 时加载 API 开发规则。

### 1.5 扩展体系

| 扩展机制 | 作用 | 上下文成本 | 你的使用场景 |
|---------|------|-----------|------------|
| **CLAUDE.md** | 每次加载的持久规则 | 高 | 项目约定、编码标准 |
| **Skills** | 按需加载的可复用知识/工作流 | 低 | `/deploy` 部署清单、API 文档 |
| **Subagents** | 隔离执行上下文 | 与主会话隔离 | 研究任务、安全审查 |
| **Agent Teams** | 多独立会话协调 | 高 | 并行 PR 审查、多模块开发 |
| **MCP** | 连接外部服务 | 中 | 数据库查询、Slack 通知 |
| **Hooks** | 事件触发的确定性脚本 | 零 | 每次编辑后自动 lint |
| **Plugins** | 打包分发上述功能 | - | 跨仓库共享配置 |

### 1.6 最佳实践总结

#### 黄金法则
1. **给 Claude 验证方式** → 提供测试用例、预期输出
2. **先探索 → 再规划 → 最后编码** → Plan Mode 先行
3. **指令要具体** → "使用 2 空格缩进" > "格式化代码"
4. **管理 Context Window** → 定期 `/clear`，用 Subagents 隔离

#### 常见陷阱
| 陷阱 | 症状 | 解法 |
|-----|------|-----|
| 厨房水槽会话 | 混杂不相关任务 | 任务间 `/clear` |
| 过度改正 | Context 被失败方法污染 | 两次失败后 `/clear` 重写提示 |
| CLAUDE.md 过大 | 指令被忽略 | 保持 200 行内，参考材料移到 Skills |
| 缺乏验证 | 代码看似正确但有漏洞 | 始终提供测试用例 |

### 1.7 CLI 命令速查

| 命令 | 功能 |
|------|------|
| `claude` | 启动交互模式 |
| `claude "任务"` | 运行一次性任务 |
| `claude -p "查询"` | 查询后退出（管道友好） |
| `claude -c` | 继续最近对话 |
| `claude -r` | 恢复之前对话 |
| `claude commit` | Git 提交 |
| `/clear` | 清除对话历史 |
| `/init` | 自动生成 CLAUDE.md |
| `/memory` | 查看/编辑记忆文件 |
| `/compact` | 压缩上下文 |
| `/agents` | 配置 Subagents |
| `/doctor` | 诊断安装问题 |
| `Shift+Tab` | 切换 Plan Mode |

### 1.8 定价

| 方案 | 价格 | 适用场景 |
|------|------|---------|
| **Claude Pro** | $20/月 | 个人开发者入门 |
| **Claude Max** | $100/月 | 重度使用 |
| **Claude Console** | 按 token 付费 | CI/CD、脚本自动化 |
| **Claude Code Internal（司内）** | 免费（公司提供） | 司内工作场景 |

---

## 二、Codex CLI 概览

### 2.1 它是什么

OpenAI 推出的终端编程代理，基于 GPT-5 系列模型，开源（Apache-2.0），功能定位与 Claude Code 类似。

### 2.2 核心特性

| 特性 | 说明 |
|------|------|
| **模型** | GPT-5.2-Codex / GPT-5.1-Codex-Max |
| **安装** | `npm install -g @openai/codex` 或 `brew install codex` |
| **记忆** | `AGENTS.md`（类似 CLAUDE.md） |
| **沙箱** | 多级安全模式（Suggest / Auto Edit / Full Auto） |
| **MCP** | 支持 MCP 服务器 |
| **CI/CD** | 支持非交互模式 |
| **认证** | ChatGPT 账号登录或 API Key |
| **开源** | 是（Apache-2.0） |

### 2.3 三种操作模式

| 模式 | 描述 | 安全级别 |
|------|------|---------|
| **Suggest** | 只建议更改，需手动确认 | 最高 |
| **Auto Edit** | 自动编辑文件，命令需确认 | 中等 |
| **Full Auto** | 全自动执行（"YOLO 模式"） | 最低 |

### 2.4 Codex CLI Internal（司内版）

- 安装: `npm install -g --registry=https://mirrors.tencent.com/npm @tencent/codex-internal`
- 启动: `codex-internal`
- 配置: `~/.codex-internal/`
- 支持模型: GPT-5.2-Codex、GPT-5.2、GPT-5.1-Codex-Max、GLM-4.7

---

## 三、Claude Code vs Codex CLI 对比

### 3.1 功能对比

| 维度 | Claude Code | Codex CLI |
|------|------------|-----------|
| **底层模型** | Claude Opus 4.6 / Sonnet 4.6 | GPT-5.3 Codex |
| **代码库理解** | ⭐⭐⭐⭐⭐ 递归探索，深度理解 | ⭐⭐⭐⭐ 良好 |
| **复杂推理** | ⭐⭐⭐⭐⭐ 扩展思考，ultrathink | ⭐⭐⭐⭐ 强 |
| **记忆系统** | CLAUDE.md + Auto Memory + rules/ | AGENTS.md |
| **多代理** | Subagents + Agent Teams | 无原生支持 |
| **Plan Mode** | 原生支持（Shift+Tab） | 无 |
| **沙箱安全** | 检查点 + 权限分级 | 三级沙箱模式 |
| **Git 集成** | 深度（commit、PR、冲突解决） | 基础 |
| **MCP** | 支持 | 支持 |
| **开源** | 否 | 是（Apache-2.0） |
| **定价（入门）** | $20/月 Pro | $200/月 ChatGPT Pro |
| **司内版** | claude-internal ✅ | codex-internal ✅ |

### 3.2 场景推荐

| 场景 | 推荐工具 | 原因 |
|------|---------|------|
| **复杂多文件重构** | Claude Code | 深度上下文 + Subagents 并行 |
| **快速 Bug 修复** | Cursor / CodeBuddy | IDE 内联修复最快 |
| **异步并行任务** | Codex | 后台沙盒虚拟机自主完成 |
| **代码审查** | Claude Code | Plan Mode + 深度推理 |
| **CI/CD 自动化** | 两者均可 | 都支持非交互模式 |
| **文档/测试生成** | Claude Code | 更强的语言理解和结构化输出 |
| **Prompt 调试** | Claude Code | 天然适合（Anthropic 自家工具） |

### 3.3 生态位总结

```
日常编辑         深度推理/自动化      异步批处理
CodeBuddy IDE ← Claude Code CLI → Codex CLI（可选）
     ↑                ↑                   ↑
 图形界面           终端 Agent          后台代理
 快速补全          复杂重构           并行任务
 内联 Diff        Plan Mode          沙盒执行
```

---

## 四、融入你的工作流建议

### 4.1 你的当前工具链

```
核心: CodeBuddy IDE + Obsidian + Git(SSH) + Supabase
辅助: Python 脚本 + upload_and_report.py + launchd 定时任务
```

### 4.2 Claude Code 切入点（按优先级排序）

#### 🥇 P0: UC 对局复盘开发调试
```bash
# 在项目目录启动
cd 10_Work/uc对局复盘/ucgit/go_ai_yr_postmatch_analysis_svr/
claude-internal

# 典型用法
> 读取 analysis.go，分析 jPoints 跳转点逻辑，找到子维度ID映射的处理位置
> 修改 subdim_behId 映射逻辑，将27-30映射改为41-44
> 用描述性消息提交更改
```

**价值**: 替代手动在 Go 代码中定位逻辑 → 修改 → commit → push 的流程。

#### 🥈 P1: Prompt 模板调试与优化
```bash
# 在任意项目中
claude-internal

> 读取当前的 AI NPC prompt 模板，分析其结构
> 优化 prompt 中关于"五行拆字批命"的部分，使回复更有角色感
> 生成 5 个测试用例来验证 prompt 效果
```

**价值**: 你的痛点之一是"AI 生成质量不稳定"，Claude Code 可以帮你系统化调试 Prompt。

#### 🥉 P2: 知识库批量处理
```bash
# 在 Obsidian Vault 目录
cd ~/Documents/Obsidian\ Vault/
claude-internal

> 读取 10_Work/uc 王也 npc/ 下所有 xlsx 文件，统计知识库条数
> 检查知识库中是否有重复或冲突的条目
> 生成知识库质量报告
```

#### P3: 自动化测试流程
```bash
# 管道模式，可脚本化
cat test_results.json | claude-internal -p "分析测试结果，找出失败用例的共性"
```

#### P4: Git 操作自动化
```bash
claude-internal commit  # 自动生成描述性 commit message
```

### 4.3 CLAUDE.md 配置建议

你可以在全局配置 `~/.claude-internal/CLAUDE.md` 写入：

```markdown
# 用户偏好
- 中文输出，Markdown 格式
- Python > JS
- 金字塔原理：结论先行 → 分组归类 → 逻辑递进
- 批判性思维：质疑假设、检验逻辑
- 使用 [[双向链接]] 格式
- 目录放 _README.md

# 工作约定
- Git commit message 使用中文
- 代码注释使用中文
- 修改文件前先备份或创建 git checkpoint
- 新数据入库前先交叉校验

# 常用命令
- Go 项目构建: `go build ./...`
- Python 测试: `python upload_and_report.py`
- Obsidian 同步: `~/.local/bin/obsidian_git_sync.sh`
```

### 4.4 与现有记忆系统的协同

| 你的 Obsidian 记忆 | Claude Code 对应 | 协同方式 |
|-------------------|-----------------|---------|
| `MEMORY.md` | `CLAUDE.md` | 关键偏好同步到两处 |
| `episodic/` 日志 | Auto Memory | Claude 自动记录补充你的手动日志 |
| `procedural/skills.md` | Skills (`/`) | 可复用工作流两处维护 |
| `semantic/context.md` | CLAUDE.md 项目指令 | 项目上下文同步 |
| `.codebuddy/rules/` | `.claude/rules/` | 理念相同，格式兼容 |

### 4.5 学习路径建议

```
Week 1: 安装 + 基础使用
├── 安装 claude-internal（司内版）
├── 在一个小项目中跑通 /init → 对话 → commit 流程
├── 理解 Plan Mode 和 Normal Mode 的切换
└── 配置全局 CLAUDE.md

Week 2: 进阶功能
├── 尝试 Subagents 进行代码审查
├── 配置 .claude/rules/ 分类规则
├── 在 UC 对局复盘项目中实际使用
└── 管道模式 + 非交互模式

Week 3: 工作流整合
├── 与 CodeBuddy IDE 配合使用
├── 编写项目级 CLAUDE.md
├── 尝试 MCP 连接 Supabase
└── 建立日常使用习惯
```

---

## 五、关键参考资料

### Claude Code 官方
- 📖 [官方文档（中文）](https://code.claude.com/docs/zh-CN/overview)
- 🚀 [快速开始](https://code.claude.com/docs/zh-CN/quickstart)
- 🧠 [记忆系统](https://code.claude.com/docs/zh-CN/memory)
- ⚙️ [最佳实践](https://code.claude.com/docs/zh-CN/best-practices)
- 🔄 [常见工作流](https://code.claude.com/docs/zh-CN/common-workflows)
- 🔌 [功能扩展](https://code.claude.com/docs/zh-CN/features-overview)
- 📋 [更新日志](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)

### Claude Code Internal（司内）
- 📖 [iwiki 文档](https://iwiki.woa.com/p/4015845000)
- 💬 CLI Internal 用户交流群

### Codex CLI
- 📖 [官方文档](https://openaicli.com/docs)
- 🐙 [GitHub 仓库](https://github.com/openai/codex)
- 📖 [Getting Started](https://github.com/openai/codex/blob/main/docs/getting-started.md)

### Codex CLI Internal（司内）
- 📖 [iwiki 文档](https://iwiki.woa.com/p/4017410955)

### 对比分析
- 📊 [Codex vs Cursor vs Claude Code 2026](https://www.nxcode.io/zh/resources/news/codex-vs-cursor-vs-claude-code-2026)
- 📊 [Claude Code vs Cursor vs Codex (Beam)](https://getbeam.dev/blog/claude-code-vs-cursor-vs-codex.html)
- 📊 [2026 AI 编码工具终极横评](https://www.aieii.com/posts/2026-03-20-ai-coding-agents-showdown/)
- 📊 [知乎完整指南](https://zhuanlan.zhihu.com/p/1971872808159141982)

---

## 六、Quick Start 操作手册

### 6.1 安装 Claude Code Internal

```bash
# 1. 确保 Node.js >= 20
node -v

# 2. 安装（司内版）
npm install -g --registry=https://mirrors.tencent.com/npm @tencent/claude-code-internal

# 3. 进入项目目录
cd ~/Documents/Obsidian\ Vault/10_Work/uc对局复盘/ucgit/go_ai_yr_postmatch_analysis_svr/

# 4. 启动
claude-internal
# 首次使用会唤起浏览器验证 OA 身份
```

### 6.2 首次配置

```bash
# 在交互模式中
/init    # 自动生成项目 CLAUDE.md
/memory  # 查看记忆状态
```

### 6.3 日常使用模式

```bash
# 模式一：交互式开发
claude-internal
> 帮我分析这个项目的架构

# 模式二：一次性任务
claude-internal "修复 build 错误"

# 模式三：管道处理
cat error.log | claude-internal -p "分析错误原因"

# 模式四：继续上次对话
claude-internal -c

# 模式五：恢复指定对话
claude-internal -r
```

### 6.4 安装 Codex CLI Internal（可选）

```bash
npm install -g --registry=https://mirrors.tencent.com/npm @tencent/codex-internal
cd your-project-dir
codex-internal
```

---

> **下一步**: 安装 `claude-internal`，在 UC 对局复盘项目中完成首次实际使用。
