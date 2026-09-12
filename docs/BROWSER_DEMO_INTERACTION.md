# 真實 Chrome 展示控制室

第一階段由 Codex 操作真實 Chrome，這個獨立進度頁只顯示主流程回報並保存補答。它不載入 `.env`、不呼叫 AI API、不執行現有 Python Beta、Playwright 或任何上架操作。

在專案根目錄執行：

```sh
python3 demo-control/server.py
```

開啟 <http://127.0.0.1:8767>。僅綁定 `127.0.0.1`，不部署網站。可用 `--port 8768` 更換埠號；`--data-dir /absolute/path` 僅供獨立測試。按 Ctrl+C 結束，再次執行時會讀取原有 session 與同輪 answers，不會重新開一輪或重設進度。

## 主流程的唯一進度來源

主 agent 是 `work/browser-demo/session.json` 的唯一寫入者，建議透過 temporary file + atomic replace 更新。伺服器不建立、不修改 session。頁面每 1.5 秒讀取一次；缺檔時顯示等待，格式暫時無法讀取時保留最後畫面並自動重試。

以下為格式示意，階段的 `done` 必須由實際完成證據支持。不要把此範例當成已發生的操作。

```json
{
  "version": 1,
  "run_id": "browser-demo-001",
  "title": "從 Persona 洞察，到真實商品頁",
  "updated_at": "2026-09-12T08:00:00Z",
  "status": "running",
  "summary": "準備 Persona 與文案；等待確認真實頁面。",
  "current_stage": "persona",
  "stages": [
    {"id": "persona", "status": "running", "detail": "整理內部研究"},
    {"id": "copy", "status": "pending"},
    {"id": "browser", "status": "pending"},
    {"id": "questions", "status": "pending"},
    {"id": "verify", "status": "pending"}
  ],
  "persona": {
    "title": "需要保持環境感知的父母與照護者",
    "summary": "開放式耳機的使用需求：聆聽內容時，仍能留意孩子與周遭環境。",
    "evidence": ["13 則命中皆為 Verified Purchase", "Missed Buyer"],
    "label": "內部 Persona 研究；不是本商品的消費者評價或效能保證。"
  },
  "copy": {"title": "主流程核對後的商品標題", "body": "主流程核對後的商品說明"},
  "browser": {"title": "等待頁面確認", "summary": "尚未回報真實頁面狀態"},
  "questions": [],
  "verification": {"summary": "尚無驗證結果", "items": []},
  "events": [{"at": "2026-09-12T08:00:00Z", "message": "開始本輪展示"}]
}
```

頂層 `status` 可用 `running / waiting / completed / blocked`；階段 `status` 可用 `pending / running / waiting / done / blocked`。五階段順序固定，缺少的階段一律顯示待進行。`current_stage` 只標示目前位置，不能取代明確的階段狀態。`browser.url` 可選，僅接受 HTTP(S) 並顯示純文字網址與「請切換到已開啟的 Chrome 商品分頁」提示；不提供開啟新表單的連結，避免中斷尚未儲存的填寫。`events` 按時間由舊到新提供，頁面倒序顯示最後 20 筆。

## 根據實站集中補答

只有主流程寫入的 `questions` 會成為表單，不會自動產生固定問題，也不會由 schema 一次攔下所有缺欄位。請勿加入密碼、API key、登入憑證或驗證碼等問題。

```json
{
  "questions": [
    {"id": "sales.price", "label": "這次商品的售價", "help": "實際頁面目前需要價格才能繼續。", "type": "text", "required": true},
    {"id": "product.condition", "label": "商品狀況", "type": "select", "options": ["全新", "二手"]},
    {"id": "product.notes", "label": "其他需要補充的內容", "type": "textarea"}
  ]
}
```

每題需有唯一且穩定的字串 `id` 與 `label`；`help / type / options / required` 可省略，type 預設 text。`required` 只標示「需確認」，允許先保存部分內容；主流程自行決定尚缺哪些資料。補答只寫入本機檔案，不會自動喚醒已結束的 Codex 對話。儲存後請回原 Codex 對話說「已補好，繼續」，沿用已開啟的 Chrome 商品分頁，不用重開商品頁。補答儲存本身不會推進階段、填入商品頁、宣稱已驗證或發起新的提問。

伺服器只寫入 `work/browser-demo/answers.json`，格式如下：

```json
{
  "version": 1,
  "run_id": "browser-demo-001",
  "updated_at": "2026-09-12T08:12:00+00:00",
  "answers": {
    "sales.price": {"value": "1990", "updated_at": "2026-09-12T08:12:00+00:00"}
  }
}
```

同輪補答以 question id 合併，重啟保留；尚未儲存的輸入在輪詢時保留。新輪 `run_id` 不會載入舊輪答案，首次儲存新輪補答會取代 answers 檔；需要保存歷史時請主流程先另行歸檔。頁面輪次過期或題目已被移除時，提交會被拒絕並要求重新整理。

## 本機介面

- `GET /health`：服務存活檢查。
- `GET /api/state`：`{"session": {...}, "answers": {...}}`，只投影文件列出的進度欄位。
- `POST /api/answers`：`Content-Type: application/json`，body 為 `{"run_id": "...", "answers": {"question.id": "文字"}}`。

API 不提供任意檔案讀取，也不輸出原始 session 的未知欄位。進度文案本身仍應只放適合展示的資訊。研究與文案分區呈現；研究證據不能自動當成商品評價或可上架敘述。
