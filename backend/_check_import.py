import sys
sys.path.insert(0, "E:/project/Baize/Baize/backend")
from app.main import app
from app.routers import auth
paths = [getattr(r, "path", None) for r in app.routes]
print("login route present:", any(p == "/api/v1/auth/login" for p in paths if p))
print("auth import OK")
print("IMPORT_OK")
