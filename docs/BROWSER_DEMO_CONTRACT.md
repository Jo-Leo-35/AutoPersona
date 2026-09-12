# Browser Demo Persona JSON 契約 v1

本契約把使用者 Persona 資料整理成可替換的 JSON，沿用現有 Python 正規化規則。範例可直接交給 Codex 操作已登入的真實賣家頁面；資料準備器本身不讀 `.env`、不呼叫 API、不操作瀏覽器。範例不是商品完成上架的證據。

## 檔案

| 檔案 | 用途 |
| --- | --- |
| `examples/browser-demo/persona-input.v1.json` | 這次開放式耳機／父母照護者示範的輸入與初步文案 |
| `examples/browser-demo/persona-input.template.v1.json` | 正式 JSON 到位時可複製的空白模板 |
| `examples/browser-demo/persona-input.schema.v1.json` | JSON Schema Draft 2020-12，供正式資料產生端驗證 |
| `examples/browser-demo/normalized.v1.json` | 既有 Python 正規化後的 canonical camelCase 欄位 |
| `examples/browser-demo/field-map.v1.json` | 瀏覽器操作參考；依 `entries[].path` 找欄位 |
| `examples/browser-demo/questions.v1.json` | Python 契約目前缺口；不是每題都要在本次詢問 |
| `examples/browser-demo/prepare_contract.py` | 無額外依賴的本機轉換器 |
| `examples/browser-demo/test_contract.py` | 契約、研究隔離、未知值與授權界線驗證 |
| `prompts/browser-demo-persona-to-listing.md` | Codex 對話示範用文案規則；未接管既有 planner 提示詞 |

版本信封固定為：

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

上方只示意外層；完整欄位請複製模板，保留未知純量為 `null`、未知清單為 `[]`。`schemaVersion` 和 `exampleId` 是來源契約資料，不會填進賣家欄位；Python 的 `normalize_listing()` 只回傳 `listing`，此轉換器會另保留版本與來源識別。

## 更換正式 JSON

1. 以正式來源取代模板的 `listing`，設定可追溯的 `exampleId`。同事若有不同結構，先按下表對映到 canonical 路徑。`schemaVersion` 變更時需明確轉換，不當成 v1 默默處理。
2. 正式產生端用提供的 JSON Schema 驗證結構，再執行本機轉換。`prepare_contract.py` 檢查版本與外層，欄位型別轉換及跨欄位一致性委派給既有 `normalize_listing()`；它不是通用 JSON Schema 驗證器。
3. 檢閱 `normalized.v1.json` 與 `field-map.v1.json`，以真實頁面確認類別和動態屬性。填入 `fillable=true` 的已知值後，才針對頁面阻礙整理問題。
4. 補答用既有 `apply_answers(listing, answers)`，答案鍵為 dotted path。需要重新產出對映時，將更新後的 listing 放回同版本信封執行轉換。

從專案根目錄執行（輸出用新的目錄，避免覆蓋示範 fixture）：

```sh
.venv/bin/python examples/browser-demo/prepare_contract.py examples/browser-demo/persona-input.v1.json --output-dir work/browser-demo/prepared
.venv/bin/python -m unittest discover -s examples/browser-demo -p 'test_contract.py' -v
```

正式輸入使用 camelCase。既有 Python 也接受各 canonical 欄位的精確 snake_case，例如 `category_path`、`use_cases`、`has_bsmi`、`package_size_cm`、`image_paths`，並接受外層 `listing` 包裝；這是 Python 匯入相容能力，不是此嚴格 canonical JSON Schema 的額外別名。兩種拼法同時出現且值不同會拒絕。只放在信封外層的 `product`／`sales` 不會被當作 listing；請把事實放到 listing 內。

## 來源到欄位

| 來源內容 | canonical 目的地 | 規則 |
| --- | --- | --- |
| 品類＋已提供受眾定位 | `product.title` | 只做有依據的名稱草稿，不創造品牌、型號或功能 |
| 需要保持環境感知的父母／照護者 | `persona.audience` | 目標客群文字 |
| 照護時希望留意周遭動靜 | `persona.useCases` | 需求情境，不是產品效果 |
| 在意環境聲音察覺 | `persona.painPoints` | 選購考量 |
| 以照護者需求出發 | `persona.positioning` | 文案定位 |
| 初步描述、重點、關鍵字 | `content.*` | 僅使用已確認事實與需求措辭 |
| 13 則命中 | `research.matchedReviewCount` | 整數 `13`；僅內部研究 |
| 全部 Verified Purchase | `research.allMatchedReviewsVerifiedPurchase` | `true`；不可成為本商品評價 |
| Missed Buyer | `research.buyerSegment` | 內部分群；不填賣家表單 |
| 實際品牌／SKU／型號 | `product.brand` / `product.model` | 本例未知，維持 `null`；SKU 不由圖片建立，也不杜撰新欄位 |
| 售價、庫存 | `sales.price` / `sales.stock` | 數值；未知為 `null`，明確庫存 `0` 可保留 |
| 認證、包裝、連線方式 | `compliance.*` | 未確認維持 `null`；`false` 代表已確認否定，不代表未知 |
| 包裹重量／尺寸／危險品判定 | `shipping.*` | 只取實際確認資訊 |
| 兩張參考圖 | `media.referenceImagePaths` | 保留來源用途；本例上傳清單為空 |
| 真頁面確認的分類 | `product.categoryPath` | 這次實站選項為「影音 > 耳機/耳麥/藍牙耳機」；之後每次重核 |

未列於 Python `FIELDS` 的賣家動態屬性（例如實站的「耳機類型」）先作頁面問題，不自行發明 JSON 欄位；需要支援時再修改正式 schema 與對映。Persona 的 needs 不可直接填為商品功能屬性。

## 本次可填文案與保留值

名稱：**開放式耳機｜父母與照護者選購參考**。本次實站已回報名稱 `16/60` 字、描述 `119/3000` 字；只是此刻頁面的觀察，不是所有類別永遠通用的限制。

描述：

> 給需要留意周遭動靜的父母與照護者，整理開放式耳機的選購方向。
>
> 照護日常中，除了個人的聆聽需求，也會在意環境聲音的察覺。選購時，可先釐清使用情境，再依已確認的商品資料評估。
>
> 商品規格、包裝內容與保固資訊，請以後續確認的實際商品資料為準。

品牌、型號、狀況、GTIN、價格、庫存、規格、認證、包裝、保固與物流事實都未提供。名稱與描述可用來完成可逆草稿，但不是完整可販售商品資料。分類值來自本次真頁面選項；類別展開的品牌、耳機類型、連接類型仍待實際商品資料。

兩圖的身份、用途與授權分開記錄：`demo-0.png` 為多品牌合照，`demo-1.png` 為單組黑色耳掛耳機與充電盒外觀參考，不能確定 SKU。本例 `imagePaths=[]`、`referenceOnly=true`、`confirmedProductImages=false`、`uploadAuthorized=false`。`false` 在此代表**目前未獲本回合上傳確認**，並非使用者永久禁止上傳；之後收到明確圖片與授權可更新。本 adapter 只在圖片清單有值、已確認商品身分、已授權、且非 referenceOnly 時才標示可上傳。

## Field map 與對話進度頁

`entries` 使用以下欄位：`path`、`label`、`value`、`status`、`fillable`、`required`、`reason`。`status` 可為 `ready`、`needs_answer`、`needs_page_choice`、`copy_context`、`local_control`、`withheld`。`fillable` 只是素材建議；實際填入仍要從當下頁面找到並核對控制項，不包含頁面選擇器或提交命令。

Persona 欄位、highlights 與 keywords 只作文案來源，因既有頁面對映沒有這些獨立欄位而不直接填入。research 不出現在 field map。分類即使有路徑也會標成 `needs_page_choice`，提醒操作方確認當下選項；不能由 JSON 自稱已選對。`required` 來自既有通用 Python 契約，不取代本次真頁面的必填判斷。

若使用這次的本機進度頁，由協調者將名稱與描述放入 `session.copy={title,body}`，根據實站整理少量 `session.questions`。不要直接把 `questions.v1.json` 全部塞進 UI；它包含無法一口氣要求使用者回答的通用資料缺口。進度頁補答以既定的 `answers[id]={value,updated_at}` 交回協調者，再對映到 canonical path，保留布林與數值型別。

所有輸出均為 `automation.allowPublish=false`。檔案值不授權任何發布，也不把「已產生」「已填入」「已儲存」「已發布」混為一談；真實操作結果要另外以頁面證據記錄。
