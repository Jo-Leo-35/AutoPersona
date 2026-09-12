#!/usr/bin/env python3
"""Run a visible Shopee listing/update from JSON, retaining one browser for follow-ups.

Use --product-id to update an existing item. --publish explicitly authorizes one
submission for this run. Without it the script fills the form and stops to review.
Login/CAPTCHA stays manual in the visible, dedicated browser profile.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
import uuid

from autopersona_py.planner import prepare_listing, PlannerError
from autopersona_py.schema import apply_answers

ROOT = Path(__file__).resolve().parent


def json_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('JSON 根節點必須是物件。')
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def product_id(value: str) -> str:
    if not re.fullmatch(r'[1-9][0-9]{0,19}', value):
        raise argparse.ArgumentTypeError('商品 ID 必須是正整數字串。')
    return value


def event(kind: str, message: str) -> None:
    print(f'[{kind}] {message}', flush=True)


def summarize(report: dict) -> None:
    print('狀態：' + report.get('phase', 'unknown'), flush=True)
    if report.get('message'):
        print(report['message'], flush=True)
    for question in report.get('questions', []):
        print(f"  {question['path']}: {question.get('label', '')} — {question.get('reason', '')}", flush=True)


def read_signal(control_dir: Path) -> dict | None:
    signal = control_dir / 'resume.json'
    if not signal.exists():
        return None
    command = json_object(signal)
    if command.get('action', 'resume') not in ('resume', 'stop'):
        raise ValueError('resume.json action 只接受 resume 或 stop。')
    if not isinstance(command.get('answers', {}), dict):
        raise ValueError('resume.json answers 必須是物件。')
    signal.unlink()
    return command


def next_command(args, control_dir: Path) -> dict | None:
    if args.wait_for_resume:
        print(f'保留目前商品頁。補答或登入完成後，寫入 {control_dir / "resume.json"}', flush=True)
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            command = read_signal(control_dir)
            if command is not None:
                return command
            time.sleep(0.5)
        print('等待逾時，已保存本轮資料；沒有重複送出。', flush=True)
        return None
    if not sys.stdin.isatty():
        return None
    text = input('Enter 繼續；answers <JSON路徑> 補答；stop 結束：').strip()
    if text == 'stop':
        return {'action': 'stop'}
    if text.startswith('answers '):
        answers = json_object(Path(text[8:]).expanduser())
        return {'action': 'resume', 'answers': answers.get('answers', answers)}
    if text:
        raise ValueError('請按 Enter，或使用 answers <JSON路徑> / stop。')
    return {'action': 'resume'}


def run(args, browser_factory=None) -> int:
    started = time.monotonic()
    if browser_factory is None:
        from autopersona_py.browser import BrowserSession
        browser_factory = BrowserSession
    prepared = prepare_listing(json_object(args.input), ROOT, use_ai=args.ai)
    listing = prepared['listing']
    if args.answers:
        answers = json_object(args.answers)
        listing = apply_answers(listing, answers.get('answers', answers))
    run_id = datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:6]
    folder = args.run_dir or ROOT / '.autopersona' / 'runs' / ('script-' + run_id)
    folder = folder.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    # A stale signal from a previous process must never resume this run.
    if (folder / 'resume.json').exists() or (folder / 'report.json').exists():
        raise ValueError('執行目錄已有前一輪資料；請先核對結果並使用新的目錄。')
    write_json(folder / 'listing.json', listing)
    print('Run：' + run_id, flush=True)
    print('資料：' + str(folder), flush=True)
    print('商品：' + str(listing['product']['title']), flush=True)
    print('目標：' + ('更新商品 ' + args.product_id if args.product_id else '新增商品'), flush=True)
    print('文案來源：' + ('OpenAI API' if args.ai else '輸入 JSON／離線整理'), flush=True)
    if args.prepare_only:
        write_json(folder / 'report.json', {'phase': 'prepared', 'run_id': run_id,
                   'targetProductId': args.product_id, 'provider': prepared['provider'],
                   'elapsedSeconds': round(time.monotonic() - started, 3)})
        return 0
    browser = browser_factory(ROOT, emit=event, headless=False, slow_mo=args.slow_mo,
                              profile_dir=args.profile_dir, record_video_dir=args.record_video_dir,
                              fullscreen=args.fullscreen)
    attempted = False
    report = {}
    try:
        report = browser.start(listing, 'shopee', '', product_id=args.product_id)
        while True:
            # Submission is bound to the current data and only attempted once.
            if report.get('phase') == 'ready' and args.publish and not attempted:
                attempted = True
                report = browser.publish(listing, listing['product']['title'])
            snapshot = dict(report, run_id=run_id, targetProductId=args.product_id,
                            operation=report.get('browser', {}).get('operation', 'update' if args.product_id else 'create'),
                            updated_at=datetime.now(timezone.utc).isoformat(),
                            elapsedSeconds=round(time.monotonic() - started, 3),
                            submission_authorized=args.publish,
                            source_kind='real_shopee_visible_playwright')
            write_json(folder / 'report.json', snapshot)
            write_json(folder / 'listing.json', listing)
            summarize(report)
            if report.get('phase') == 'published':
                if args.hold_open:
                    browser.page.wait_for_timeout(args.hold_open * 1000)
                return 0
            if report.get('phase') == 'ready' and not args.publish:
                print('填表已完成。未指定 --publish，本輪不會送出。', flush=True)
                if args.hold_open:
                    browser.page.wait_for_timeout(args.hold_open * 1000)
                return 0
            command = next_command(args, folder)
            if command is None or command.get('action') == 'stop':
                return 2
            answers = command.get('answers', {})
            if attempted or report.get('publishAttempted'):
                if answers:
                    print('本輪已送出；先核對保存結果，未套用新答案。', flush=True)
                report = browser.inspect()
            else:
                if answers:
                    listing = apply_answers(listing, answers)
                report = browser.fill(listing)
    finally:
        browser.close()
        video = browser.video_path()
        if video:
            write_json(folder / 'recording.json', {'source_kind': 'real_shopee_playwright', 'raw_video': video,
                       'publication_verified': bool(report.get('browser', {}).get('completionVerified'))})


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--input', required=True, type=Path, help='Listing JSON or a listing wrapper')
    result.add_argument('--product-id', type=product_id, help='Update this existing product; omit only to create a new item')
    result.add_argument('--answers', type=Path, help='Initial dotted-field answers JSON')
    result.add_argument('--ai', action='store_true', help='Explicitly call the configured OpenAI API for copy')
    result.add_argument('--publish', action='store_true', help='Authorize one create/update submission after page validation')
    result.add_argument('--prepare-only', action='store_true', help='Validate/normalize JSON without starting Chrome')
    result.add_argument('--profile-dir', type=Path, default=ROOT / '.autopersona/browser-profile/shopee', help='Dedicated automation profile; never use everyday Chrome profile')
    result.add_argument('--run-dir', type=Path, help='Private run folder with listing/report/resume.json')
    result.add_argument('--wait-for-resume', action='store_true', help='Wait for resume.json after login or missing information')
    result.add_argument('--timeout', type=int, default=900, help='Seconds to wait for each resume signal')
    result.add_argument('--slow-mo', type=int, default=0, help='Optional pacing per browser action in ms; default 0 for fast runs, e.g. 150 for recording')
    result.add_argument('--fullscreen', action='store_true', help='Open the visible automation Chrome in fullscreen with the native window viewport')
    result.add_argument('--hold-open', type=int, default=0, help='Seconds to retain the completed browser for review/recording')
    result.add_argument('--record-video-dir', type=Path, help='Optional private Playwright raw video directory')
    return result


def main():
    argument_parser = parser()
    args = argument_parser.parse_args()
    if not 1 <= args.timeout <= 3600 or not 0 <= args.hold_open <= 600 or not 0 <= args.slow_mo <= 5000:
        argument_parser.error('timeout: 1–3600；hold-open: 0–600；slow-mo: 0–5000。')
    try:
        return run(args)
    except (KeyboardInterrupt, EOFError):
        print('已停止；請先核對本輪 report 與蝦皮商品，避免重複建立。', file=sys.stderr)
        return 130
    except PlannerError as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:
        # Provider/browser exceptions may embed credentials or page contents.
        print('腳本未完成（' + type(error).__name__ + '）；請核對輸入格式及本輪 report。', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
