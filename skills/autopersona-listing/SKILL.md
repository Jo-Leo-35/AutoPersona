---
name: autopersona-listing
description: Use AutoPersona to turn Persona Engine JSON and supplied product facts into Shopee seller listings. Supports visible Chrome demos, fast Python runs, incremental answers, and verified saves or relisting. Use for this project's listing workflow, replay, or recording.
---

# AutoPersona 商品上架

將 Persona 洞察轉成商品文案，在使用者看得到的蝦皮賣家中心完成填寫、補答與結果核對。此 Skill 依賴 AutoPersona 專案；先找到包含 `shopee_run.py`、`autopersona_py/` 的專案根目錄。目前位置為 `/Users/etahn/Ethan_file/AutoPersona`，使用者指定的新位置優先。下列程式與資料路徑均相對於專案根目錄。

## 選擇入口

| 使用者需求 | 執行方式 | 需要時讀取 |
| --- | --- | --- |
| 真實畫面 Demo、重播、操作已登入 Chrome | Codex 瀏覽器工具，批次填入已確認欄位 | [Chrome 與錄影](references/chrome-demo.md) |
| 自動化腳本、快速重跑 | `shopee_run.py`，有視窗、預設零延遲 | [Python 快速執行](references/python-run.md) |
| Python 控制台、對話補答 API | `autopersona.py` | [Python 控制台](references/python-dashboard.md) |

沿用使用者選擇的模式。錄 Demo 時縮短說明，讓賣家頁保持前景；不必為展示另外啟動控制室。只有一位操作者控制實際商品頁；若已要求平行分工，其餘 agent 分別處理資料、控制室或文件。

## Persona 與商品資料

- 隊友輸入契約為 `examples/browser-demo/persona-input.schema.v1.json`，範本為同目錄 `persona-input.template.v1.json`，外層包含 `schemaVersion`、`exampleId`、`listing`。用 `prepare_contract.py INPUT --output-dir OUTPUT` 正規化。
- `listing.persona` 決定文案情境；`listing.product`、`compliance` 等提供商品事實；`listing.research` 保存研究依據。13 則命中、Verified Purchase、Missed Buyer 是客群研究，不能寫成本商品評價或性能保證。
- 未知價格、庫存、規格、認證與物流資料維持 `null`。更新同一商品時可保留現場原值，保存後核對；保留數值 `0` 與布林 `false`。只補問實際阻擋操作的資訊。
- 先查看提供的圖片，再決定是否適合作為商品圖；已有圖庫重跑不重複上傳。產品重量不能代替包裹重量。
- OPEN SPORT 範例與來源在 `products/jlab-open-sport-demo/`、`docs/OPEN_SPORT_PERSONA.md`。歷史商品 ID、售價、圖片與已完成記錄不能當作新商品的事實或發布授權。

## 執行與完成條件

沿用同一輪的商品 ID、輸入、已回答資訊與授權。直接執行已獲授權的保存；若發布決定仍缺，先完成可審閱的表單，再問必要問題。範例 JSON 或 Skill 本身不授權發布。

保存後重新開啟同一商品詳情，核對標題、完整描述、必填屬性、認證、圖片數、售價與庫存。重新上架另核對新的詳情頁出現「下架」且無「上架」。按鈕反應、列表跳轉或總數都不足以證明完成。

每輪腳本至多提交一次。結果不明時續接查核同一輪，不重按發布或新建商品；明確驗證失敗且尚未提交時，修正後續接。

Google 若顯示「This browser or app may not be secure」，停止該腳本輪次，改用蝦皮支援的正常登入方式，或在相同任務授權下切到 Codex 操作已登入 Chrome。不要降低瀏覽器安全設定、偽裝自動化或搬移日常 Chrome 的登入憑證。詳細續接方式見 Python 參考。

設定由程式讀取專案 `.env`，支援 `OPENAI_API_KEY`／`GPT-API`；一般 JSON 重播不需要 API。憑證不進入輸入 JSON、畫面或日誌。`work/`、`.autopersona/`、profile、原始錄影保持私有。

結束時簡短說明實際使用的模式與結果：區分本機測試、真實賣家保存、架上狀態與買家下單驗證。若 Python 登入受阻而由 Codex Chrome 完成，不可宣稱 Python 端到端成功。
