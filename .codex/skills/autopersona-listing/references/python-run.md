# Python 快速執行

以下命令在 AutoPersona 專案根目錄執行。安裝方式見 `docs/SHOPEE_SCRIPT.md`；沿用現有 `.venv`。腳本使用專用登入 profile 與可見 Chrome。

## 準備與啟動

一般商品先驗證輸入，不開瀏覽器：

```sh
.venv/bin/python shopee_run.py --input PATH_TO_JSON --prepare-only
```

已獲授權更新既有商品時：

```sh
.venv/bin/python shopee_run.py --input PATH_TO_JSON --product-id CONFIRMED_PRODUCT_ID --publish --fullscreen --wait-for-resume --hold-open 40
```

`PATH_TO_JSON`、`CONFIRMED_PRODUCT_ID` 是需要替換的參數。只有明確要建立新商品才省略 `--product-id`；只填表核對則省略 `--publish`。

使用者明確要求重跑同一個 OPEN SPORT Demo，且本輪已授權實際更新／重新上架時可用：

```sh
python3 run_open_sport.py --publish --fullscreen --wait-for-resume --hold-open 40
```

此簡化入口固定預設 JSON 與歷史商品 `43834400022`，自動使用專案 `.venv`。不要用它處理另一件商品。無瀏覽器檢查可用 `python3 run_open_sport.py --prepare-only`。

預設 `--slow-mo 0`，不額外延遲；要看清錄影步驟才用 `--slow-mo 150`。`--fullscreen` 使用實際視窗尺寸。`--hold-open` 避免完成時立即關閉錄影畫面。

預設依輸入 JSON／離線整理文案，不呼叫 AI。只有需要 API 生成時才加 `--ai`；API 失敗不能當成成功生成。

## 同輪續接

Codex 的非互動式執行需要 `--wait-for-resume`。終端會顯示本輪資料目錄；`report.json` 記錄最新 phase、questions、目標 ID 與 elapsedSeconds。用唯一的新 `--run-dir` 或預設自動目錄；不可重用有舊 report／訊號的資料夾。

登入、驗證或頁面操作由使用者在可見視窗完成。完成後向本輪目錄原子寫入 `resume.json`：

```json
{"action":"resume"}
```

有已確認補答時：

```json
{"action":"resume","answers":{"sales.price":3990,"sales.stock":1}}
```

價格與庫存只是訊號格式範例，需使用本輪答案。只補真正缺少的 schema 欄位；`page.*`／`manual` 問題需在頁面操作。JSON 中的 `null` 價格與庫存於既有商品保留原值；不要改成預設數字。

停止目前輪次寫入 `{"action":"stop"}`，等待程序關閉。互動式終端機中，Enter 代表續接，`answers PATH` 代表補答後續接，`stop` 才代表停止；停止後同樣等待程序退出。

Google 登入拒絕自動化瀏覽器時停止該輪，不循環重試。可請使用者採用蝦皮支援的登入方式，或切換到已登入 Chrome 的 Codex 路線；先停 Python，再交接唯一 UI 操作者。2026-09-12 真實快跑在此受阻，當輪改由 Codex Chrome 完成。16 項本機腳本／adapter 測試曾通過，但不代表真實 Python 已發布成功。

## 結果

- `ready`：已填妥、尚未提交；省略 `--publish` 的預期結果。
- `published`：工作流已取得保存驗證；另查看 `browser.completionVerified`、實際 URL 與 `operation`。
- `operation: update`／`relist`：一般更新／重新上架。後者需新詳情頁的「下架」狀態。
- `browser.retainedExistingFields`：保留並核對原值的欄位。
- `elapsedSeconds`：本輪啟動至該 report 的時間，包含登入及補答等待，不能當作純填表耗時。

送出結果不明時只 inspect／resume 同一輪。腳本每輪最多提交一次，不能靠開新輪重送來消除不確定性。保存後核對詳情，並如實區分賣家架上狀態與未測試的買家下單。
