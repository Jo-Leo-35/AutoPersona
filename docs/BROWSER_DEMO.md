# Persona Engine → 蝦皮：真實 Chrome 展示

第一階段由 Codex 在可見的 Chrome 操作真實賣家中心。Python 負責整理 JSON 與提供本機進度頁；保留的 [Python／Playwright Beta](PYTHON_BETA.md) 是另一個入口。

## 資料、進度與實站結果

展示順序為 Persona → 文案 → 真實頁面 → 待補資訊 → 驗證。商品事實來自本輪已核對的商品資料；Persona 研究只支援定位，不代替品牌、型號、功能或認證證據。

`examples/browser-demo/persona-input.v1.json` 是保留的通用示例，並非每一輪實際販售的商品。新商品應以本輪核對完成的 JSON 與圖片為準。研究命中數、Verified Purchase 與客群標籤留在內部研究欄位，不當成本商品評價。

主流程將進度寫入 `work/browser-demo/session.json`，補答寫入同目錄的 `answers.json`。這些私有檔案不隨 Git 分享。控制室的完成標記只能反映已回報的實際結果；發布結果與商品連結仍須在蝦皮頁面核對。

[2026-09-12 早期觀察紀錄](BROWSER_DEMO_OBSERVATIONS.md) 保存當時的欄位、物流預設與待補狀態。它是歷史快照，不能代替目前 Chrome 的商品內容，也不表示後續輪次已發布成功。

## 啟動與展示

在專案根目錄執行：

```sh
python3 examples/browser-demo/prepare_contract.py \
  examples/browser-demo/persona-input.v1.json \
  --output-dir work/browser-demo/prepared
```

命令生成 normalized JSON、欄位對映與通用缺漏清單，不讀取 AI 設定、不開啟瀏覽器。實際操作由 Codex 接手，依當前頁面挑選必要問題，不把整份通用缺漏清單直接詢問使用者。

另開終端機啟動控制室：

```sh
python3 demo-control/server.py --port 8767
```

在 Chrome 開啟 [本機控制室](http://127.0.0.1:8767)。若同埠服務已在執行，可直接沿用。新 clone 尚無 session 時會顯示等待，由 Codex 依 [互動格式](BROWSER_DEMO_INTERACTION.md) 建立第一輪狀態。啟動控制室不會自動開始真實瀏覽器操作。

1. 提供本輪商品 JSON，核對商品事實、Persona 與內部研究的分區。
2. 展示控制室的文案與進度。
3. 切到已保留的真實 Chrome 商品分頁，操作並核對實際欄位。
4. 依實站需要集中補答；在控制室儲存後，回 Codex 對話說「已補好，繼續」。
5. 若本輪包含發布，依既有授權完成核對與送出，再讀取平台結果與商品連結；結果不明時先查商品列表，避免重複建立商品。

## 從對話續接或重跑

同一次展示可在對話中貼上：

> 繼續 AutoPersona 第一階段 Demo。先讀 work/browser-demo/session.json、answers.json（若存在）與 docs/BROWSER_DEMO_OBSERVATIONS.md。沿用已開啟的 Chrome 商品頁，核對頁面與本輪商品資料後繼續。只詢問仍會阻擋下一步的必要資料；若已送出但結果不明，先確認商品列表，避免重複建立。

儲存補答只更新本機檔案，不會自動喚醒已結束的 Codex 對話。不用重開商品頁；重新開啟新增商品網址會得到另一份空白表單，無法恢復原來未儲存的內容。

正式 Persona JSON 可從 `examples/browser-demo/persona-input.template.v1.json` 開始，依 `persona-input.schema.v1.json` 填入本輪資料，保留版本欄位，再執行準備命令。欄位契約見 [JSON 說明](BROWSER_DEMO_CONTRACT.md)。

同輪續接保留 `run_id` 與原 session／answers；只有新商品才建立新輪。若 Chrome 表單已因關閉或過期消失，可根據保存的 JSON 恢復草稿；重新建立前先核對是否已有草稿或商品。

## 錄製真實操作

根目錄 `record_visible_demo.py` 用 macOS 的 `screencapture` 錄下目前可見畫面，再透過 ffmpeg 匯出 30–40 秒 MP4。錄影器不控制 Chrome、不填入 fixture、不呼叫 AI，也不判定發布成功。錄影時保持操作中的 Chrome 在前景。

先安裝錄影依賴，再錄下實際操作：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-video.txt
.venv/bin/python record_visible_demo.py capture \
  --seconds 90 --clicks \
  --output artifacts/raw-visible-demo.mov
```

macOS 需允許執行程式錄製螢幕。`--display 1` 選螢幕，`--rect x,y,width,height` 限定錄製範圍；原片檔名必須尚不存在。錄影不包含音訊，私有原片放在已忽略的 `artifacts/` 或 `work/`。

匯出 36 秒影片：

```sh
.venv/bin/python record_visible_demo.py export \
  --input artifacts/raw-visible-demo.mov \
  --output artifacts/autopersona-visible-demo.mp4 \
  --seconds 36
```

預設把來源片段調整為 36 秒，輸出 1600×900 MP4 與同名 JSON 紀錄。`--start`／`--end` 選來源秒數，`--crop x,y,width,height` 使用來源像素裁切；需要分段剪輯時，使用 `--segments path/to/segments.json`：

```json
[
  {"start": 0, "end": 15, "seconds": 10, "caption": "Persona 與商品文案"},
  {"start": 15, "end": 45, "seconds": 16, "caption": "真實 Chrome 商品欄位操作"},
  {"start": 45, "end": 60, "seconds": 10, "caption": "核對頁面結果"}
]
```

片段時間須落在實際原片範圍，總長 30–40 秒。可為各片段設定 `crop` 與 `redactions`；遮罩座標依裁切後、縮放前的像素計算。字幕應描述真實畫面，必要時註明等待已加速；未驗證上架就不寫完成。分享前檢查帳號名稱、通知與私人資訊，並確認影片中的結果與平台一致。

舊的 `record_demo.py` 保留為 **legacy local fixture** 錄影器，僅記錄本機模擬賣場；使用方式見 [Python Beta 錄影入口](PYTHON_BETA.md#錄影入口)。

## 開發與驗證

```sh
.venv/bin/python -m unittest discover -s tests_python -v
.venv/bin/python -m unittest discover -s examples/browser-demo -p 'test_*.py' -v
node --test
```

Python 瀏覽器測試操作本機 fixture；它們驗證邏輯與續接，不能當成真實蝦皮發布成功的證據。`.env`、`work/`、`.autopersona/`、`artifacts/` 與瀏覽器登入 profile 均排除於 Git。第一階段不需要額外 AI API 呼叫。

[上架 Skill](../.codex/skills/autopersona-listing/SKILL.md) 已整理可見 Chrome、Python 快跑、補答續接、錄影與保存核對。原始檔位於 `.codex/skills`，由 `.agents/skills` 的相對連結供 Codex 載入；每次仍需依當前頁面確認。
