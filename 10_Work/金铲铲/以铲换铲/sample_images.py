#!/usr/bin/env python3
"""分层50%随机抽样脚本"""
import os, random, json

random.seed(42)

base = '金铲铲的图片 3'
categories = {
    'L1_不是铲子': f'{base}/不是铲子',
    'L2_是铲子但不符合金铲铲': f'{base}/是铲子但不符合金铲铲',
    'L3_是金铲铲_无手工': f'{base}/符合金铲铲/是金铲铲（无手工痕迹）',
    'L4_较优秀_有手工': f'{base}/符合金铲铲/较优秀金铲铲（有手工痕迹）',
    'L5_优秀_强手工': f'{base}/符合金铲铲/优秀金铲铲（强手工痕迹及创意）',
}

IMG_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.avif', '.gif'}
result = {}
total_all = 0
sampled_all = 0

for cat_key, cat_path in categories.items():
    files = [f for f in os.listdir(cat_path) if os.path.splitext(f)[1].lower() in IMG_EXTS]
    files.sort()
    n = max(1, len(files) // 2)
    sampled = random.sample(files, n)
    result[cat_key] = {
        'path': cat_path,
        'total': len(files),
        'sampled': len(sampled),
        'files': sampled
    }
    total_all += len(files)
    sampled_all += len(sampled)
    print(f'{cat_key}: {len(files)}张 → 抽样{len(sampled)}张')

print(f'\n总计: {total_all}张 → 抽样{sampled_all}张 ({sampled_all/total_all*100:.1f}%)')

with open('sampled_images.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print('\n抽样结果已保存到 sampled_images.json')
