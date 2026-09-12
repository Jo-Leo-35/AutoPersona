# AutoPersona

將 Persona 研究整理成商品草稿，依蝦皮賣家中心的實際欄位補齊資料，再核對操作結果。商品事實、行銷文案與內部研究分開保存；未知品牌、型號、價格、規格與認證不自動補造。

## 從真實 Chrome 展示開始

目前主要入口是 **Codex 操作可見的真實 Chrome**。本機控制室顯示 Persona → 文案 → 真實頁面 → 待補資訊 → 驗證，補答後回 Codex 對話接續同一個商品分頁。

2026-09-12 的 **JLab JBuds OPEN SPORT** 本輪 Demo 已完成既有商品更新並從保存詳情讀回：耳機類型為開放式，完整文案含左右 NCC 與內容物，售價 3990、庫存 1、圖片 2 張。此為真實賣家中心操作；未測試買家下單。見 [本輪操作與錄影](docs/OPEN_SPORT_DEMO.md)、[Persona JSON 串接](docs/OPEN_SPORT_PERSONA.md) 與 [實站驗證紀錄](docs/OPEN_SPORT_BROWSER_RUN.md)。舊圖片研究與舊操作紀錄保留為歷史資料。

在專案根目錄執行，需 Python 3.9 以上：

```sh
python3 examples/browser-demo/prepare_contract.py \
  examples/browser-demo/persona-input.v1.json \
  --output-dir work/browser-demo/prepared
python3 demo-control/server.py --port 8767
```

開啟 [展示控制室](http://127.0.0.1:8767)，在 Codex 對話提供本輪商品資料並開始或續接。第一個命令只整理範例 JSON；第二個命令只提供進度頁，瀏覽器操作由 Codex 執行。這個入口不需要 AI API key。

新 clone 尚無執行狀態，控制室會先顯示等待；由 Codex 建立 `work/browser-demo/session.json`。既有輪次沿用原檔與已開啟的 Chrome 商品分頁。儲存補答後，回對話說「已補好，繼續」。完整步驟見 [真實 Chrome 展示](docs/BROWSER_DEMO.md)。

## 選擇工作方式

要從 JSON 直接執行有視窗的自動化，可用 `shopee_run.py`：支援既有商品 ID、登入後續接、補答及單次提交。[腳本操作說明](docs/SHOPEE_SCRIPT.md)

本輪 OPEN SPORT 的簡化入口是 `python3 run_open_sport.py --publish --fullscreen`：自動選用專案虛擬環境、正式 JSON 與既有商品 ID，預設不加逐步操作延遲。只檢查輸入可用 `python3 run_open_sport.py --prepare-only`。省略 `--publish` 會填表並停在保存前；專用 Chrome 若需要登入，完成登入後在終端機按 Enter 續接。

| 入口 | 用途 | 控制頁／結果 |
| --- | --- | --- |
| `demo-control/server.py` | 第一階段：Codex 操作現有真實 Chrome | `127.0.0.1:8767`；以實站頁面核對進度 |
| `shopee_run.py --input … --product-id …` | JSON 驅動可見 Playwright；續接及更新既有商品 | 終端機／本機 run report；`--publish` 才送出 |
| `autopersona.py --mode shopee` | Python Beta：Playwright 開啟獨立可見瀏覽器、填表與補答 | `127.0.0.1:8765`；仍需實站驗證 |
| `autopersona.py --offline --mode demo` | 本機賣場 fixture，供開發與測試 | 本機模擬，未建立真實蝦皮商品 |
| `src/cli.js` | 保留的早期 JavaScript 草稿、驗證與填表流程 | 停在發布前，見 [早期流程文件](docs/WORKFLOW.md) |

Python Beta 的安裝、AI／離線差異與命令見 [Python Beta 說明](docs/PYTHON_BETA.md)。`--offline` 控制文案來源；`--mode demo` 才代表本機模擬。

## 可重複使用的 Skill

[autopersona-listing](skills/autopersona-listing/SKILL.md) 整理了 Persona JSON、可見 Chrome、Python 快跑、補答續接與錄影核對。可在 Codex 指定讀取此 Skill；安裝成個人 Skill 後，以 `$autopersona-listing` 呼叫。Skill 需搭配此專案，使用者指定的專案位置優先。

例如：「使用 autopersona-listing Skill，快速重播同一個 OPEN SPORT，錄影已開始，使用全螢幕。」Skill 會沿用已確認資料與發布授權；新商品不沿用範例商品 ID。

2026-09-12 的 Python 真實快跑在 Google 登入限制處停止，之後由 Codex 操作已登入 Chrome 完成商品更新及保存核對。此結果不代表 Python 端到端發布已通過；[登入限制與續接](docs/SHOPEE_SCRIPT.md#google-登入限制實跑記錄) 保留完整說明。

## 資料與錄影

- [版本化 JSON 契約與範例](docs/BROWSER_DEMO_CONTRACT.md)：對接 Persona Engine，保留商品未知值。
- [進度、補答與續接格式](docs/BROWSER_DEMO_INTERACTION.md)：`session.json` 與 `answers.json` 的責任邊界。
- [實站觀察紀錄](docs/BROWSER_DEMO_OBSERVATIONS.md)：具日期的頁面觀察，不代表每次執行都已完成。
- [JLab 圖片案例與受眾適配研究](docs/PRODUCT_RESEARCH.md)：品牌比對、尚未確定的型號、來源及可用商品 JSON；保留原 Persona 與入耳式商品的定位落差。
- `record_visible_demo.py`：錄製目前可見的真實 Chrome 操作；使用方式見 [錄影說明](docs/BROWSER_DEMO.md#錄製真實操作)。
- `record_demo.py`：保留的 **legacy local fixture** 錄影器，只錄本機模擬流程，不能作為蝦皮操作或上架證據。

`examples/` 保存可分享範例；`products/` 與根目錄小型參考圖保留既有素材。研究中的 Verified Purchase、命中數與客群標籤屬於內部研究，不能直接寫成這件商品的評價或效能保證。

## 開發與驗證

工作分支為 `Python-Beta-Python-Branch`。Python Beta 依賴安裝完成後，在專案根目錄執行：

```sh
.venv/bin/python -m unittest discover -s tests_python -v
.venv/bin/python -m unittest discover -s examples/browser-demo -p 'test_*.py' -v
.venv/bin/python products/jlab-image-demo/test_jlab.py
node --test
```

JavaScript 需 Node.js 20 以上，`npm test` 等同 `node --test`。Python 瀏覽器整合測試使用本機 fixture；測試通過不能代替實際蝦皮結果。

`.env`、`work/`、`.autopersona/`、`artifacts/`、錄影原片與登入 profile 都是本機私有資料，已列入 `.gitignore`。AI 設定只從 [.env.example](.env.example) 複製並在本機填入。公開分享影片前，確認內容與實際結果一致，且未包含登入憑證或帳號私人資訊。
