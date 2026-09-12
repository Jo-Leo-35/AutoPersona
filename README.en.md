# AutoPersona

[繁體中文](README.md) | English

AutoPersona turns Persona research into a product listing draft, fills the fields required by Shopee Taiwan Seller Centre, and verifies the saved result. Product facts, marketing copy, and internal research remain separate. Unknown brands, models, prices, specifications, and certification numbers stay unknown until supported by product information.

## Current status

The primary demo uses **Codex to operate a visible, real Chrome window**. A local control room shows the flow from Persona insight to product copy, browser interaction, missing information, and verification.

The JLab JBuds OPEN SPORT demo was verified on September 12, 2026: Codex updated the existing Shopee product, reopened its detail page, and confirmed the open-ear attribute, full description, certification information, price of NT$3,990, stock of 1, and two existing images. The live-product list and public product page were also checked. No buyer checkout or order was attempted. See the [demo guide](docs/OPEN_SPORT_DEMO.md), [Persona integration notes](docs/OPEN_SPORT_PERSONA.md), and [browser verification record](docs/OPEN_SPORT_BROWSER_RUN.md).

The **Python/Playwright route has not passed an end-to-end run on Shopee**. Its dedicated browser encountered a Google sign-in restriction before submission. The successful demo continued through Codex in an already signed-in Chrome window. Local tests and that Chrome result do not establish Python publication success. See the [script guide](docs/SHOPEE_SCRIPT.md) for the login restriction and resumption process.

## Quickstart: the visible Chrome demo

Run these commands from the repository root with Python 3.9 or later:

```sh
python3 examples/browser-demo/prepare_contract.py \
  examples/browser-demo/persona-input.v1.json \
  --output-dir work/browser-demo/prepared
python3 demo-control/server.py --port 8767
```

Open the [local control room](http://127.0.0.1:8767), then provide the current product information in Codex and ask it to start or resume the demo. The first command normalizes sample JSON; the second serves the progress page. Codex performs the browser operations. This route does not require an AI API key.

A fresh clone initially displays a waiting state. Codex creates `work/browser-demo/session.json` from the current task and updates it as actual page evidence becomes available. To continue an existing run, retain its session and the open Chrome product tab. Save requested answers in the control room, then return to Codex and say that the answers are ready. Saving answers does not automatically resume an ended conversation.

The reusable workflow is maintained in [`.codex/skills/autopersona-listing/SKILL.md`](.codex/skills/autopersona-listing/SKILL.md). A relative symlink at `.agents/skills/autopersona-listing` points to that source so Codex can discover it through its [repository Skill location](https://learn.chatgpt.com/docs/build-skills). There is one copy of the Skill, with no global installation required. In Codex opened on this project, invoke `$autopersona-listing` with the current product data. It covers Persona input, visible Chrome, the Python script, follow-up answers, verification, and recording. New products must use their own input and target; the OPEN SPORT demo product ID is not a general default.

## JSON contract

Start with the [complete input template](examples/browser-demo/persona-input.template.v1.json) and validate the producer's output against the [versioned JSON Schema](examples/browser-demo/persona-input.schema.v1.json). The envelope below is abbreviated:

```json
{
  "schemaVersion": "1.0.0",
  "exampleId": "your-source-record-id",
  "listing": {
    "product": {},
    "persona": {},
    "content": {},
    "compliance": {},
    "sales": {},
    "shipping": {},
    "media": {},
    "research": {"internalOnly": true},
    "automation": {"mode": "draft_only", "allowPublish": false}
  }
}
```

Use `null` for unknown scalar values and `[]` for unknown lists. Explicit `false` and zero stock remain meaningful values. Keep confirmed product information in `product`, `compliance`, `sales`, and `shipping`; use `persona` to guide the emphasis of `content`.

Research counts, Verified Purchase labels, and the Missed Buyer segment belong in `research`. They must not become reviews of this particular product or evidence of a safety claim. Reference images belong in `media.referenceImagePaths`; upload images and their confirmation are recorded separately.

`prepare_contract.py` checks the versioned envelope and delegates field normalization to the Python schema code. It produces normalized data, a field map, and candidate questions; it is not a general JSON Schema validator. Ask only for missing information that actually blocks the current page. Full rules are in the [contract documentation](docs/BROWSER_DEMO_CONTRACT.md), and the OPEN SPORT example is in [`products/jlab-open-sport-demo/`](products/jlab-open-sport-demo/).

## Fast Python script

Install the Python dependencies and browser runtime:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

To work on your own existing product, replace the input path and product ID below:

```sh
.venv/bin/python shopee_run.py \
  --input path/to/your-listing.json \
  --product-id YOUR_EXISTING_PRODUCT_ID \
  --fullscreen --hold-open 40
```

This fills the form and stops before submission. Add `--publish` to authorize one submission after page validation. Omit `--product-id` only when creating a new product. The script distinguishes an update from relisting an inactive product and checks the saved fields after submission. If the result is uncertain, it inspects the same product instead of submitting again.

For an existing product, `sales.price` and `sales.stock` set to `null` preserve the values read from its current page and include them in the save verification. The script does not type `null` into the form. Existing images are retained when rerunning the same product; replacing images is a separate operation.

The script uses a dedicated profile under `.autopersona/browser-profile/shopee`. Complete supported Shopee login or verification in that visible window, then press Enter in the running terminal. To supply missing fields, enter `answers path/to/answers.json`; answer keys use dotted paths such as `sales.stock`. The script does not take over an everyday Chrome profile. The observed Google sign-in restriction still needs to be resolved through a supported login method before a Python run can proceed.

Useful options:

| Option | Behavior |
| --- | --- |
| `--prepare-only` | Normalize the input without opening the browser. |
| `--publish` | Authorize one create, update, or relist submission for this run. |
| `--fullscreen` | Use a visible fullscreen window with its native viewport size. |
| `--slow-mo 150` | Add optional pacing for a demonstration; the default is `0`. |
| `--hold-open 40` | Keep the completed page visible for review or recording. |
| `--ai` | Explicitly request API-generated copy; otherwise use the supplied JSON and local preparation. |
| `--record-video-dir work/script-video` | Save private Playwright footage. |

For resumption from Codex or another process, use a new run directory:

```sh
.venv/bin/python shopee_run.py \
  --input path/to/your-listing.json \
  --product-id YOUR_EXISTING_PRODUCT_ID \
  --publish --fullscreen \
  --run-dir work/script-run-01 --wait-for-resume
```

After login or answering a question, write `work/script-run-01/resume.json`:

```json
{"action": "resume", "answers": {"sales.stock": 1}}
```

Use `{"action":"resume"}` without new answers, or `{"action":"stop"}` to stop. The process consumes the signal and continues with the same browser. Each wait defaults to 900 seconds, configurable with `--timeout`. Do not reuse a run directory containing an old report or unconsumed signal. Private `listing.json` and `report.json` files record progress, retained values, and page evidence. See the [full script guide](docs/SHOPEE_SCRIPT.md).

### OPEN SPORT demo shortcut

These commands are **only for replaying this repository's existing OPEN SPORT demo**:

```sh
python3 run_open_sport.py --prepare-only
python3 run_open_sport.py --publish --fullscreen --wait-for-resume --hold-open 40
```

The wrapper selects the project virtual environment when present, the prepared OPEN SPORT input, and its fixed existing product ID `43834400022`. Run the second command only when an actual update or relisting of that demo has been authorized. Omit `--publish` to stop before submission. Use `shopee_run.py` with your own input and target for other products. The wrapper shares the Python login limitation described above.

## Other entry points

| Entry point | Purpose |
| --- | --- |
| `demo-control/server.py` | Progress and answers for Codex-operated Chrome; local port `8767`. |
| `autopersona.py --offline --mode shopee` | Python Beta dashboard on port `8765`, with a separate visible browser and local copy preparation. |
| `autopersona.py --offline --mode demo` | Local seller-page fixture for development and tests. |
| `src/cli.js` | Earlier JavaScript draft, validation, and form-filling workflow; stops before publication. |

`--offline` chooses the copy source; only `--mode demo` selects the local simulated seller page. Details are in the [Python Beta guide](docs/PYTHON_BETA.md) and [earlier JavaScript workflow](docs/WORKFLOW.md).

## Recording

On macOS, `record_visible_demo.py` captures the visible screen without audio and exports a 30–40 second MP4. Keep the intended Chrome window in the foreground and allow the capture to finish naturally:

```sh
.venv/bin/python -m pip install -r requirements-video.txt
.venv/bin/python record_visible_demo.py capture \
  --seconds 90 --clicks \
  --output work/recording-01/raw.mov
.venv/bin/python record_visible_demo.py export \
  --input work/recording-01/raw.mov \
  --output artifacts/autopersona-visible-demo.mp4 \
  --seconds 36
```

Screen capture requires macOS Screen Recording access. Choose a new raw output path each time. The export writes a video and a matching JSON manifest; it does not determine publication success. Use `--segments` to select actual scenes and add captions, cropping, or redactions. See the [recording guide](docs/BROWSER_DEMO.md).

The delivered OPEN SPORT video is a tour of the saved result and its verification; it does not contain the original update submission. The older `record_demo.py` records only the local fixture and cannot demonstrate a real Shopee listing. Review every shareable clip for accurate claims and private account information.

## Development and tests

After installing the Python dependencies, run:

```sh
.venv/bin/python -m unittest discover -s tests_python -v
.venv/bin/python -m unittest discover -s examples/browser-demo -p 'test_*.py' -v
.venv/bin/python products/jlab-image-demo/test_jlab.py
node --test
```

JavaScript requires Node.js 20 or later; `npm test` also runs `node --test`. Browser integration tests use local fixtures. Their success verifies application behavior, not a live Shopee publication.

## Configuration and privacy

The Codex-operated demo needs no API configuration. For Python AI mode, copy [`.env.example`](.env.example) to a local `.env` and supply `OPENAI_API_KEY` or the supported legacy `GPT-API` key name. `OPENAI_MODEL` and `OPENAI_BASE_URL` are configurable; environment variables take precedence over the file. API failures are reported rather than presented as successful AI generation.

Keep credentials out of product JSON, source code, screenshots, and logs. `.env`, `work/`, `.autopersona/`, `artifacts/`, recordings, and browser sign-in profiles are ignored by Git. Share source examples and reviewed deliverables rather than raw run state, answers, or login footage.
