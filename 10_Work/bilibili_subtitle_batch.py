#!/usr/bin/env python3
"""
B站视频批量下载音频 + Whisper转录字幕脚本
- 从链接文件读取所有视频URL
- 用yt-dlp下载音频
- 用whisper转录为文字
- 输出为单个汇总Markdown文件
"""

import subprocess
import os
import sys
import json
import re
import time
import glob

# ========== 配置 ==========
LINKS_FILE = "/Users/liusixing_tx/Documents/Obsidian Vault/10_Work/B站合集链接_海克斯大乱斗.txt"
OUTPUT_DIR = "/Users/liusixing_tx/Documents/Obsidian Vault/10_Work/海克斯大乱斗_字幕"
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
TEXT_DIR = os.path.join(OUTPUT_DIR, "text")
SUMMARY_FILE = "/Users/liusixing_tx/Documents/Obsidian Vault/10_Work/海克斯大乱斗_字幕汇总.md"

WHISPER_MODEL = "base"  # base模型CPU上速度快10倍，中文识别足够用
WHISPER_LANGUAGE = "zh"

# 并发控制
MAX_RETRIES = 2
SLEEP_BETWEEN = 2  # 每个视频间隔秒数，避免被限流

# ========== 工具函数 ==========

def ensure_dirs():
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(TEXT_DIR, exist_ok=True)


def read_links(filepath):
    with open(filepath, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines


def extract_bvid(url):
    m = re.search(r"(BV[a-zA-Z0-9]+)", url)
    return m.group(1) if m else None


def get_video_title(bvid):
    """通过B站API获取视频标题"""
    try:
        result = subprocess.run(
            ["curl", "-s", f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        if data.get("code") == 0:
            return data["data"]["title"]
    except Exception:
        pass
    return bvid


def download_audio(url, bvid):
    """用yt-dlp下载音频，返回音频文件路径"""
    output_path = os.path.join(AUDIO_DIR, f"{bvid}.mp3")
    if os.path.exists(output_path):
        print(f"  [跳过下载] 音频已存在: {bvid}", flush=True)
        return output_path

    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "5",  # 中等质量，节省空间
        "-o", os.path.join(AUDIO_DIR, f"{bvid}.%(ext)s"),
        "--no-playlist",
        "--retries", "3",
        "--socket-timeout", "30",
        url
    ]

    for attempt in range(MAX_RETRIES):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                # yt-dlp 可能生成不同扩展名，查找实际文件
                for ext in ["mp3", "m4a", "wav", "opus", "webm"]:
                    candidate = os.path.join(AUDIO_DIR, f"{bvid}.{ext}")
                    if os.path.exists(candidate):
                        return candidate
                # 尝试glob匹配
                matches = glob.glob(os.path.join(AUDIO_DIR, f"{bvid}.*"))
                if matches:
                    return matches[0]
            print(f"  [重试 {attempt+1}/{MAX_RETRIES}] 下载失败: {result.stderr[:200]}", flush=True)
        except subprocess.TimeoutExpired:
            print(f"  [重试 {attempt+1}/{MAX_RETRIES}] 下载超时", flush=True)
        time.sleep(3)

    return None


def transcribe_audio(audio_path, bvid):
    """用whisper转录音频，返回文字"""
    text_path = os.path.join(TEXT_DIR, f"{bvid}.txt")
    if os.path.exists(text_path):
        print(f"  [跳过转录] 文字已存在: {bvid}", flush=True)
        with open(text_path, "r") as f:
            return f.read()

    try:
        # 使用whisper命令行
        cmd = [
            "whisper",
            audio_path,
            "--model", WHISPER_MODEL,
            "--language", WHISPER_LANGUAGE,
            "--output_format", "txt",
            "--output_dir", TEXT_DIR,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode == 0:
            # whisper输出文件名基于输入文件名
            audio_basename = os.path.splitext(os.path.basename(audio_path))[0]
            whisper_output = os.path.join(TEXT_DIR, f"{audio_basename}.txt")
            if os.path.exists(whisper_output):
                # 重命名为bvid.txt（如果不同）
                if whisper_output != text_path:
                    os.rename(whisper_output, text_path)
                with open(text_path, "r") as f:
                    return f.read()
        print(f"  [转录失败] {result.stderr[:200]}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"  [转录超时] {bvid}", flush=True)
    except Exception as e:
        print(f"  [转录错误] {e}", flush=True)

    return None


def generate_summary(results):
    """生成汇总Markdown文件"""
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write("# 海克斯大乱斗 - 视频字幕汇总\n\n")
        f.write(f"- **UP主**: 安逸天晴\n")
        f.write(f"- **视频总数**: {len(results)}\n")
        f.write(f"- **成功转录**: {sum(1 for r in results if r['text'])}\n")
        f.write(f"- **转录失败**: {sum(1 for r in results if not r['text'])}\n")
        f.write(f"- **生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Whisper模型**: {WHISPER_MODEL}\n\n")
        f.write("---\n\n")

        for i, r in enumerate(results, 1):
            f.write(f"## {i}. {r['title']}\n\n")
            f.write(f"- **BV号**: {r['bvid']}\n")
            f.write(f"- **链接**: {r['url']}\n\n")
            if r["text"]:
                f.write(f"### 转录内容\n\n")
                f.write(r["text"].strip())
                f.write("\n\n")
            else:
                f.write(f"> ⚠️ 转录失败\n\n")
            f.write("---\n\n")

    print(f"\n✅ 汇总文件已生成: {SUMMARY_FILE}", flush=True)


# ========== 主流程 ==========

def main():
    ensure_dirs()

    links = read_links(LINKS_FILE)
    total = len(links)
    print(f"📋 共 {total} 个视频待处理\n", flush=True)

    # 加载已有进度
    progress_file = os.path.join(OUTPUT_DIR, "progress.json")
    progress = {}
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            progress = json.load(f)
        print(f"📌 检测到已有进度，已完成 {len(progress)} 个\n", flush=True)

    results = []

    for i, url in enumerate(links, 1):
        bvid = extract_bvid(url)
        if not bvid:
            print(f"[{i}/{total}] ❌ 无法解析BV号: {url}", flush=True)
            results.append({"bvid": "unknown", "url": url, "title": "未知", "text": None})
            continue

        # 检查是否已处理
        if bvid in progress:
            print(f"[{i}/{total}] ⏩ 已处理: {progress[bvid]['title']}", flush=True)
            results.append(progress[bvid])
            continue

        print(f"[{i}/{total}] 🎬 处理: {bvid}", flush=True)

        # 1. 获取标题
        title = get_video_title(bvid)
        print(f"  标题: {title}", flush=True)

        # 2. 下载音频
        print(f"  📥 下载音频...", flush=True)
        audio_path = download_audio(url, bvid)
        if not audio_path:
            print(f"  ❌ 下载失败，跳过", flush=True)
            result = {"bvid": bvid, "url": url, "title": title, "text": None}
            results.append(result)
            progress[bvid] = result
            with open(progress_file, "w") as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
            continue

        # 3. Whisper转录
        print(f"  🎙️ 转录中...", flush=True)
        text = transcribe_audio(audio_path, bvid)
        if text:
            print(f"  ✅ 转录完成 ({len(text)} 字)", flush=True)
        else:
            print(f"  ❌ 转录失败", flush=True)

        result = {"bvid": bvid, "url": url, "title": title, "text": text}
        results.append(result)

        # 保存进度
        progress[bvid] = result
        with open(progress_file, "w") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

        # 间隔
        if i < total:
            time.sleep(SLEEP_BETWEEN)

    # 生成汇总
    generate_summary(results)

    # 统计
    success = sum(1 for r in results if r["text"])
    failed = total - success
    print(f"\n📊 处理完成: 成功 {success}/{total}, 失败 {failed}", flush=True)


if __name__ == "__main__":
    main()
