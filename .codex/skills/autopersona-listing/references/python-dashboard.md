# Python Beta 控制台

只有需要 Python 控制台與對話補答 API 時才讀取。此入口與 `demo-control/server.py` 的 API 不同；快速腳本請用 [python-run.md](python-run.md)。以下程式與文件路徑相對於 AutoPersona 專案根目錄。

## Locate and prepare

Find the project containing `autopersona.py` and `autopersona_py/`. Resolve the project from the skill's real path or the user's supplied project location. Read `docs/PYTHON_BETA.md` for installation and the JSON contract only when needed.

Write the user's supplied facts and Persona text into `.autopersona/inputs/<name>.json` inside the project. Accept a full nested JSON object, a `listing` wrapper, or `{"personaBrief": "<user text>"}`. Use `examples/open-ear-headphones.json` to understand field names; do not copy its product or image paths into an unrelated listing. Relative image paths resolve from the project root. Copy explicitly supplied product images into a product folder when they are outside the project.

Read credentials through the application, which accepts `OPENAI_API_KEY` or `GPT-API` from the project's `.env` and lets environment variables override it. Do not include `.env` contents in prompts, input JSON, logs, screenshots, or reports. `OPENAI_MODEL` controls the runtime API model; Codex's own model setting is separate.

Unknown SKU, price, stock, condition, specifications, certifications, and shipping facts stay `null`. Research such as “13 verified-purchase matches” describes an audience insight, not reviews of this listing. Avoid turning it into product claims. Reuse supplied facts and existing answers before asking anything.

## Run the visible workflow

From the project root:

```sh
.venv/bin/python autopersona.py --ai --mode shopee --input .autopersona/inputs/<name>.json --autostart --open-dashboard
```

Keep the server process running. It prints the local dashboard URL. If a session is already running, inspect `GET /api/state` first and continue the relevant session. Use a free `--port` and separate `--profile-dir` for an independent run rather than overwriting another draft. Do not use the everyday Chrome profile.

For JSON-only handoff, use `--prepare-only --output .autopersona/prepared.json`. For an explicitly chosen offline rehearsal, use `--offline --mode demo`; say that it uses a local mock seller page. A model failure is reported as an error and must not be silently called a successful AI run.

The control panel shows the current seller URL, recurring screenshots, generated key-value data, page questions, and events. Login or a page control needing manual operation is displayed as `awaiting_browser`. The user can complete it in the visible Chrome window and resume.

## Continue from conversation

Use the local HTTP API with JSON bodies. POST requests are asynchronous: `202` means queued, not completed. Poll `GET /api/state` until `busy` is false, using bounded waits. Keep the user informed while work runs.

| Request | Meaning |
| --- | --- |
| `GET /api/state` | Current phase, questions, listing, browser URL, and events |
| `POST /api/prepare` with `{"input": {...}, "use_ai": true}` | Create a new draft; replaces the current draft and closes its browser |
| `POST /api/start` with `{"mode": "shopee"}` | Open and fill the visible seller page |
| `POST /api/answers` with `{"answers": {"sales.price": 1990, "sales.stock": 5}}` | Apply the user's supplied answers and continue on the same page |
| `POST /api/resume` with `{}` | Inspect the page again after manual interaction |
| `POST /api/focus` with `{}` | Bring the seller page forward |
| `GET /api/listing` / `GET /api/report` | Export the draft or current run report |

Ask only the unresolved information necessary for the next step. Preserve numeric and boolean types, including zero stock and `false`. Questions with a `page.*` path or `manual` type require the user to operate that control in the visible browser; they are not schema keys to submit as answers.

## Review and completion

When the phase is `ready`, present the actual title, price, stock, images, and destination for review. Use the user's existing authorization when it covers this concrete listing; otherwise request the missing publication decision after the draft is reviewable. The application accepts `POST /api/publish` with `{"confirmation": "<exact current product title>"}`; the title binds the action to the current draft.

Do not report success from a click, an HTTP 202 response, or a product-list redirect alone. Require the workflow's `published` result with verified page evidence, and state whether it was the local demo or real Shopee. After an attempted submission with ambiguous result, inspect or resume that run instead of starting a duplicate listing.

Return a short result with completed actions, actual published URL/evidence when available, and any remaining missing information. Local reports live in `.autopersona/runs/<run_id>/`; these files and browser profiles are private runtime data, not source deliverables.
