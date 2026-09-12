# JBuds OPEN SPORT Persona 介接資料

本輪商品資料位於 `products/jlab-open-sport-demo/`，保留原有 `products/jlab-image-demo/` 修改與歷史記錄。商品型號、規格、認證字號與內容物取自 2026-09-12 本輪使用者提供資料；此資料建置步驟沒有呼叫 API、讀取 `.env` 或操作瀏覽器。

## 輸入與輸出

隊友的 Persona Engine 可輸出 `persona-input.v1.json` 相同結構。沿用 `examples/browser-demo/persona-input.schema.v1.json`，外層為 `schemaVersion`、`exampleId`、`listing`。未知值使用 `null`，陣列無資料使用 `[]`。

| 區塊 | 本輪用途 |
| --- | --- |
| `listing.product` | 使用者明示的 JLab JBuds OPEN SPORT 型號、標題與候選商品分類 |
| `listing.persona` | 父母／照護者的需求、使用情境與文案定位 |
| `listing.content` | 可填商品頁的標題以外文案、重點與關鍵字 |
| `listing.compliance` | NCC、BSMI、無線、開放式及實際內容物 |
| `listing.sales`、`listing.shipping` | 本輪未提供的販售／物流資料保持 `null` |
| `listing.media` | 參考圖片路徑；本輪沿用頁面既有圖片，不新增上傳 |
| `listing.research` | 13 則、全部 Verified Purchase、Missed Buyer 等內部研究 |
| `listing.automation` | 與既有範例一致的草稿模式；資料匯入本身不觸發發布 |

`research` 可增加隊友的來源與追溯資料，其餘區塊沿用現有 schema。需要新增欄位時，先共同更新 schema、Python 欄位定義及控制室映射。不要將研究命中數放入 `content` 或當作本件商品評價。

```bash
cd /Users/etahn/Ethan_file/AutoPersona
python3 products/jlab-open-sport-demo/prepare_open_sport.py
```

此命令以既有 `prepare_contract()` 正規化 `persona-input.v1.json`，產生：

- `listing.v1.json`：正規化後商品資料。
- `field-map.v1.json`：逐欄填寫、選項核對或保留觀測值的建議。
- `questions.v1.json`：缺少資訊及何時需要詢問。未知資料可先保留空白；只在實站要求時集中補問。
- `browser-handoff.json`：單一瀏覽器操作者可直接讀取的標題、文案及欄位值，不含 Persona 研究。
- `title.txt`、`description.txt`：可直接填入商品表單的純文字。
- `research.json`：內部展示與追溯資料。

`confirmed-facts.json` 只存本輪使用者明示答案。`product-facts.json` 存完整規格與左右耳認證 mapping。價格 3990 元、庫存 1 與 2 張圖片已由本輪瀏覽器操作者讀回，保存在 `observed-site-state.json`，保留既有頁面值，不改写為本輪賣家確認。

## 本輪文案與現場規則

標題為「JLab JBuds OPEN SPORT 開放式運動藍牙耳機｜藍牙5.3 IP55」。第一段從父母／照護者希望留意周遭動靜的需求切入，後面完整列出使用者提供規格與商品內容物。Persona 決定文案著重的情境，產品主張來自明示商品資料。

- 不套用舊入耳式推論，也不添加本輪未提供的主動降噪、電子環境音模式或可調耳掛功能。
- IP55 僅標示適用耳機。26 小時為含充電盒合計續航，單耳為 9 小時以上。
- 9.4 g 與 36.8 g 是耳機與充電盒重量，不能拿來填物流包裹重量。
- NCC 保留左耳 `CCAH24LPA380T2` 與右耳 `CCAH24LPA390T5`；若實站欄位僅接受單碼，主欄填左耳，完整左右字號在描述中保留。
- 本輪明示內容物為耳機與 USB-C 充電線，已補入描述及 `compliance.packageContents`。
- 現場售價、庫存及既有 2 張圖保留。圖片角色由主 agent 檢視決定，本資料包不沿用歷史上傳確認旗標。
- 研究的 13 則命中與 Verified Purchase 不進入商品文案，也不推論一定聽見哭聲、警報或照護事件。

表單讀回、存檔／發布結果與操作影片由主 agent 及唯一瀏覽器操作者記錄；`browser-handoff.json` 的存在本身不代表實站操作已完成。
