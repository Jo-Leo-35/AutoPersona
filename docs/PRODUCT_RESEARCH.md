# JBuds OPEN SPORT 商品資料與來源

目前正式商品為 **JLab JBuds OPEN SPORT 開放式運動藍牙耳機**。使用者已明確提供型號、規格、價格 NT$3,990 與庫存 1；已核對[台灣代理該型號商品頁](https://store.igogosport.com/products/jlab-jbuds-open-sport)的產品特色、商品規格與左右耳字號，內容吻合。這項明確來源已取代先前根據低資訊圖片作出的入耳式推論，候選研究已停止。

本文件對應可重建資料與既有商品 `43834400022` 的欄位交接，不以本地生成結果宣稱遠端保存成功。

## 有效欄位與來源

| 欄位 | 目前值 | 來源與用途 |
| --- | --- | --- |
| 品牌／型號 | JLab／JLab JBuds OPEN SPORT 開放式運動藍牙耳機 | 使用者提供，代理型號頁核對吻合 |
| 價格 | NT$3,990 | 使用者「價格是3990」；不套用來源零售價 |
| 庫存 | 1 | 使用者明確提供；不套用來源零售庫存 |
| 耳機類型 | 開放式 | 實站新增並選取的選項；來源另記 `browser_observed` |
| 連接 | 無線、Bluetooth 5.3 | 使用者規格與代理正文 |
| NCC 左耳 | CCAH24LPA380T2 | 使用者提供且代理該型號段落吻合；填入 NCC 主欄 |
| NCC 右耳 | CCAH24LPA390T5 | 使用者提供且代理該型號段落吻合；與左耳一併放商品描述 |
| BSMI | R3B170 | 使用者提供且代理該型號段落吻合 |
| 商品狀況 | Canonical JSON 保留 `null` | 既有頁觀測為全新，交接要求沿用該頁值；不冒充使用者確認，也不因此再提問 |

實站 NCC 欄只接受單碼；雙碼曾觸發格式錯誤。因此 `compliance.nccNumber` 是左耳單碼，`browser-handoff.json.certificationEarMapping`、`product-facts.json.certifications.ncc` 與商品描述保留左右耳完整標記。這是已觀測表單限制的對映，不是漏除右耳認證。

認證狀態為 `user_provided_matched_taiwan_distributor_product_page`，已清除原型號／證號不一致 blocker。尚未聲稱完成獨立政府資料庫查驗。舊 `CCAH24LP3330T0` 只留在明確標示 `superseded` 的歷史記錄，不再是有效欄位。

## 商品規格與文案

使用者提供且代理商品規格正文吻合的資料整理在 `product-facts.json`，包括 14.2 mm 動圈、耳機 IP55、SBC／AAC、HSP／HFP／A2DP／AVRCP、MEMS -38 dB ±1 dB、20 Hz–20 kHz、單耳 9.4 g／盒 36.8 g、單耳 9 小時以上／盒另供 17 小時／總約 26 小時、500 mAh 充電盒、約 2 小時充電與 Type-C。

IP55 僅用於耳機，不能延伸至充電盒。續航保留使用條件限制。來源摘要標題出現 20 小時，但商品特色與規格正文均是 26 小時；本資料採用使用者資料與正文相符的 26 小時。音頻解碼原文附帶的 `(free)` 不轉成贈品或價格主張。来源商店的保固資格、完整配件、售價、库存、物流與退貨條款不自動沿用為這件商品的事實。

最終標題是「JLab JBuds OPEN SPORT 開放式運動藍牙耳機 黑色｜耳掛設計」。完整描述可直接從 `browser-handoff.json.description` 取得，包含開放式設計、可調耳掛、規格與左右耳字號。

Persona 已恢復為需要保持環境感知的父母／照護者，定位是聆聽時保留與家人及周遭互動的日常選擇。這是受眾需求與開放式設計的對應，不是哭聲、警報或照護安全保證。原本 13 則命中、全部 Verified Purchase、Missed Buyer 僅留在 `research`，不當作本商品評論或買家見證。

## 圖片角色

- 使用者要求導入 `demo-0.png` 與 `demo-1.png`；以下兩圖角色是主 agent 根據圖片內容所作配置，不是使用者逐圖指定的角色。
- `demo-1.png`：主 agent 依圖片內容配置為本商品圖。`imagePaths=["demo-1.png"]`，商品確認與上傳授權皆為 `true`，`referenceOnly=false`。
- `demo-0.png`：多品牌合照，只放 `referenceImagePaths`，供內部研究與控制室參考，不能上傳為此 SKU。
- `products/jlab-image-demo/supplied-product.png`：保留最初指定商品圖片來源副本。主 agent 已查看 `demo-1.png` 與指定商品外觀相同；檔案編碼不同，不主張兩者位元完全相同。
- 先前官方候選比對圖留在忽略的 `work/product-research/jlab-candidate-images/`，不進商品媒體集合。

## 可重建來源與交接

- `confirmed-facts.json`：使用者正式答案與各欄來源；重建不能把價格、庫存、型號或新字號抹回未知。
- `product-facts.json`：正式型號規格與左右認證對映。
- `observed-site-state.json`：真實頁面選項、單碼限制、既有全新值與圖片觀测，和使用者確認來源分開。
- `certification-review.json`：有效證號、來源與已解除的阻擋狀態。
- `identity-followup.json`：正式身分結論與舊視覺推論撤回記錄。
- `superseded-research.json`：先前候選與舊證號歷史，整份 `applyToStorefront=false`。
- `prepare_jlab.py`：使用既有 `empty_listing`、`apply_answers`、`normalize_listing` 與問題收集契約離線重建；不讀設定或金鑰、不呼叫付費 API、不操作瀏覽器。

生成結果是 `examples/browser-demo/jlab-image-input.v1.json` 及商品目錄內的 `listing.v1.json`、`field-map.v1.json`、`questions.v1.json`、`research.json`、`browser-handoff.json`。交接頁包含正式文案、資料來源、既有商品 ID、左右耳對映、單碼限制與兩張圖的角色；內部研究不作表單欄位。

`questions.v1.json` 保留 canonical 缺項，另記既有頁觀測。是否提問仍由當下實站需要決定，不把離線清單整批當成新的固定問題。包裝物流資料、保固資格與未確認販售事實繼續留空。生成契約保留 `allowPublish=false`，由主流程根據本次使用者授權處理既有商品操作。

```sh
python3 products/jlab-image-demo/prepare_jlab.py
python3 products/jlab-image-demo/test_jlab.py
```

8 個資料邊界測試涵蓋正式型號與未提供欄位、持久答案、左右 NCC 對映、兩圖角色、Persona 研究隔離、規格限定、舊推論撤回及生成結果一致性。
