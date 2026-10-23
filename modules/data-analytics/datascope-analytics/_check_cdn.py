# -*- coding: utf-8 -*-
import json, urllib.request, ssl, os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def head(url, timeout=10):
    try:
        req = urllib.request.Request(url, method='GET', headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read(20000)
            return r.status, len(data)
    except Exception as e:
        return 'ERR', str(e)[:120]

urls = {
  'jsdelivr_vchart_latest': 'https://cdn.jsdelivr.net/npm/@visactor/vchart@1/build/index.min.js',
  'jsdelivr_vchart_resolved': 'https://data.jsdelivr.com/v1/packages/npm/@visactor/vchart/resolved?specifier=1',
  'unpkg_vchart': 'https://unpkg.com/@visactor/vchart@1/build/index.min.js',
  'jsdelivr_papaparse': 'https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js',
  'cdnjs_papaparse': 'https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.4.1/papaparse.min.js',
  'miaoda_fonts': 'https://miaoda.feishu.cn/fonts/css2?family=Noto+Sans+SC:wght@400;500;700;900&display=swap',
}
for k, u in urls.items():
    st, ln = head(u)
    print(f'{k}: {st} {ln}')

# resolve latest vchart 1.x version
try:
    req = urllib.request.Request('https://data.jsdelivr.com/v1/packages/npm/@visactor/vchart/resolved?specifier=1', headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        d = json.loads(r.read().decode('utf-8'))
        print('vchart resolved version:', d.get('version'))
except Exception as e:
    print('resolve err:', str(e)[:120])

# ensure output dir exists
os.makedirs(r'C:\project\代码研究\数据分析\datascope-analytics', exist_ok=True)
print('dir ok')
