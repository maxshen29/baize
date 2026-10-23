import os
import anyio
from fastapi.staticfiles import StaticFiles

# Replicate the exact path computation used in backend/app/main.py
ROOT = os.environ.get(
    "MODULES_DIR",
    os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules")
    ),
)
print("MODULES_DIR =", ROOT, "| exists =", os.path.isdir(ROOT))

app = StaticFiles(directory=ROOT, html=True)


async def call_get(path: str):
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"",
    }
    status = {}
    body_chunks = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        if msg["type"] == "http.response.start":
            status["code"] = msg["status"]
            status["headers"] = msg.get("headers", [])
        elif msg["type"] == "http.response.body":
            body_chunks.append(msg.get("body", b""))

    await app(scope, receive, send)
    ct = ""
    for k, v in status.get("headers", []):
        if k.lower() == b"content-type":
            ct = v.decode()
    return status.get("code"), ct, b"".join(body_chunks)


async def main():
    checks = [
        "/protein-analysis/index.html",
        "/protein-analysis/_tmp_cdrcheck.js",
        "/protein-analysis/公众号指南/01_开篇.html",
        "/protein-analysis/",
    ]
    for url in checks:
        code, ct, body = await call_get(url)
        print(f"{code}  {ct:<26}  {url}  bytes={len(body)}")
    code, ct, body = await call_get("/protein-analysis/index.html")
    text = body.decode("utf-8", "ignore")
    print("served index is the 3Dmol tool:",
          "3Dmol.org/build/3Dmol-min.js" in text and "files.rcsb.org/download" in text)


anyio.run(main)
