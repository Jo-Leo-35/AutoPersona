# AutoPersona Python Beta

這是保留的 Python／Playwright 工作流程：整理商品草稿、啟動獨立可見瀏覽器、補答缺漏並核對結果。第一階段由 Codex 操作既有 Chrome 的展示入口，請見 [真實 Chrome 展示](BROWSER_DEMO.md)；兩者使用不同控制頁與執行狀態。

## 安裝與啟動

在專案根目錄執行，支援 Python 3.9 以上：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
python autopersona.py --offline --mode shopee
```

使用 Chrome 開啟 [Python Beta 控制面板](http://127.0.0.1:8765)。程式只監聽 `127.0.0.1`；終端機按 Ctrl+C 結束。載入範例並自動啟動可見瀏覽器：

```sh
python autopersona.py --offline --mode shopee --autostart
```

`--input path/to/listing.json` 指定資料；`--port 8766` 更換埠號；`--open-dashboard` 額外開啟面板視窗。預設蝦皮入口為 [待優化商品列表](https://seller.shopee.tw/portal/product/list/live/need_optimized)。瀏覽器使用 `.autopersona/browser-profile/shopee` 的獨立登入資料，不會接手日常 Chrome 的既有分頁。

只產生 JSON、不啟動瀏覽器：

```sh
python autopersona.py --offline --prepare-only \
  --input examples/open-ear-headphones.json \
  --output work/python-beta/prepared.json
```

## AI、離線文案與本機 fixture

| 選項 | 文案來源 | 商品頁面 |
| --- | --- | --- |
| `--ai --mode shopee` | OpenAI API | 真實蝦皮 |
| `--offline --mode shopee` | 本機固定規則 | 真實蝦皮 |
| `--offline --mode demo` | 本機固定規則 | 本機賣場 fixture |

`--offline` 不等於模擬賣場；只有 `--mode demo` 才使用 fixture。開啟本機演練：

```sh
python autopersona.py --offline --mode demo --autostart
```

AI 模式使用專案 `.env` 或環境變數。環境變數優先於 `.env`，同一來源依序接受 `OPENAI_API_KEY`、既有名稱 `GPT-API`。範本見 [`.env.example`](../.env.example)。

| 設定 | 專案預設值／用途 |
| --- | --- |
| `OPENAI_API_KEY` 或 `GPT-API` | API 金鑰，擇一設定 |
| `OPENAI_MODEL` | `gpt-6-astra`，實際可用性以帳號 API 回應為準 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` |

```sh
python autopersona.py --ai --mode shopee --autostart
```

`--ai` 使用 Python OpenAI SDK 的 Responses API 與嚴格 JSON schema 整理文案。請求失敗會回報錯誤，不會把離線內容稱為成功的 AI 結果。金鑰不得放入 Persona、截圖、版本控制或分享檔案。

## JSON 與研究邊界

既有範例為 [`examples/open-ear-headphones.json`](../examples/open-ear-headphones.json)；版本化的第一階段契約見 [JSON 說明](BROWSER_DEMO_CONTRACT.md)。核心格式定義在 [`schema.py`](../autopersona_py/schema.py)，整理邏輯在 [`planner.py`](../autopersona_py/planner.py)，提示詞在 [`persona-to-listing.md`](../prompts/persona-to-listing.md)。

接受 `product`、`persona`、`content`、`compliance`、`sales`、`shipping`、`media`、`research`、`automation` 巢狀欄位，也接受包在 `listing` 內的物件。未知價格、庫存、狀況、品牌、型號、規格、認證與物流數字保留 `null`；集合欄位可為空陣列。`prepare_listing()` 回傳 `listing`、`questions`、`warnings`、`provider`。

AI 只能整理 Persona 與文案，不能改寫已提供的事實或補造商品資料。研究命中數、Verified Purchase 與 Missed Buyer 留在內部 `research`，不能宣稱本次商品有對應數量的已驗證購買評論。客群希望留意環境聲音是需求，不是商品安全或功能已驗證的證據。

`media.imagePaths` 應指向本輪實際使用的圖片；`referenceOnly`、`confirmedProductImages`、`uploadAuthorized` 分別記錄參考用途、商品核對與上傳授權。沿用本輪已取得的授權，換商品時更新相應資料；不要從根目錄參考圖自行推測品牌、型號或規格。圖片不符時應先釐清實際商品。

## 補資料與核對結果

1. 在面板載入 Persona／JSON，選擇文案來源，檢查草稿與研究註記。
2. 啟動可見瀏覽器，完成登入，進入商品頁並填入已知欄位。
3. 回答缺漏問題並繼續；同一瀏覽器工作階段保留原頁面。數值、布林與零庫存均按型別處理。
4. 新出現的必要屬性形成追問；無法可靠對應的控制項由使用者在瀏覽器處理，再回面板核對。
5. 若本輪要求發布，先核對具體商品內容；面板以完全相同的商品名稱綁定最後操作。只有實際頁面確認成功，才可記錄發布完成。

程式有流程與重複提交防護，但尚未保證所有蝦皮分類均可自動填妥。本機 fixture 成功、HTTP 回應或按鈕點擊本身，都不是實際蝦皮發布證據。登入、驗證與平台變動需依可見頁面處理。

## 錄影入口

真實 Chrome 操作錄影使用根目錄 `record_visible_demo.py`，見 [真實操作錄影](BROWSER_DEMO.md#錄製真實操作)。

舊的 `record_demo.py` 是 **legacy local fixture** 錄影器：它會把面板切到 `mode=demo`，填入示範答案並完成本機模擬發布。保留它供開發回歸，不能用它的影片宣稱操作或發布了真實蝦皮商品。獨立啟動 fixture 面板後才執行：

```sh
python -m pip install -r requirements-video.txt
python autopersona.py --offline --mode demo
```

另一個終端機執行：

```sh
source .venv/bin/activate
python record_demo.py --url http://127.0.0.1:8765 \
  --output artifacts/local-fixture-demo.mp4
```

此命令會操作所指定的本機面板，請使用專供 fixture 的執行輪次。`--ai` 只改變整理文案的來源，不會把 fixture 錄影變成真實蝦皮錄影。

## 驗證與既有 skill

```sh
.venv/bin/python -m unittest discover -s tests_python -v
```

測試涵蓋未知事實保留、答案型別、模型輸出邊界、設定遮蔽與流程狀態。瀏覽器整合測試使用本機 fixture，需 Playwright 與 Chromium；缺少 Playwright 時會略過該整合測試。

[`skills/autopersona-listing/SKILL.md`](../skills/autopersona-listing/SKILL.md) 是既有 Python Beta skill 草稿，保留供後續整合。第一階段 Codex 操作 Chrome 的觀察，需經實站驗證後再整理成可重用規則。
