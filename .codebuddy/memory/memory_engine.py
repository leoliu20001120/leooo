#!/usr/bin/env python3
"""
🧠 CodeBuddy 记忆管理引擎 v2.1
=================================

用法:
  python3 memory_engine.py tree
  python3 memory_engine.py stats
  python3 memory_engine.py health
  python3 memory_engine.py search "关键词"
  python3 memory_engine.py index
"""

import os
import re
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# ============================================================
# 配置
# ============================================================

MEMORY_ROOT = Path(__file__).parent
EPISODIC_DIR = MEMORY_ROOT / "episodic"
SEMANTIC_DIR = MEMORY_ROOT / "semantic"
PROCEDURAL_DIR = MEMORY_ROOT / "procedural"
WORKING_DIR = MEMORY_ROOT / "working"
MEMORY_FILE = MEMORY_ROOT / "MEMORY.md"

# 文件大小阈值
MAX_LINES_WARNING = 200
MAX_LINES_CRITICAL = 400


# ============================================================
# 工具函数
# ============================================================

def get_date_from_filename(filename: str) -> datetime | None:
    match = re.match(r"(\d{4}-\d{2}-\d{2})\.md$", filename)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d")
    return None


def count_lines(filepath: Path) -> int:
    try:
        return len(filepath.read_text(encoding="utf-8").splitlines())
    except Exception:
        return 0


def count_chars(filepath: Path) -> int:
    """统计字符数（比'字数'更准确且不需要分词）"""
    try:
        text = filepath.read_text(encoding="utf-8")
        # 减去空行和纯标记行
        return len(text.replace("\n", "").replace(" ", ""))
    except Exception:
        return 0


# ============================================================
# 命令: tree
# ============================================================

def cmd_tree(args):
    """显示记忆系统文件树"""
    print("🧠 记忆系统文件树\n")

    def show_dir(path: Path, prefix: str = "", is_last: bool = True):
        if not path.exists():
            return

        items = sorted(path.iterdir())
        # 过滤掉 .py 和隐藏文件
        items = [i for i in items if not i.name.startswith(".") and i.suffix != ".py"]

        for idx, item in enumerate(items):
            is_last_item = (idx == len(items) - 1)
            connector = "└── " if is_last_item else "├── "

            if item.is_file():
                lines = count_lines(item)
                chars = count_chars(item)
                size_info = f"({lines}行, {chars}字符)"
                print(f"{prefix}{connector}{item.name} {size_info}")
            elif item.is_dir():
                file_count = len(list(item.glob("*.md")))
                print(f"{prefix}{connector}{item.name}/ ({file_count}个文件)")
                next_prefix = prefix + ("    " if is_last_item else "│   ")
                show_dir(item, next_prefix, is_last_item)

    print(f"{MEMORY_ROOT.name}/")
    show_dir(MEMORY_ROOT)


# ============================================================
# 命令: stats
# ============================================================

def cmd_stats(args):
    """记忆统计"""
    print("📊 记忆系统统计\n")

    dirs = {
        "semantic":   SEMANTIC_DIR,
        "procedural": PROCEDURAL_DIR,
        "episodic":   EPISODIC_DIR,
        "working":    WORKING_DIR,
    }

    total_files = 0
    total_lines = 0

    # MEMORY.md
    if MEMORY_FILE.exists():
        ml = count_lines(MEMORY_FILE)
        print(f"  MEMORY.md          {ml:>4} 行")
        total_lines += ml
        total_files += 1

    print()

    for name, dirpath in dirs.items():
        if not dirpath.exists():
            print(f"  {name + '/':<20} (不存在)")
            continue

        files = sorted(dirpath.glob("*.md"))
        dir_lines = 0
        for f in files:
            lc = count_lines(f)
            dir_lines += lc
            flag = " ⚠️" if lc > MAX_LINES_WARNING else ""
            print(f"    {f.name:<28} {lc:>4} 行{flag}")

        total_files += len(files)
        total_lines += dir_lines
        print(f"  {'─' * 38}")

    print(f"\n  合计: {total_files} 个文件, {total_lines} 行")

    # 情景记忆时间跨度
    if EPISODIC_DIR.exists():
        dates = []
        for f in EPISODIC_DIR.glob("*.md"):
            d = get_date_from_filename(f.name)
            if d:
                dates.append(d)
        if dates:
            span = (max(dates) - min(dates)).days + 1
            print(f"  情景记忆: {min(dates).strftime('%m-%d')} → {max(dates).strftime('%m-%d')} ({span}天, {len(dates)}个日志)")


# ============================================================
# 命令: health
# ============================================================

def cmd_health(args):
    """健康检查——只检查真正重要的东西"""
    print("🏥 记忆健康检查\n")

    problems = []
    ok = []

    # 1. MEMORY.md 必须存在
    if MEMORY_FILE.exists():
        ok.append("MEMORY.md 存在")
    else:
        problems.append("❌ MEMORY.md 缺失！这是核心启动文件")

    # 2. 今天的日志
    today = datetime.now().strftime("%Y-%m-%d")
    today_file = EPISODIC_DIR / f"{today}.md"
    if today_file.exists():
        ok.append(f"今日日志 ({today}) 存在")
    else:
        problems.append(f"⚠️  今日日志 ({today}.md) 未创建")

    # 3. 各目录存在性
    for name, path in [("semantic/", SEMANTIC_DIR), ("procedural/", PROCEDURAL_DIR),
                        ("episodic/", EPISODIC_DIR), ("working/", WORKING_DIR)]:
        if path.exists() and list(path.glob("*.md")):
            ok.append(f"{name} 正常")
        else:
            problems.append(f"⚠️  {name} 为空或不存在")

    # 4. 文件膨胀检查
    for dirpath in [SEMANTIC_DIR, PROCEDURAL_DIR]:
        if not dirpath.exists():
            continue
        for f in dirpath.glob("*.md"):
            lc = count_lines(f)
            if lc > MAX_LINES_CRITICAL:
                problems.append(f"🔴 {f.name} 有 {lc} 行，建议拆分")
            elif lc > MAX_LINES_WARNING:
                problems.append(f"🟡 {f.name} 有 {lc} 行，接近上限")

    # 5. 超过30天的旧日志
    if EPISODIC_DIR.exists():
        cutoff = datetime.now() - timedelta(days=30)
        old = [f for f in EPISODIC_DIR.glob("*.md")
               if (d := get_date_from_filename(f.name)) and d < cutoff]
        if old:
            problems.append(f"⚠️  {len(old)} 个日志超30天，应蒸馏后归档")

    # 6. working 有未完成任务？
    wf = WORKING_DIR / "current.md"
    if wf.exists():
        content = wf.read_text(encoding="utf-8")
        if "🔴" in content or "🟡" in content:
            problems.append("📌 有未完成的跨会话任务")

    # 输出
    for item in ok:
        print(f"  ✅ {item}")
    for item in problems:
        print(f"  {item}")

    score = len(ok) / (len(ok) + len(problems)) * 100 if (ok or problems) else 0
    print(f"\n  健康度: {score:.0f}%")


# ============================================================
# 命令: search
# ============================================================

def cmd_search(args):
    """搜索记忆"""
    query = args.query.lower()
    print(f"🔍 搜索: \"{args.query}\"\n")

    results = []

    # 搜索所有 md 文件
    for f in sorted(MEMORY_ROOT.rglob("*.md")):
        # 跳过 archive 目录
        if "archive" in str(f):
            continue
        try:
            content = f.read_text(encoding="utf-8")
            if query in content.lower():
                matches = [(i, line.strip())
                           for i, line in enumerate(content.splitlines(), 1)
                           if query in line.lower()]
                results.append((f.relative_to(MEMORY_ROOT), matches))
        except Exception:
            continue

    if not results:
        print("  未找到匹配")
        return

    for rel_path, matches in results:
        print(f"📄 {rel_path} ({len(matches)}处)")
        for line_no, text in matches[:3]:
            # 截断过长的行
            if len(text) > 80:
                text = text[:77] + "..."
            print(f"   L{line_no}: {text}")
        if len(matches) > 3:
            print(f"   ... +{len(matches) - 3}处")
        print()


# ============================================================
# 命令: index
# ============================================================

INDEX_FILE = MEMORY_ROOT / "_index.md"

def cmd_index(args):
    """自动生成/更新 _index.md 索引文件"""
    print("📇 生成记忆索引...\n")

    lines = [
        "# 🗂️ 记忆系统索引\n",
        f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} | 由 `memory_engine.py index` 更新\n",
        "---\n",
        "## 文件清单\n",
        "| 文件 | 类别 | 行数 |",
        "|------|------|------|",
    ]

    category_map = {
        "MEMORY.md": "核心",
        "semantic": "语义",
        "procedural": "程序",
        "episodic": "情景",
        "working": "工作",
    }

    file_entries = []

    # MEMORY.md
    if MEMORY_FILE.exists():
        lc = count_lines(MEMORY_FILE)
        file_entries.append(("MEMORY.md", "核心", lc))

    # 各子目录
    for dirname in ["semantic", "procedural", "episodic", "working"]:
        dirpath = MEMORY_ROOT / dirname
        if not dirpath.exists():
            continue
        cat = category_map.get(dirname, dirname)
        for f in sorted(dirpath.glob("*.md")):
            lc = count_lines(f)
            rel = f"{dirname}/{f.name}"
            file_entries.append((rel, cat, lc))

    for fname, cat, lc in file_entries:
        lines.append(f"| `{fname}` | {cat} | {lc} |")

    # 高频关键词提取
    lines.append("")
    lines.append("## 高频关键词\n")
    lines.append("| 关键词 | 出现文件数 |")
    lines.append("|--------|-----------|")

    # 统计关键词
    keyword_files = defaultdict(set)
    all_md_files = list(MEMORY_ROOT.rglob("*.md"))
    # 排除 _index.md 自身
    all_md_files = [f for f in all_md_files if f.name != "_index.md"]

    for f in all_md_files:
        try:
            content = f.read_text(encoding="utf-8").lower()
        except Exception:
            continue
        # 提取 ## 标题中的关键词
        for m in re.finditer(r"^#{1,3}\s+(.+)$", content, re.MULTILINE):
            heading = m.group(1).strip().lower()
            # 跳过过短或纯格式的标题
            if len(heading) < 2 or heading.startswith("|"):
                continue
            keyword_files[heading].add(str(f.relative_to(MEMORY_ROOT)))

    # 按出现文件数排序，取 top 15
    sorted_kw = sorted(keyword_files.items(), key=lambda x: -len(x[1]))
    for kw, files in sorted_kw[:15]:
        if len(files) >= 2:  # 至少出现在 2 个文件中
            lines.append(f"| {kw} | {len(files)} |")

    # 项目速查
    lines.append("")
    lines.append("## 项目速查\n")
    lines.append("| 项目 | 路径 |")
    lines.append("|------|------|")

    # 从 MEMORY.md 中提取活跃项目
    if MEMORY_FILE.exists():
        mem_content = MEMORY_FILE.read_text(encoding="utf-8")
        for m in re.finditer(r"###\s+.+?`([^`]+)`", mem_content):
            path = m.group(1)
            # 提取 ### 后面的文字（去掉 emoji）
            line = m.group(0)
            name = re.sub(r"###\s+[^\w]*\s*", "", line).split("`")[0].strip()
            lines.append(f"| {name} | `{path}` |")

    output = "\n".join(lines) + "\n"
    INDEX_FILE.write_text(output, encoding="utf-8")
    print(f"  ✅ 已写入 {INDEX_FILE.name} ({len(file_entries)} 个文件)")


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="🧠 记忆管理引擎 v2.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("tree", help="显示记忆文件树")
    sub.add_parser("stats", help="统计仪表盘")
    sub.add_parser("health", help="健康检查")
    p_search = sub.add_parser("search", help="搜索记忆")
    p_search.add_argument("query", help="关键词")
    sub.add_parser("index", help="生成/更新 _index.md 索引")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {"tree": cmd_tree, "stats": cmd_stats, "health": cmd_health,
     "search": cmd_search, "index": cmd_index}[args.command](args)


if __name__ == "__main__":
    main()
