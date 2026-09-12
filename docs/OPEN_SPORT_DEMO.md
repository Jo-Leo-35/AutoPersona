# JLab OPEN SPORT：Persona 驅動的真實蝦皮 Demo

本輪商品是 **JLab JBuds OPEN SPORT 開放式運動藍牙耳機**。商品依據為使用者提供的正式型號、規格與內容物；舊輪從圖片推測的入耳式定位已不適用。開發分支為 `Python-Beta-Python-Branch`，既有 staged／unstaged 修改保留。

第一階段由 Codex 生成 AI 文案，使用瀏覽器工具操作使用者看得到的 Chrome。Python 提供本機進度頁、資料整理與錄影輔助；本輪不以 Python／Playwright 自動化或模擬賣場作為真實上架成功證據。

## 展示入口與進度

- 專案：`/Users/etahn/Ethan_file/AutoPersona`
- 控制室：<http://127.0.0.1:8767>
- 既有蝦皮商品：<https://seller.shopee.tw/portal/product/43834400022>
- 已核對的公開商品頁：<https://shopee.tw/product/607172018/43834400022/>
- 本輪進度：`work/browser-demo/session.json`
- 補答：`work/browser-demo/answers.json`（有補答才建立）
- 舊進度歸檔：`work/open-sport-interaction/session-before-open-sport.json`

本輪已讀到既有售價 NT$3,990、庫存 1 與 2 張圖片，保留這些現場值；已送出商品更新並返回列表，再從真實商品連結開啟新的詳情分頁；新標題、604 字完整描述、開放式類型、認證與售價／庫存皆已讀回一致。賣家中心保存驗證完成，且已核對架上商品分頁與公開商品頁；未進行第三方買家下單。

控制室以 Persona → 商品與文案 → 真實蝦皮 → 補充資訊 → 保存驗證呈現進度。「已確認商品」卡將商品事實與內部 Persona 研究分開；「展示方式」說明 AI 文案由 Codex 產生、Chrome 由瀏覽器工具操作。完成標記由實站證據更新。

## 啟動與續接

在專案根目錄執行以下指令；若 `/health` 已回傳 `ok: true`，沿用現有服務即可。

```sh
python3 demo-control/server.py --port 8767
```

服務只綁定 `127.0.0.1`，不載入 `.env`、不呼叫 AI API、不控制蝦皮。原有 session 與同輪補答在重啟後保留。不要為了重播另開新增商品頁；沿用商品 ID 43834400022，先確認目前實站內容。

對話續接範例：

> 繼續 AutoPersona OPEN SPORT 第一階段 Demo。先讀 docs/OPEN_SPORT_DEMO.md、本輪商品 JSON、work/browser-demo/session.json 與 answers.json（若存在）。由單一 agent 沿用真實 Chrome 的商品 43834400022，核對與修正完整描述及耳機類型；保存後重新讀回。需要補答時只集中詢問實站仍欠缺的資料。請錄下實際畫面，依證據更新控制室，不把舊輪或模擬結果當成本輪成功。

## 正式 JSON 串接

本輪獨立資料放在 `products/jlab-open-sport-demo/`，保留舊商品資料。正式 Persona Engine 可提供相同 `schemaVersion: "1.0.0"` 與 `listing` 巢狀格式；其餘結構與原 `docs/BROWSER_DEMO_CONTRACT.md` 相容。

| 檔案 | 用途 |
| --- | --- |
| `persona-input.v1.json` | 可提供給隊友的本輪輸入樣例 |
| `listing.v1.json` | 正規化的商品、Persona、文案及欄位值 |
| `product-facts.json`、`confirmed-facts.json` | 本輪使用者提供的正式規格與確認依據 |
| `observed-site-state.json` | 瀏覽器讀到的現場值，與使用者確認分開 |
| `browser-handoff.json`、`field-map.v1.json` | 交給唯一瀏覽器操作 agent 的欄位對映 |
| `title.txt`、`description.txt` | 可直接填入的標題與完整 604 字文案 |
| `questions.v1.json` | 依實站需要才提出的補充欄位候選 |

`listing.sales.price` 與 `stock` 保持 `null`，因為本輪對話沒有新增指定價格／庫存；現場讀到 3990／1 保存在 `observed-site-state.observedFields`，用於保留既有值。控制室不把整份 questions 候選清單一次問完，只有實站阻擋下一步時才填入 `session.questions`。

研究命中數及 Verified Purchase 標籤放在 `listing.research`，商品頁使用 `listing.content.description`。左右耳 NCC 全碼保留在完整文案，單碼認證欄的實際限制由瀏覽器操作 agent 確認。

## 展示步驟與說詞

1. **Persona 洞察。**「Persona Engine 發現需要保持環境感知的父母與照護者，13 則命中全部為 Verified Purchase，分類為 Missed Buyer。」這是研究依據，不是本商品的 13 則買家評價，也不代表需求普遍率。
2. **已確認商品與 AI 文案。**展示 OPEN SPORT 型號、藍牙 5.3、14.2 mm 單體、IP55（耳機）、續航與內容物。Codex 將『希望兼顧聆聽與周遭互動』轉為商品定位，避免宣稱照護安全或必定聽見環境聲。
3. **可見 Chrome。**切換至現有蝦皮商品頁，展示已知資料填入與修正。實際頁面由唯一瀏覽器操作 agent 控制，其他 agent 負責契約與控制室，避免競爭同一表單。
4. **依頁面補充。**需要時在控制室補答，按「儲存補答」，回 Codex 說「已補好，繼續」。儲存補答只寫本機資料；主流程讀取後接續原表單。
5. **保存與讀回。**根據本輪授權保存，重新開啟商品詳情或商品列表，核對商品 ID、標題、完整描述、開放式屬性、價格／庫存、認證和實際商品狀態。只有讀回成功才將驗證改成已完成。

若平台只保存修改但尚未顯示可販售狀態，展示說詞應為「已保存並讀回商品資料」；上架狀態依平台實際結果陳述。

## 錄製本次實際操作

首次 600 秒錄製在提前中斷後沒有輸出原片，因此不作為影片證據。已完成的商品更新與公開頁核驗仍有實站紀錄。本輪改為重新錄製 **保存後成果導覽**，不重送更新，內容是 Persona 控制室、商品資料與文案、賣家中心保存欄位、公開商品頁。影片不聲稱包含原始送出動作。

5 秒試錄已確認可產生可解碼的 2880×1800 真實畫面。新成果導覽於 UTC 2026-09-12 05:33:50 開始，錄製 180 秒並等待自然結束：

```sh
.venv/bin/python record_visible_demo.py capture \
  --seconds 180 --clicks \
  --output work/open-sport-integration/saved-results-tour-20260912.mov
```

錄影器將路徑解析成絕對路徑再交給 macOS。每個場景都要在原生 Chrome 視窗選取正確分頁；瀏覽器工具讀到背景分頁，不代表螢幕正在顯示該分頁。等待程式顯示實際檔案大小，不要提前終止錄影子程序。原片沒有音訊，保存在私有 `work/`。

主 agent 依实际原片選取片段，裁除帳號及無關畫面，加上符合實際結果的字幕。錄影原始檔名與片段時間寫入隨附 JSON；是否真正上架以獨立實站紀錄為準。

```sh
.venv/bin/python record_visible_demo.py export \
  --input work/open-sport-integration/saved-results-tour-20260912.mov \
  --segments work/open-sport-integration/segments.json \
  --output /Users/etahn/Documents/Codex/2026-09-12/chrome-plugin-browser-openai-bundled-browserfamily-2/outputs/autopersona-shopee-demo.mp4
```

最終影片已匯出並驗證：36.0 秒、1600×900、30 fps、1080 frames、無音訊。六段皆取自 180.11 秒真實成果導覽原片，經剪輯與加速；已完整解碼並檢视六個場景畫面、字幕及裁切，帳號頁首與右側預覽已排除。隨附同名 JSON 包含原片時間、裁切與獨立商品驗證結果。`record_demo.py` 的本機模擬影片不參與這次交付。

## 控制室相容性

既有 `/health`、`GET /api/state`、`POST /api/answers` 與原欄位不變；新增可選的 `product` 和 `execution` 公開欄位，舊 session 沒有這兩欄時對應卡片隱藏。

```json
{
  "product": {
    "title": "JLab JBuds OPEN SPORT 開放式運動藍牙耳機",
    "summary": "使用者正式提供的商品型號與規格。",
    "facts": ["藍牙 5.3", "14.2 mm 動圈", "IP55（耳機）"],
    "source": "使用者已確認型號",
    "reference_note": "圖片用途依本輪素材核對結果。"
  },
  "execution": {
    "summary": "AI 文案由 Codex 產生；真實 Chrome 由瀏覽器工具操作。",
    "items": ["本頁只呈現進度並保存補答。"]
  }
}
```

公開 API 仍只投影指定欄位，未知原始欄位不會呈現在畫面。控制室不能宣告商品保存或發布成功；它只呈現主流程已核對的結果。

## 可重複 Skill

既有 [AutoPersona Listing Skill](../skills/autopersona-listing/SKILL.md) 已加入第一階段可見 Chrome 的操作路由，並通過 Skill 結構檢查。續跑時優先遵循實際頁面證據與單一瀏覽器操作者的安排。Python／Playwright Beta 的實站端到端尚未經本輪驗證。

## 本輪實站驗證紀錄

瀏覽器操作 agent 在 UTC 2026-09-12 05:25:31 送出更新後返回商品列表，並從真實商品連結開啟新的詳情分頁（tab 523925265）重新讀取：

| 項目 | 保存後讀回結果 |
| --- | --- |
| 商品 ID | 43834400022 |
| 標題 | JLab JBuds OPEN SPORT 開放式運動藍牙耳機｜藍牙5.3 IP55（42／60 字） |
| 描述 | 604 字，含完整規格、左右 NCC、內容物與 USB-C 充電線 |
| 耳機類型 | 開放式 |
| 售價／庫存 | NT$3,990／1 |
| 圖片 | 2 張既有圖，本輪未新增上傳 |
| 認證 | NCC 主欄 CCAH24LPA380T2；BSMI R3B170 |
| 頁面結果 | 可見下架／更新按鈕；可見錯誤清單為空 |
| 商品列表 | 同商品 ID，數量 1，無已售完標記 |

另已在「架上商品 (5)」分頁找到同商品，價格 NT$3,990、數量 1，再由「更多 → 即時預覽」開啟[公開商品頁](https://shopee.tw/product/607172018/43834400022/)，確認新標題、NT$3,990、還剩 1 件與尚無評價。公開商品頁與庫存已核對；未進行第三方買家下單。
