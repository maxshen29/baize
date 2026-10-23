import os

pairs = [
    ("ORIGINAL", "E:/project/Baize/蛋白质界面分析"),
    ("MIGRATED", "E:/project/Baize/Baize/modules/protein-analysis"),
]
rows = []
for label, base in pairs:
    rows.append("===== %s : %s =====" % (label, base))
    if not os.path.exists(base):
        rows.append("  NOT FOUND")
        continue
    entries = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in (".workbuddy", ".git", "node_modules", "__pycache__")]
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, base)
            entries.append((os.path.getsize(full), rel))
    entries.sort()
    for sz, rel in entries:
        rows.append("  %8d  %s" % (sz, rel))
    rows.append("  TOTAL FILES: %d" % len(entries))

with open("E:/project/Baize/Baize/_cmp.log", "w", encoding="utf-8") as fh:
    fh.write("\n".join(rows))
print("DONE")
