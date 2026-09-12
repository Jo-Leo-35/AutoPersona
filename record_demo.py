#!/usr/bin/env python3
"""Record real control-room interactions and export a 36-second MP4.

Run autopersona.py first. All publication in this recorder is LOCAL DEMO ONLY.
Dependencies: pip install -r requirements-video.txt
"""
import argparse
import json
from pathlib import Path
import subprocess
import time
from urllib.parse import urlparse

import imageio_ffmpeg
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description="錄製 36 秒 AutoPersona 操作示範")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--ai", action="store_true", help="Record a real .env API request")
    parser.add_argument("--output", type=Path, default=Path("artifacts/autopersona-demo.mp4"))
    args = parser.parse_args()
    parsed = urlparse(args.url)
    if parsed.hostname not in ("127.0.0.1", "localhost") or parsed.scheme != "http":
        parser.error("Recording is restricted to the local demo dashboard")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw_dir = args.output.parent / ".recordings"
    raw_dir.mkdir(exist_ok=True)
    segments = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=False)
        context = browser.new_context(viewport={"width": 1600, "height": 1000},
                                      record_video_dir=str(raw_dir),
                                      record_video_size={"width": 1600, "height": 1000},
                                      locale="zh-TW", color_scheme="light")
        page = context.new_page()
        recording_start = time.monotonic()
        page.goto(args.url, wait_until="networkidle")
        page.add_style_tag(content="html{scroll-padding-bottom:120px} #record-caption{position:fixed;left:28px;right:28px;bottom:22px;z-index:2147483647;background:#102d2ced;color:white;border:1px solid #ffffff33;border-radius:17px;padding:18px 25px;box-shadow:0 12px 40px #0003;pointer-events:none;font:600 23px/1.5 system-ui} #record-caption small{float:right;font-size:13px;font-weight:400;color:#b8d7d3;padding-top:9px}")

        def caption(text):
            page.evaluate("text => {let el=document.getElementById('record-caption');if(!el){el=document.createElement('div');el.id='record-caption';document.body.append(el)}el.replaceChildren(document.createTextNode(text));let small=document.createElement('small');small.textContent='本機實際操作 · 等待過程已加速';el.append(small)}", text)

        def state():
            response = page.request.get(args.url + "/api/state")
            if not response.ok:
                raise RuntimeError("Cannot read local dashboard state")
            return response.json()

        def idle(timeout=150):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                current = state()
                if not current["busy"]:
                    if current["phase"] == "error":
                        raise RuntimeError(current.get("error", "Workflow error"))
                    return current
                page.wait_for_timeout(250)
            raise TimeoutError("The demo operation did not finish")

        def scene_begin(text):
            caption(text)
            return time.monotonic() - recording_start

        def scene_end(start, seconds):
            segments.append({"start": start, "end": time.monotonic() - recording_start, "seconds": seconds})

        # The panel IDs are part of the demo UI's stable recording interface.
        start = scene_begin("01  一份 Persona 洞察，開始建立商品")
        page.locator("#useAi").set_checked(args.ai)
        page.wait_for_timeout(2600)
        scene_end(start, 4)

        start = scene_begin("02  " + ("GPT-6 Astra 讀取資訊，整理文案與 key-value" if args.ai else "離線模式整理文案與 key-value"))
        page.locator("#prepareBtn").click()
        current = idle()
        if current["phase"] != "prepared":
            raise RuntimeError("Preparation did not complete")
        page.wait_for_timeout(1300)
        scene_end(start, 6)

        start = scene_begin("03  Playwright 開啟可見頁面，自動填入已知資料")
        page.locator("#modeSelect").select_option("demo")
        page.locator("#startBtn").click()
        current = idle()
        if current["mode"] != "demo":
            raise RuntimeError("Recorder refuses to publish outside local demo")
        page.wait_for_timeout(1800)
        scene_end(start, 7)

        start = scene_begin("04  發現缺漏資訊，補充後接續目前步驟")
        for _ in range(5):
            current = state()
            if current["phase"] == "ready":
                break
            if current["phase"] not in ("awaiting_info", "awaiting_browser"):
                raise RuntimeError("Unexpected phase while answering demo questions")
            page.locator("#demoFillBtn").click()
            page.wait_for_timeout(800)
            page.locator("#answersSubmit").click()
            current = idle()
        if current["phase"] != "ready":
            raise RuntimeError("Demo did not reach review after answering questions")
        page.wait_for_timeout(1300)
        scene_end(start, 9)

        start = scene_begin("05  預覽商品內容，確認後完成本機示範發布")
        page.locator("#publishInput").fill(current["listing"]["product"]["title"])
        page.wait_for_timeout(900)
        page.locator("#publishBtn").click()
        current = idle()
        if current["phase"] != "published" or current["mode"] != "demo":
            raise RuntimeError("The visible demo page did not confirm publication")
        page.wait_for_timeout(1300)
        scene_end(start, 6)

        start = scene_begin("AutoPersona  從客群洞察到商品表單，每一步都看得見")
        page.evaluate("window.scrollTo({top:0,behavior:'smooth'})")
        page.wait_for_timeout(2800)
        page.screenshot(path=str(args.output.with_suffix(".png")))
        scene_end(start, 4)
        video_path = Path(page.video.path())
        context.close()
        browser.close()

    filters = []
    for index, segment in enumerate(segments):
        duration = max(segment["end"] - segment["start"], 0.1)
        filters.append("[0:v]trim=start=%.3f:end=%.3f,setpts=%.8f*(PTS-STARTPTS),fps=30,setsar=1[v%d]" %
                       (segment["start"], segment["end"], segment["seconds"] / duration, index))
    filters.append("".join("[v%d]" % i for i in range(len(segments))) +
                   "concat=n=%d:v=1:a=0,scale=1600:1000:flags=lanczos,format=yuv420p[out]" % len(segments))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video_path),
                    "-filter_complex", ";".join(filters), "-map", "[out]", "-c:v", "libx264",
                    "-preset", "medium", "-crf", "19", "-movflags", "+faststart", str(args.output)], check=True)
    frames, seconds = imageio_ffmpeg.count_frames_and_secs(str(args.output))
    if not 30 <= seconds <= 40:
        raise RuntimeError("Recording duration is outside the requested 30–40 seconds")
    manifest = {"duration_seconds": seconds, "frames": frames, "provider": current["provider"],
                "mode": "demo", "publication": "local_simulation_only", "audio": "none",
                "segments": segments, "run_id": current["run_id"], "video": str(args.output)}
    args.output.with_suffix(".json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
