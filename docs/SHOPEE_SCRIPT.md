# JSON → 可見 Chrome 自動化腳本

`shopee_run.py` 直接讀取 listing JSON、開啟有視窗的 Playwright、填寫蝦皮欄位，依實際必填欄位收集補答。`--product-id` 指定既有商品；已下架商品會選「上架」，架上商品會選「更新」，重跑不新增另一件商品。

## 安裝與執行

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-video.txt
.venv/bin/python -m playwright install chromium
```

更新本輪既有商品：

```sh
.venv/bin/python shopee_run.py \
  --input products/jlab-open-sport-demo/listing.v1.json \
  --product-id 43834400022 \
  --publish --fullscreen
```

`--publish` 代表本輪完成頁面核對後，授權送出一次「更新／上架」。省略它可只填表並檢查；只有要建立另一件新商品時才省略 `--product-id`。預設沿用專用 `.autopersona/browser-profile/shopee`，不使用日常 Chrome profile。

預設 `--slow-mo 0`，快速填寫沒有額外演示延遲。錄影需要較慢節奏時可加 `--slow-mo 150`；完成後需停留畫面時加 `--hold-open 40`。`--fullscreen` 使用全螢幕視窗與實際視窗大小，不限制為小型 viewport。輸入 JSON 的價格／庫存為 `null` 時，讀取並保留目前商品頁原值，保存後再核對；不把 `null` 寫入表單。

第一次登入或蝦皮要求驗證時，在脚本開啟的 Chrome 完成，再回執行中的終端機按 Enter。遇到缺資料也停在同一商品頁；可用 `answers <JSON檔案路徑>` 補答，例如：

```json
{"sales.price": 3990, "sales.stock": 1}
```

腳本預設保留 JSON 中已整理好的文案，不呼叫 API。需要生成文案時加 `--ai`，設定從本機 `.env` 讀取，不寫入報告；API 失敗不會假裝成功或悄悄改為離線。

## 從 Codex 或其他程序續接

```sh
.venv/bin/python shopee_run.py \
  --input products/jlab-open-sport-demo/listing.v1.json \
  --product-id 43834400022 --publish \
  --run-dir work/script-run-01 --wait-for-resume --hold-open 40
```

登入或補答完成後，向本輪目錄寫入 `resume.json`：

```json
{"action":"resume", "answers":{"sales.stock":1}}
```

沒有新答案時用 `{"action":"resume"}`；結束用 `{"action":"stop"}`。程序讀取後會移除訊號，繼續原有瀏覽器，不重開商品。每次最多等待 900 秒，可用 `--timeout` 調整。新執行目錄不要沿用含有舊 report 或未消費訊號的資料夾。

只有實際頁面要求的欄位會阻擋續接；保留店舖已有的物流設定。無法辨識的自訂欄位會明確提出，不能安全定位時不盲目填寫。

## 狀態、結果與錄影

本輪目錄保存 `listing.json` 與 `report.json`，記錄目標商品、已填欄位、仍缺資料及頁面證據。`ready` 表示填寫完成；`published` 必須有頁面成功證據。既有商品的一般更新標示 `operation: update`，重新上架標示 `operation: relist`。`elapsedSeconds` 記錄本轮到當前狀態的實測秒數，`browser.retainedExistingFields` 列出沿用原值的欄位。

填寫會重用同一表單的定位結果，批次完成已知欄位後檢查。保存後等待實際導頁或保存訊息，再重新載入同一商品詳情核對標題、描述、認證等欄位。重新上架另需在新的詳情頁看到「下架」且沒有「上架」；列表商品總數可能有快取，不作完成證據。

送出後結果不明時，腳本只重新查核，不會重按送出。先看同輪 report 與商品列表，再决定後續操作。

可加 `--record-video-dir work/script-video` 保存 Playwright 原片。完整 Chrome 視窗錄影與 36 秒 MP4 匯出，見 [真實錄影說明](BROWSER_DEMO.md#錄製真實操作)。登入過程與帳號資訊應排除於可分享片段；原片、profile、補答均保持本機私有。

## 適用範圍

本輪對應台灣蝦皮賣家中心的商品編輯頁。類別、品牌、耳機類型、連接類型、NCC、BSMI、售價和庫存依頁面定位；UI 改版或登入驗證仍可能需要可見視窗中的人工續接。

同一既有商品重跑會保留已有圖片，避免重複上傳；替換圖片需先明確移除／更換目前圖庫，腳本不把已有縮圖當成本機圖片內容一致的證明。通用新商品仍需按實際分類的必要欄位驗證。

## Google 登入限制（實跑記錄）

2026-09-12 快速腳本已啟動，但專用瀏覽器的 Google 登入顯示「This browser or app may not be secure」，因此在提交前停止。當輪 Demo 改由 Codex 操作已登入的 Chrome，完成一次更新及重新開啟商品詳情驗證；這不是 Python 端到端成功紀錄。再次使用 Python 前，需先透過蝦皮支援的登入方式完成專用 profile 登入；不要透過降低瀏覽器安全設定處理此錯誤。
