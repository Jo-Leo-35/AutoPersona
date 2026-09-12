"""Local control room; a single worker owns all synchronous Playwright objects."""
from __future__ import annotations

import argparse
import copy
import json
import mimetypes
import queue
import re
import sys
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
WEB = Path(__file__).resolve().parent / "web"


class Workflow:
    def __init__(self, root=ROOT, *, headless=False, profile_dir=None, mode="shopee"):
        from .planner import config_status
        self.root = Path(root)
        self.headless = headless
        self.profile_dir = Path(profile_dir).resolve() if profile_dir else None
        self.base_url = ""
        self.lock = threading.RLock()
        self.tasks = queue.Queue()
        self.stop_event = threading.Event()
        self.browser = None
        self.latest_image = b""
        self.last_capture = 0.0
        config = config_status(self.root)
        config["api_configured"] = config.get("configured", False)
        self.state = {
            "phase": "idle", "mode": mode, "provider": {"mode": "offline"},
            "listing": None, "questions": [], "warnings": [], "events": [],
            "browser": {}, "run_id": None, "busy": False, "config": config,
            "filled": [], "error": None,
        }
        self.worker = threading.Thread(target=self._work, name="visible-browser", daemon=True)
        self.worker.start()

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.state)

    def event(self, message, level="info"):
        with self.lock:
            self.state["events"].append({"time": datetime.now().strftime("%H:%M:%S"),
                                         "message": str(message), "level": level})
            self.state["events"] = self.state["events"][-180:]

    def submit(self, action, payload):
        from .schema import apply_answers
        with self.lock:
            if self.state["busy"]:
                raise ValueError("目前的步驟仍在進行，請等進度更新後再操作。")
            if action == "prepare":
                if not isinstance(payload.get("input"), dict):
                    raise ValueError("請提供 JSON 物件。")
                if not isinstance(payload.get("use_ai", False), bool):
                    raise ValueError("use_ai 必須是布林值。")
            elif action == "start":
                if not self.state["listing"]:
                    raise ValueError("請先整理商品資料。")
                if payload.get("mode", "shopee") not in ("demo", "shopee"):
                    raise ValueError("不支援的模式。")
            elif action in ("answers", "resume", "publish", "focus"):
                if not self.state["listing"]:
                    raise ValueError("請先整理商品資料。")
                if action != "answers" and not self.browser:
                    raise ValueError("請先開啟操作瀏覽器。")
                if action == "answers":
                    if self.state.get("publishAttempted"):
                        raise ValueError("本次發布已送出，請先核對結果；建立新草稿才能修改商品資料。")
                    answers = payload.get("answers")
                    if not isinstance(answers, dict):
                        raise ValueError("補充資料必須是 key-value 物件。")
                    apply_answers(self.state["listing"], answers)
                if action == "publish":
                    if self.state["phase"] != "ready":
                        raise ValueError("請完成待補資料並檢查表單後，再確認發布。")
                    title = self.state["listing"].get("product", {}).get("title")
                    if not title or payload.get("confirmation") != title:
                        raise ValueError("請輸入完整商品名稱，確認這一次發布。")
            else:
                raise ValueError("未知操作。")
            self.state["busy"] = True
            self.state["error"] = None
            self.tasks.put((action, copy.deepcopy(payload)))
        return self.snapshot()

    def _capture(self):
        if self.browser:
            try:
                data = self.browser.screenshot()
                with self.lock:
                    self.latest_image = data
                    self.last_capture = time.monotonic()
                    self.state["browser"]["screenshotCapturedAt"] = time.time()
                    page = getattr(self.browser, "page", None)
                    if page and not page.is_closed():
                        parsed = urlparse(page.url)
                        self.state["browser"]["url"] = parsed._replace(query="", fragment="").geturl()
                        self.state["browser"]["title"] = page.title()[:160]
            except Exception:
                pass  # A closed window is explained by the next explicit browser operation.

    def browser_event(self, kind, message):
        self.event(message, "info")
        if time.monotonic() - self.last_capture > 0.7:
            self._capture()

    def _save(self):
        state = self.snapshot()
        if not state["run_id"] or not state["listing"]:
            return
        folder = self.root / ".autopersona" / "runs" / state["run_id"]
        folder.mkdir(parents=True, exist_ok=True)
        for name, data in (("listing.json", state["listing"]), ("report.json", state)):
            target = folder / name
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(target)

    def _schema_questions(self, listing):
        from .schema import collect_questions
        questions = collect_questions(listing, self.root)
        if self.state["mode"] == "shopee" and listing.get("media", {}).get("confirmedProductImages") is not True and listing.get("media", {}).get("uploadAuthorized") is not True:
            questions = [q for q in questions if q["path"] != "media.confirmedProductImages"]
            questions.append({"path": "media.confirmedProductImages", "label": "確認圖片是這次販售的實際商品",
                              "type": "boolean", "required": True,
                              "reason": "目前圖片標記為示範參考素材；確認或替換後才會傳到蝦皮。"})
        return questions

    def _accept_browser(self, result):
        result = result or {}
        with self.lock:
            merged = {q["path"]: q for q in self._schema_questions(self.state["listing"])}
            for question in result.get("questions", []):
                merged[question["path"]] = question
            phase = result.get("phase", "awaiting_browser")
            if phase == "ready" and any(q.get("required", True) for q in merged.values()):
                phase = "awaiting_info"
            self.state.update({"phase": phase, "questions": list(merged.values()),
                               "browser": result.get("browser", self.state["browser"]),
                               "filled": result.get("filled", self.state["filled"])})
            if result.get("publishAttempted"):
                self.state["publishAttempted"] = True
            if result.get("message"):
                self.event(result["message"])

    def _execute(self, action, payload):
        from .planner import prepare_listing
        from .schema import apply_answers
        if action == "prepare":
            if self.browser:
                self.browser.close()
                self.browser = None
            with self.lock:
                self.latest_image = b""
                self.state.update(phase="preparing", browser={}, events=[], questions=[], filled=[],
                                  listing=None, warnings=[], provider={"mode": "openai" if payload.get("use_ai") else "offline"},
                                  run_id=datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6],
                                  publishAttempted=False)
            self.event("整理 Persona 資訊與商品事實…")
            prepared = prepare_listing(payload["input"], self.root, use_ai=payload.get("use_ai", False))
            with self.lock:
                self.state.update({k: prepared[k] for k in ("listing", "questions", "warnings", "provider")})
                self.state["phase"] = "prepared"
            self.event("文案與 key-value 已備妥。可以先開啟表單，逐步補充缺少的資料。")
        elif action == "start":
            from .browser import BrowserSession
            if self.browser:
                self.browser.close()
            with self.lock:
                self.state.update(mode=payload.get("mode", "shopee"), phase="starting")
            self.browser = BrowserSession(self.root, emit=self.browser_event, headless=self.headless,
                                          profile_dir=self.profile_dir)
            self.event("開啟可見瀏覽器：" + ("本機模擬賣場" if self.state["mode"] == "demo" else "蝦皮賣家中心"))
            self._accept_browser(self.browser.start(self.state["listing"], self.state["mode"], self.base_url))
        elif action == "answers":
            with self.lock:
                self.state["listing"] = apply_answers(self.state["listing"], payload["answers"])
            self.event("已收到補充資料。" + ("繼續填寫目前頁面…" if self.browser else "可開啟表單。"))
            if self.browser:
                with self.lock:
                    self.state["phase"] = "filling"
                self._accept_browser(self.browser.fill(self.state["listing"]))
            else:
                with self.lock:
                    self.state.update(questions=self._schema_questions(self.state["listing"]), phase="prepared")
        elif action == "resume":
            self.event("重新查看目前頁面，繼續可完成的步驟…")
            with self.lock:
                self.state["phase"] = "filling"
            self._accept_browser(self.browser.fill(self.state["listing"]))
        elif action == "publish":
            with self.lock:
                self.state["phase"] = "publishing"
            self.event("已確認本次發布，正在檢查結果…")
            self._accept_browser(self.browser.publish(self.state["listing"], payload["confirmation"]))
            if self.state["phase"] == "published":
                self.event("本機示範發布完成，沒有建立真實賣場商品。" if self.state["mode"] == "demo"
                           else "蝦皮頁面已顯示發布完成，請查看商品結果。", "success")
        elif action == "focus":
            if hasattr(self.browser, "focus"):
                self.browser.focus()
            elif getattr(self.browser, "page", None):
                self.browser.page.bring_to_front()

    def _work(self):
        while not self.stop_event.is_set():
            try:
                action, payload = self.tasks.get(timeout=1.2)
            except queue.Empty:
                self._capture()
                continue
            try:
                self._execute(action, payload)
            except Exception as exc:
                from .planner import PlannerError
                # SDK exceptions can include request bodies. Only our own validation errors are public.
                safe = str(exc) if isinstance(exc, (ValueError, PlannerError)) else "操作未完成（%s）。請檢查瀏覽器，再按重新查看頁面。" % type(exc).__name__
                safe = re.sub(r"sk-[A-Za-z0-9_\-]+", "[redacted]", safe)
                with self.lock:
                    self.state.update(phase="error", error=safe)
                self.event(safe, "error")
            finally:
                self._capture()
                with self.lock:
                    self.state["busy"] = False
                try:
                    self._save()
                except OSError:
                    self.event("目前狀態無法寫入磁碟，瀏覽器仍保留；可從面板匯出 JSON。", "error")
                finally:
                    self.tasks.task_done()
        if self.browser:
            self.browser.close()

    def close(self):
        self.stop_event.set()
        self.worker.join(timeout=5)


def make_handler(flow):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AutoPersona/0.2"

        def log_message(self, *_args):
            pass

        def respond(self, data, status=200, content_type="application/json; charset=utf-8"):
            body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def local_request(self):
            expected = urlparse(flow.base_url).netloc
            if self.headers.get("Host") != expected:
                self.respond({"error": "Invalid local host"}, 403)
                return False
            origin = self.headers.get("Origin")
            if origin and origin != flow.base_url:
                self.respond({"error": "Only the local control room can perform this action"}, 403)
                return False
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                self.respond({"error": "Cross-site access denied"}, 403)
                return False
            return True

        def do_GET(self):
            if not self.local_request():
                return
            route = unquote(urlparse(self.path).path)
            if route == "/api/state":
                self.respond(flow.snapshot())
            elif route == "/api/example":
                self.respond(json.loads((flow.root / "examples/open-ear-headphones.json").read_text(encoding="utf-8")))
            elif route == "/api/screenshot":
                with flow.lock:
                    data = flow.latest_image
                self.respond(data, 200 if data else 204, "image/png")
            elif route in ("/api/listing", "/api/report"):
                self.respond(flow.snapshot()["listing"] if route.endswith("listing") else flow.snapshot())
            elif route.startswith("/media/"):
                target = (flow.root / route[len("/media/"):]).resolve()
                state = flow.snapshot()
                image_paths = (state.get("listing") or {}).get("media", {}).get("imagePaths", [])
                allowed = {(flow.root / p).resolve() for p in ["demo-0.png", "demo-1.png"] + image_paths if isinstance(p, str)}
                if target not in allowed or flow.root not in target.parents or target.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp") or not target.is_file():
                    self.respond({"error": "Image not available"}, 404)
                else:
                    self.respond(target.read_bytes(), content_type=mimetypes.guess_type(str(target))[0] or "image/png")
            else:
                name = "index.html" if route == "/" else "demo-seller.html" if route in ("/demo/seller", "/demo/seller/") else route.lstrip("/")
                target = (WEB / name).resolve()
                if WEB.resolve() not in target.parents or not target.is_file() or target.suffix not in (".html", ".css", ".js", ".svg"):
                    self.respond({"error": "Not found"}, 404)
                else:
                    mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                    self.respond(target.read_bytes(), content_type=mime + "; charset=utf-8")

        def do_POST(self):
            if not self.local_request():
                return
            try:
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ValueError("Requests must use application/json")
                size = int(self.headers.get("Content-Length", "0"))
                if size <= 0 or size > 250_000:
                    raise ValueError("Request size must be between 1 and 250000 bytes")
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError("JSON object required")
                route = urlparse(self.path).path
                action = route.removeprefix("/api/")
                if route != "/api/" + action:
                    raise ValueError("Unknown route")
                self.respond(flow.submit(action, payload), 202)
            except (ValueError, UnicodeError) as exc:
                self.respond({"error": str(exc)}, 400)

    return Handler


def open_dashboard(url, stop_event, emit):
    """A separate Playwright thread keeps the control panel visibly open."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(channel="chrome", headless=False)
            except Exception:
                browser = playwright.chromium.launch(headless=False)
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                while not stop_event.is_set() and not page.is_closed():
                    page.wait_for_timeout(500)
            finally:
                browser.close()
    except Exception as exc:
        emit("控制面板視窗已關閉或無法開啟（%s）；可手動開啟 %s。" % (type(exc).__name__, url))


def main(argv=None):
    parser = argparse.ArgumentParser(description="AutoPersona Python Beta — 可見瀏覽器與分步補資料")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--input", type=Path, default=ROOT / "examples/open-ear-headphones.json")
    parser.add_argument("--mode", choices=("demo", "shopee"), default="shopee")
    provider = parser.add_mutually_exclusive_group()
    provider.add_argument("--ai", action="store_true", help="Use .env API settings to prepare copy")
    provider.add_argument("--offline", action="store_true", help="Use local deterministic copy (default)")
    parser.add_argument("--autostart", action="store_true", help="Prepare input and open the visible seller browser")
    parser.add_argument("--open-dashboard", action="store_true", help="Open the control panel in visible Chrome with Playwright")
    parser.add_argument("--profile-dir", type=Path, help="Dedicated seller browser profile directory (never use your everyday Chrome profile)")
    parser.add_argument("--prepare-only", action="store_true", help="Write the structured listing and questions as JSON, then exit")
    parser.add_argument("--output", type=Path, help="JSON destination for --prepare-only (otherwise stdout)")
    parser.add_argument("--headless", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("port must be 0..65535")
    if args.output and not args.prepare_only:
        parser.error("--output requires --prepare-only")
    if args.prepare_only and (args.autostart or args.open_dashboard):
        parser.error("--prepare-only cannot open browser windows")
    load_input = args.prepare_only or args.autostart or args.ai or args.input != ROOT / "examples/open-ear-headphones.json"
    raw = None
    if load_input:
        try:
            raw = json.loads(args.input.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("輸入檔必須是 JSON 物件。")
        except (OSError, ValueError, UnicodeError) as exc:
            parser.error("無法載入輸入 JSON（%s）。請檢查 --input 檔案與格式。" % type(exc).__name__)
    if args.prepare_only:
        from .planner import PlannerError, prepare_listing
        try:
            prepared = prepare_listing(raw, ROOT, use_ai=args.ai)
            body = json.dumps(prepared, ensure_ascii=False, indent=2) + "\n"
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(body, encoding="utf-8")
                print("JSON 已儲存：" + str(args.output.resolve()), file=sys.stderr)
            else:
                print(body, end="")
            return 0
        except (PlannerError, ValueError) as exc:
            parser.error(str(exc))
    flow = Workflow(headless=args.headless, profile_dir=args.profile_dir, mode=args.mode)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(flow))
    except OSError:
        flow.close()
        parser.error("無法使用此連接埠，請改用 --port 8766 或其他未使用的埠。")
    flow.base_url = "http://127.0.0.1:%d" % server.server_port
    print("AutoPersona Python Beta\n控制面板：%s\n請在 Chrome 開啟此網址；Ctrl+C 停止。" % flow.base_url, flush=True)
    if load_input:
        def bootstrap():
            flow.submit("prepare", {"input": raw, "use_ai": args.ai})
            flow.tasks.join()
            if args.autostart and flow.snapshot()["phase"] == "prepared":
                flow.submit("start", {"mode": args.mode})
        threading.Thread(target=bootstrap, daemon=True).start()
    dashboard_thread = None
    if args.open_dashboard:
        dashboard_thread = threading.Thread(target=open_dashboard,
                                            args=(flow.base_url, flow.stop_event, flow.event),
                                            daemon=True, name="control-panel")
        dashboard_thread.start()
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        print("\n正在結束示範…", flush=True)
    finally:
        flow.close()
        server.server_close()
        if dashboard_thread:
            dashboard_thread.join(timeout=3)


if __name__ == "__main__":
    main()
