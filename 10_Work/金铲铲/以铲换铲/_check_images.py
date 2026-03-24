import re, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

for html_name in ['review_20pct_webui.html', 'review_webui.html']:
    with open(html_name, 'r') as f:
        content = f.read()
    
    files = re.findall(r'file:\s*"([^"]+)"', content)
    paths = re.findall(r'path:\s*"([^"]+)"', content)
    
    # Check if it uses _converted.jpg pattern
    uses_converted = '_converted.jpg' in content
    
    total = 0
    missing = 0
    for p, fn in zip(paths, files):
        base = os.path.splitext(fn)[0]
        if uses_converted:
            converted = os.path.join(p, base + '_converted.jpg')
            if os.path.exists(converted):
                total += os.path.getsize(converted)
                continue
        orig = os.path.join(p, fn)
        if os.path.exists(orig):
            total += os.path.getsize(orig)
        else:
            missing += 1
    
    print(f'{html_name}: {len(files)} images, total: {total/1024/1024:.1f}MB, missing: {missing}')
    if uses_converted:
        print(f'  (uses _converted.jpg pattern)')
