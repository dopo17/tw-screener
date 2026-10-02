# 台股關鍵點篩選器：每日自動更新

每個交易日收盤後，自動下載上市＋上櫃行情與加權指數，累積成 `data/history.csv`，
再把資料嵌進篩選頁面，更新成 `docs/index.html`。你只要打開網址，不用再手動匯入 CSV。

## 設定（一次就好）
1. 在 GitHub 建立一個 **public** repo，把這個資料夾的檔案全部上傳（包含隱藏的 `.github`）。
2. Settings → Pages → Source 選 `Deploy from branch`，Branch 選 `main`、資料夾選 `/docs`。
3. Actions → `daily-update` → Run workflow。
   - 第一次建議先把天數填 `5` 試跑，確認證交所與櫃買的資料抓得到。
   - 沒問題再用預設 `150` 回補（約 15～20 分鐘）。
4. 之後每週一到週五台灣時間 16:30 自動更新。網址：`https://<你的帳號>.github.io/<repo 名稱>/`

## 不用 GitHub，在自己電腦跑
`python update_data.py && python build_site.py`，用排程（Windows 工作排程器或 cron）每天收盤後執行，再開啟 `docs/index.html`。

## 注意
- 資料是公開行情，沒有你的資金或部位；public repo 任何人都看得到這個網頁。
- 價格沒有還原除權息，除息日會有跳空，可能影響當天的訊號。
- 只收 4 位數代號的股票（排除 ETF、權證）；篩選頁只納入 20 日均量 ≥ 500 張的股票，可在 `build_site.py` 調整。
- 證交所、櫃買的網頁 API 格式若改版，要修 `update_data.py` 裡的 `quotes()`。
