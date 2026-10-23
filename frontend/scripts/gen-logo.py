"""白泽 Logo · 多尺寸 PNG 生成脚本（品牌资源再生成用）

用法：
    python frontend/scripts/gen-logo.py

依赖：Pillow（pip install Pillow）
产出（写入 frontend/public/）：
    favicon-16.png / favicon-32.png / favicon-48.png / apple-touch-icon.png(180) / logo-mark-512.png

图形与矢量源一致：渐变方章 + 白色几何「白」（丿 + 日 + 瞳）+ 泽之水波。
采用超采样(4x) + LANCZOS 降采样，边缘平滑；小尺寸自动省略水波细节以避免糊化。
主用资源为 SVG（logo-mark.svg / favicon.svg / logo.svg / logo-mark-mono.svg），
PNG 仅供不支持 SVG 的场景（旧版 Safari、apple-touch-icon）兜底。
"""
import os
from PIL import Image, ImageDraw

STOPS = [(0.0, (0x34, 0xD3, 0x99)), (0.48, (0x10, 0xB9, 0x81)), (1.0, (0x06, 0xB6, 0xD4))]


def lerp(a, b, t):
    return int(round(a + (b - a) * t))


def grad_color(t):
    t = max(0.0, min(1.0, t))
    for i in range(len(STOPS) - 1):
        t0, c0 = STOPS[i]
        t1, c1 = STOPS[i + 1]
        if t0 <= t <= t1:
            k = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            return (lerp(c0[0], c1[0], k), lerp(c0[1], c1[1], k), lerp(c0[2], c1[2], k))
    return STOPS[-1][1]


def render(target, with_wave):
    SS = max(256, target * 4)  # 超采样
    k = SS / 64.0

    # 斜向渐变底（沿反对角线逐线填充，颜色恒定）
    grad = Image.new('RGB', (SS, SS))
    d = ImageDraw.Draw(grad)
    n = 2 * SS - 1
    for s in range(n):
        t = s / (n - 1)
        col = grad_color(t)
        x0 = max(0, s - SS + 1)
        y0 = min(s, SS - 1)
        x1 = min(s, SS - 1)
        y1 = max(0, s - SS + 1)
        d.line([(x0, y0), (x1, y1)], fill=col)

    # 圆角方章遮罩（对应 SVG：rect x=2 y=2 w=60 h=60 rx=18）
    mask = Image.new('L', (SS, SS), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([2 * k, 2 * k, 62 * k, 62 * k], radius=18 * k, fill=255)

    base = Image.new('RGBA', (SS, SS), (0, 0, 0, 0))
    base.paste(grad, (0, 0), mask)

    # 白色几何「白」覆盖层
    ov = Image.new('RGBA', (SS, SS), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    W = (255, 255, 255, 255)
    sw = 3.2 * k

    def line(p0, p1, width=sw, color=W):
        od.line([p0, p1], fill=color, width=int(round(width)), joint='curve')
        for p in (p0, p1):  # 圆头
            r = width / 2.0
            od.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)

    # 丿
    line((29 * k, 10.5 * k), (22.3 * k, 17 * k))
    # 日（圆角外框）—— 描边以路径为中心线，bbox 外扩 sw/2
    h = sw / 2.0
    od.rounded_rectangle([20.6 * k - h, 16.8 * k - h, 43.4 * k + h, 42.0 * k + h],
                         radius=5.2 * k + h, outline=W, width=int(round(sw)))
    # 日中横
    line((20.6 * k, 29.4 * k), (43.4 * k, 29.4 * k))
    # 瞳
    pr = 3.5 * k
    od.ellipse([32 * k - pr, 35.6 * k - pr, 32 * k + pr, 35.6 * k + pr], fill=W)

    # 泽之水波（小尺寸省略）
    if with_wave:
        ww = 2.0 * k
        cw = (255, 255, 255, 102)
        pts = [(13 * k, 49.6 * k), (18 * k, 47.0 * k), (24 * k, 49.0 * k), (32 * k, 49.6 * k),
               (40 * k, 50.2 * k), (46 * k, 47.2 * k), (51 * k, 49.6 * k)]
        od.line(pts, fill=cw, width=int(round(ww)), joint='curve')
        for p in (pts[0], pts[-1]):
            r = ww / 2.0
            od.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=cw)

    out = Image.alpha_composite(base, ov)
    return out.resize((target, target), Image.LANCZOS)


JOBS = [
    (16, 'favicon-16.png', False),
    (32, 'favicon-32.png', False),
    (48, 'favicon-48.png', False),
    (180, 'apple-touch-icon.png', True),
    (512, 'logo-mark-512.png', True),
]

if __name__ == '__main__':
    frontend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(frontend, 'public')
    os.makedirs(out_dir, exist_ok=True)
    for size, name, wave in JOBS:
        render(size, wave).save(os.path.join(out_dir, name))
        print(f'  ✓ {name:24s} {size}x{size}')
    print('PNG 生成完成 →', out_dir)
