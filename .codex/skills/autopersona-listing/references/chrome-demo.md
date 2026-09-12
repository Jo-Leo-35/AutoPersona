# 可見 Chrome 與錄影

使用 Codex 當前可用的瀏覽器工具，依工具文件取得現有蝦皮商品分頁。不要同時啟動 Python 操作相同商品。目標入口為 `https://seller.shopee.tw/portal/product`；有已確認商品 ID 時續接該商品。

## 快速重播

1. 查看目前頁面與登入狀態，將商品頁切到使用者看得到的前景視窗。使用者要求全螢幕時切成全螢幕。
2. 讀取本輪 `browser-handoff.json` 或已確認 listing。以新取得的欄位定位批次填寫標題、認證及其他已知欄位，避免逐字輸入與不必要停頓。
3. Quill 商品描述需要完整取代：聚焦編輯區、全選、刪除、貼上純文字，核對字數與完整內容。自訂屬性新增後，確認選項已選取。
4. 價格／庫存有本輪新值才輸入，否則讀取並保留現場值。輸入後移開焦點，確認沒有阻擋驗證。既有商品在架上用「更新」，已下架用「上架」。依本輪授權送出一次。
5. 等待保存結果，重新開啟同一商品詳情核對。列表總件數可能有快取；不以它作為重新上架成功證據。

瀏覽器工具讀到背景分頁不代表觀眾看得到。原生視窗的選中分頁與商品頁須一致；操作後用實際畫面確認。

## 選用控制室

只有需要 Persona、進度與補答展示時，才執行或沿用：

```sh
python3 demo-control/server.py --port 8767
```

`http://127.0.0.1:8767` 只展示進度與保存補答，不操作 Chrome，也不自動喚醒 Codex。先讀 `docs/BROWSER_DEMO_INTERACTION.md` 與目前 `work/browser-demo/session.json`；同輪保留 `run_id`，讀取匹配的答案，由單一寫入者原子更新狀態。尚未完成的階段不標完成。這個控制室不能接收 Python Beta 的工作流 API。

## 錄影

使用者已開始自行錄影時，直接操作，不再另開錄影器或反覆詢問時機。若要求 Codex 錄製，依 `record_visible_demo.py --help` 與 `docs/BROWSER_DEMO.md` 的 capture/export 用法執行。

- macOS 原生 capture 使用絕對輸出路徑與有限時長；等到自然結束並確認檔案。提早中斷 `screencapture` 可能使影片遺失。
- 全螢幕 Demo 以賣家頁為主，其他控制頁只有在需要該場景時切換。
- 分享前核對影片可解碼、時長與抽樣畫面，處理不適合分享的帳號資訊。
- 原始操作片段與保存結果巡覽分開標示；不能把巡覽剪成看似錄到了原始提交。
- `record_demo.py` 僅錄本機 fixture，不能作為真實蝦皮上架證據。

目前 OPEN SPORT 的真實操作與影片範圍記錄在 `docs/OPEN_SPORT_BROWSER_RUN.md`、`docs/OPEN_SPORT_DEMO.md`。
