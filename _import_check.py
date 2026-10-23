import sys
sys.path.insert(0, "E:/project/Baize/Baize/backend")
import os
os.environ.setdefault("MODULES_DIR", "E:/project/Baize/Baize/modules")
from app.main import app  # must import without DB
paths = sorted({getattr(r, "path", "") for r in app.routes})
print("has /modules static mount:", any(p == "/modules" for p in paths))
print("has /health:", "/health" in paths)
print("has /api/v1/auth/login:", "/api/v1/auth/login" in paths)
print("IMPORT_OK")
