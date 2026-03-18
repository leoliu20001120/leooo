#!/usr/bin/env python3
"""
Skills Usage Analyzer
====================
从 .codebuddy/memory/ 日志中提取 skill 使用情况，
生成结构化数据供周报使用。
"""

import os
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# ── 已知 Skills 清单 ──────────────────────────────────────────────
KNOWN_SKILLS = {
    # Anthropic 官方
    "algorithmic-art":      {"emoji": "🎨", "category": "创意设计", "alias": ["算法艺术"]},
    "brand-guidelines":     {"emoji": "🏷️", "category": "创意设计", "alias": ["品牌规范"]},
    "canvas-design":        {"emoji": "🖼️", "category": "创意设计", "alias": ["canvas设计", "Canvas"]},
    "claude-api":           {"emoji": "🔌", "category": "开发工具", "alias": ["Claude API"]},
    "doc-coauthoring":      {"emoji": "📝", "category": "文档处理", "alias": ["文档协作"]},
    "docx":                 {"emoji": "📄", "category": "文档处理", "alias": ["Word", "word文档"]},
    "frontend-design":      {"emoji": "🎨", "category": "开发工具", "alias": ["前端设计"]},
    "internal-comms":       {"emoji": "📢", "category": "沟通协作", "alias": ["内部沟通"]},
    "markitdown":           {"emoji": "📋", "category": "文档处理", "alias": ["转Markdown"]},
    "mcp-builder":          {"emoji": "🔧", "category": "开发工具", "alias": ["MCP构建"]},
    "memory-management":    {"emoji": "🧠", "category": "效率工具", "alias": ["记忆管理"]},
    "pdf":                  {"emoji": "📕", "category": "文档处理", "alias": ["PDF处理"]},
    "planning-with-files":  {"emoji": "📊", "category": "效率工具", "alias": ["任务规划", "文件规划"]},
    "pptx":                 {"emoji": "📽️", "category": "文档处理", "alias": ["PPT", "演示文稿"]},
    "self-improving-agent": {"emoji": "🔄", "category": "效率工具", "alias": ["自我改进", "错题本"]},
    "skill-creator":        {"emoji": "⚙️", "category": "元工具",   "alias": ["Skill创建"]},
    "slack-gif-creator":    {"emoji": "🎬", "category": "创意设计", "alias": ["GIF创建"]},
    "theme-factory":        {"emoji": "🎭", "category": "创意设计", "alias": ["主题工厂"]},
    "using-superpowers":    {"emoji": "⚡", "category": "元工具",   "alias": ["超能力"]},
    "web-artifacts-builder":{"emoji": "🌐", "category": "开发工具", "alias": ["Web构建"]},
    "webapp-testing":       {"emoji": "🧪", "category": "开发工具", "alias": ["Web测试"]},
    "xlsx":                 {"emoji": "📊", "category": "文档处理", "alias": ["Excel", "表格"]},
}

CATEGORIES = {
    "创意设计": "🎨",
    "开发工具": "🔧",
    "文档处理": "📄",
    "效率工具": "⚡",
    "沟通协作": "💬",
    "元工具":   "🔩",
}


def get_workspace_root():
    """获取工作空间根目录"""
    return Path(__file__).resolve().parent.parent.parent


def get_memory_dir():
    """获取 memory 目录"""
    return get_workspace_root() / ".codebuddy" / "memory"


def get_week_range(date=None):
    """获取指定日期所在周的范围 (周一到周日)"""
    if date is None:
        date = datetime.now().date()
    start = date - timedelta(days=date.weekday())  # 周一
    end = start + timedelta(days=6)  # 周日
    return start, end


def get_last_week_range():
    """获取上一周的范围"""
    today = datetime.now().date()
    last_week_end = today - timedelta(days=today.weekday() + 1)  # 上周日
    last_week_start = last_week_end - timedelta(days=6)  # 上周一
    return last_week_start, last_week_end


def read_memory_files(start_date, end_date):
    """读取指定日期范围内的所有 memory 文件"""
    memory_dir = get_memory_dir()
    entries = []
    
    current = start_date
    while current <= end_date:
        filename = f"{current.strftime('%Y-%m-%d')}.md"
        filepath = memory_dir / filename
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            entries.append({
                "date": current,
                "content": content,
                "filename": filename,
            })
        current += timedelta(days=1)
    
    return entries


def is_listing_section(section, section_title):
    """判断一个段落是否是"清单/列举"型（如安装记录、Skill清单），而非真正使用"""
    title_lower = section_title.lower()
    
    # 标题关键词排除：安装、清单、列表
    listing_keywords = [
        "安装", "install", "清单", "列表", "list",
        "完整 skill", "全部 skill", "skill 清单",
        "部署", "配置", "setup",
    ]
    for kw in listing_keywords:
        if kw in title_lower:
            return True
    
    # 如果段落中列举了超过 5 个不同的 skill 名称 → 大概率是清单
    section_lower = section.lower()
    mentioned_count = 0
    for skill_name in KNOWN_SKILLS:
        if skill_name.lower() in section_lower:
            mentioned_count += 1
    if mentioned_count >= 6:
        return True
    
    # 如果是纯列表格式（大量 "- xxx —" 行）
    list_lines = [l for l in section.split("\n") if re.match(r'^-\s+\S+\s+—', l.strip())]
    if len(list_lines) >= 5:
        return True
    
    return False


# ── 语义推断规则 ──────────────────────────────────────────────────
# 当段落内容没有直接提及 skill 名称时，通过内容关键词推断使用了哪些 skill
SEMANTIC_RULES = [
    {
        "skill": "frontend-design",
        "keywords": [
            "html", "css", "prototype", "原型", "ui", "ux", "页面设计",
            "前端", "组件", "样式", "配色", "动画", "交互", "布局",
            "响应式", "figma", "svg", "canvas", ".html",
        ],
        "min_match": 2,  # 至少命中 2 个关键词
    },
    {
        "skill": "doc-coauthoring",
        "keywords": [
            "文档", "readme", "_readme", "prd", "需求文档",
            "技术方案", "设计文档", "规范", "说明文档",
            "撰写", "编写文档", "知识库",
        ],
        "min_match": 2,
    },
    {
        "skill": "planning-with-files",
        "keywords": [
            "规划", "里程碑", "阶段", "phase", "mvp", "路线图",
            "任务分解", "工作计划", "四阶段", "进度", "迭代",
        ],
        "min_match": 2,
    },
    {
        "skill": "xlsx",
        "keywords": [
            ".xlsx", "excel", "电子表格", "spreadsheet", "数据表",
            "sku", "数据收集", "热量数据", "种子数据", "品牌数据",
        ],
        "min_match": 2,
    },
    {
        "skill": "webapp-testing",
        "keywords": [
            "测试脚本", "test_", "e2e", "端到端测试", "验证方案",
            "准确率", "达标线", "测试用例",
        ],
        "min_match": 2,
    },
    {
        "skill": "memory-management",
        "keywords": [
            "知识库", "目录结构", "目录重构", "归档", "索引",
            "memory", "记忆", "知识沉淀", "分类体系",
        ],
        "min_match": 2,
    },
    {
        "skill": "skill-creator",
        "keywords": [
            "skill", "技能", "周报系统", "tracker",
            "分析引擎", "自动化",
        ],
        "min_match": 2,
    },
]


def infer_skills_from_content(section, section_title):
    """基于内容关键词语义推断使用了哪些 skill"""
    text = (section_title + " " + section).lower()
    inferred = set()
    
    for rule in SEMANTIC_RULES:
        hit_count = sum(1 for kw in rule["keywords"] if kw.lower() in text)
        if hit_count >= rule["min_match"]:
            inferred.add(rule["skill"])
    
    return inferred


def extract_skill_usage(entries):
    """从 memory 条目中提取 skill 使用记录
    
    核心策略：
    1. 优先检测显式使用标记："使用 xxx skill"、"(xxx skill)"
    2. 排除清单/安装型段落（列举了大量 skill 名称但并非真正使用）
    3. 在"解决问题"型段落中匹配 skill 名称
    """
    usages = []
    
    # 构建匹配模式：skill 名称 + 别名
    skill_patterns = {}
    for skill_name, info in KNOWN_SKILLS.items():
        patterns = [skill_name, skill_name.replace("-", " "), skill_name.replace("-", "_")]
        patterns.extend(info.get("alias", []))
        skill_patterns[skill_name] = patterns
    
    for entry in entries:
        content = entry["content"]
        date = entry["date"]
        
        # 按 ## 标题分割成段落
        sections = re.split(r'\n(?=## )', content)
        
        for section in sections:
            # 提取标题
            title_match = re.match(r'##\s+(.+)', section)
            if not title_match:
                continue
            section_title = title_match.group(1).strip()
            
            # ── 排除清单型段落 ──
            if is_listing_section(section, section_title):
                continue
            
            section_lower = section.lower()
            matched_skills = set()
            
            # ── 策略 1：显式使用标记（高置信度） ──
            explicit_patterns = [
                r'使用\s*(\S+?)\s*skill',
                r'using\s+(\S+?)\s+skill',
                r'\(使用\s*(\S+?)\s*skill\)',
                r'\((\S+?)\s+skill\)',
                r'skill[：:]\s*(\S+)',
                r'通过\s*(\S+?)\s*skill',
                r'借助\s*(\S+?)\s*skill',
                r'调用了?\s*(\S+?)\s*skill',
            ]
            for pat in explicit_patterns:
                matches = re.findall(pat, section_lower)
                for m in matches:
                    m_clean = m.strip().lower().replace(" ", "-")
                    for skill_name in KNOWN_SKILLS:
                        if m_clean in skill_name or skill_name in m_clean:
                            matched_skills.add(skill_name)
            
            # ── 策略 2：上下文关联匹配（标题或正文中提及 skill，且段落描述了具体工作） ──
            has_action_context = any(kw in section_lower for kw in [
                "创建", "生成", "修改", "更新", "升级", "实现", "完成",
                "开发", "设计", "构建", "编写", "部署", "测试", "修复",
                "分析", "整理", "重构", "优化", "新增", "添加",
                "create", "build", "implement", "update", "fix", "add",
            ])
            
            if has_action_context:
                for skill_name, patterns in skill_patterns.items():
                    for pattern in patterns:
                        if pattern.lower() in section_lower:
                            matched_skills.add(skill_name)
                            break
            
            # ── 策略 3：基于内容语义的推断（当段落没有直接提及 skill 名称时） ──
            if has_action_context and not matched_skills:
                inferred = infer_skills_from_content(section, section_title)
                matched_skills.update(inferred)
            
            if matched_skills:
                # 提取该段落描述的"解决了什么问题"
                problem_desc = extract_problem_description(section, section_title)
                
                for skill in matched_skills:
                    usages.append({
                        "date": date,
                        "skill": skill,
                        "section_title": section_title,
                        "problem": problem_desc,
                        "category": KNOWN_SKILLS[skill]["category"],
                    })
    
    return usages


def extract_problem_description(section, title):
    """提取段落所描述的问题/任务"""
    # 优先取标题作为问题描述
    desc = title
    
    # 尝试提取更具体的描述（第一段正文）
    lines = section.split("\n")
    for line in lines[1:]:
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-") and not line.startswith("|") and not line.startswith("```"):
            desc = line[:100]
            break
    
    return desc


def aggregate_stats(usages):
    """汇总统计数据"""
    stats = {
        "total_uses": len(usages),
        "unique_skills": len(set(u["skill"] for u in usages)),
        "by_skill": defaultdict(lambda: {"count": 0, "problems": [], "dates": set()}),
        "by_category": defaultdict(lambda: {"count": 0, "skills": set()}),
        "by_date": defaultdict(lambda: {"count": 0, "skills": set()}),
        "daily_breakdown": defaultdict(list),
    }
    
    for u in usages:
        skill = u["skill"]
        cat = u["category"]
        date_str = u["date"].strftime("%Y-%m-%d")
        
        stats["by_skill"][skill]["count"] += 1
        stats["by_skill"][skill]["problems"].append({
            "date": date_str,
            "title": u["section_title"],
            "desc": u["problem"],
        })
        stats["by_skill"][skill]["dates"].add(date_str)
        
        stats["by_category"][cat]["count"] += 1
        stats["by_category"][cat]["skills"].add(skill)
        
        stats["by_date"][date_str]["count"] += 1
        stats["by_date"][date_str]["skills"].add(skill)
        
        stats["daily_breakdown"][date_str].append({
            "skill": skill,
            "title": u["section_title"],
        })
    
    # 转换 set 为 list 以便 JSON 序列化
    for k, v in stats["by_skill"].items():
        v["dates"] = sorted(list(v["dates"]))
    for k, v in stats["by_category"].items():
        v["skills"] = sorted(list(v["skills"]))
    for k, v in stats["by_date"].items():
        v["skills"] = sorted(list(v["skills"]))
    
    return stats


def analyze_week(start_date=None, end_date=None):
    """分析指定周的 skill 使用情况"""
    if start_date is None or end_date is None:
        start_date, end_date = get_week_range()
    
    entries = read_memory_files(start_date, end_date)
    usages = extract_skill_usage(entries)
    stats = aggregate_stats(usages)
    
    return {
        "period": {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "week_number": start_date.isocalendar()[1],
        },
        "entries_count": len(entries),
        "stats": stats,
        "raw_usages": usages,
    }


if __name__ == "__main__":
    # 分析本周
    result = analyze_week()
    print(f"📊 Week {result['period']['week_number']}: "
          f"{result['period']['start']} ~ {result['period']['end']}")
    print(f"   日志文件数: {result['entries_count']}")
    print(f"   总使用次数: {result['stats']['total_uses']}")
    print(f"   涉及 Skills: {result['stats']['unique_skills']} 个")
    print()
    
    for skill, data in sorted(
        result["stats"]["by_skill"].items(),
        key=lambda x: x[1]["count"],
        reverse=True
    ):
        info = KNOWN_SKILLS.get(skill, {})
        emoji = info.get("emoji", "❓")
        print(f"   {emoji} {skill}: {data['count']}次")
        for p in data["problems"]:
            print(f"      └── [{p['date']}] {p['title']}")
