#!/usr/bin/env python3
"""Read-only demo progress, with local answer capture. Python standard library only."""
import argparse
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(__file__).with_name("index.html")
LOCK = threading.Lock()
STAGES = ("persona", "copy", "browser", "questions", "verify")


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path, default):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    if not isinstance(value, dict):
        raise ValueError("資料格式需要 JSON object")
    return value


def pick(source, keys):
    if not isinstance(source, dict):
        return {}
    return {key: source[key] for key in keys if key in source}


def public_session(raw):
    """Expose only the documented presentation fields, never arbitrary JSON or files."""
    session = pick(raw, ("version", "run_id", "title", "updated_at", "status", "summary", "current_stage"))
    session.setdefault("run_id", "")
    session.setdefault("status", "waiting")
    session["stages"] = [pick(stage, ("id", "status", "detail")) for stage in raw.get("stages", [])
                         if isinstance(stage, dict) and stage.get("id") in STAGES]
    for name, keys in {
        "persona": ("title", "summary", "evidence", "label"),
        "product": ("title", "summary", "facts", "source", "reference_note"),
        "copy": ("title", "body"),
        "execution": ("summary", "items"),
        "browser": ("title", "url", "summary"),
        "verification": ("summary", "items"),
    }.items():
        session[name] = pick(raw.get(name), keys)
    session["questions"] = [pick(question, ("id", "label", "help", "type", "options", "required"))
                            for question in raw.get("questions", [])
                            if isinstance(question, dict) and isinstance(question.get("id"), str)]
    session["events"] = [pick(event, ("at", "message")) for event in raw.get("events", [])
                         if isinstance(event, dict)][-20:]
    return session


def answers_for(data_dir, run_id):
    result = read_json(data_dir / "answers.json", {})
    if not run_id or result.get("run_id") != run_id:
        return {"version": 1, "run_id": run_id, "updated_at": None, "answers": {}}
    return pick(result, ("version", "run_id", "updated_at", "answers"))


def atomic_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".answers-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass  # Avoid recording question contents, answers, or URL query strings.

    def send(self, status, value, content_type="application/json; charset=utf-8"):
        body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        return self.headers.get("Host") in {
            "127.0.0.1:" + str(self.server.server_port),
            "localhost:" + str(self.server.server_port),
        }

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, {"error": "僅供本機存取"})
        route = self.path.split("?", 1)[0]
        if route in ("/", "/index.html"):
            return self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if route == "/health":
            return self.send(200, {"ok": True, "mode": "local-progress"})
        if route == "/api/state":
            try:
                session = public_session(read_json(self.server.data_dir / "session.json", {}))
                return self.send(200, {"session": session, "answers": answers_for(self.server.data_dir, session["run_id"])})
            except (ValueError, TypeError, OSError):
                return self.send(503, {"error": "展示資料暫時無法讀取，將自動重試。"})
        return self.send(404, {"error": "找不到頁面"})

    def do_POST(self):
        origin = self.headers.get("Origin")
        expected = "http://" + self.headers.get("Host", "")
        if not self.valid_host() or (origin and origin != expected):
            return self.send(403, {"error": "請從本機進度頁提交"})
        if self.path != "/api/answers":
            return self.send(404, {"error": "找不到頁面"})
        if self.headers.get_content_type() != "application/json":
            return self.send(415, {"error": "需要 JSON 資料"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 131072:
                return self.send(413, {"error": "補答內容過大或空白"})
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict) or not isinstance(payload.get("answers"), dict):
                raise ValueError("補答格式不正確")
            with LOCK:
                session = public_session(read_json(self.server.data_dir / "session.json", {}))
                if not session["run_id"] or payload.get("run_id") != session["run_id"]:
                    return self.send(409, {"error": "展示輪次已更新，請重新整理後補答"})
                questions = {q["id"]: q for q in session["questions"]}
                values = payload["answers"]
                if not values or any(key not in questions for key in values):
                    raise ValueError("問題清單已更新，請重新整理後補答")
                for key, value in values.items():
                    if not isinstance(value, str) or len(value) > 12000:
                        raise ValueError("每則補答需為文字且不超過 12000 字")
                    question = questions[key]
                    if question.get("type") == "select" and value and value not in question.get("options", []):
                        raise ValueError("請選擇問題提供的選項")
                saved = answers_for(self.server.data_dir, session["run_id"])
                saved.update(version=1, updated_at=now())
                saved.setdefault("answers", {})
                for key, value in values.items():
                    saved["answers"][key] = {"value": value.strip(), "updated_at": saved["updated_at"]}
                atomic_write(self.server.data_dir / "answers.json", saved)
            return self.send(200, {"ok": True, "answers": saved})
        except (ValueError, UnicodeError) as error:
            return self.send(400, {"error": str(error) if not isinstance(error, json.JSONDecodeError) else "JSON 資料格式不正確"})
        except (TypeError, OSError):
            return self.send(503, {"error": "補答暫時無法儲存，請保留內容後重試"})


def main():
    parser = argparse.ArgumentParser(description="AutoPersona 真實 Chrome 展示進度頁（不控制瀏覽器）")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "work" / "browser-demo")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.data_dir = args.data_dir.resolve()
    print(f"AutoPersona 展示進度頁：http://127.0.0.1:{server.server_port}", flush=True)
    print("讀取 session.json；僅將補答寫入 answers.json。Ctrl+C 結束。", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
