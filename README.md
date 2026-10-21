# 台灣毛孩趴趴走・全台寵物友善地圖 🐾
### （支援使用者上傳、社群檢驗審核、Google Maps 自動串接與關店版本追蹤）

專為全台毛爸媽設計的現代化**寵物友善空間平台**。除了完整同步**臺中市動保處 186 處官方認證空間**與臺北市動保處 248 處認證店家外，更全面具備**使用者上傳**、**社群回報檢驗**、**Google Maps 營運動態自動檢驗**與**關店異動版本歷史追蹤 (Version Changelog)**！

---

## 🌟 四大進階升級核心架構

```
┌────────────────────────────────────────────────────────────────────────┐
│                        毛孩趴趴走 自動化閉環體系                         │
├─────────────────┬──────────────────────┬───────────────────────────────┤
│ 1. 使用者上傳   │ 2. 社群檢驗與審核    │ 3. Google Maps 自動檢驗更新   │
│ • 線上表單提交  │ • 群眾回報規範異動   │ • Google Places API 自動掃描  │
│ • 規範與照片備註│ • 一鍵回報已歇業門市 │ • 辨識 OPERATIONAL vs CLOSED  │
│ • Google 地圖   │ • 管理員/社群多重審核│ • 自動發布新 Version Changelog│
└─────────────────┴──────────────────────┴───────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. 版本異動日誌 (Version Changelog)                                     │
│ • 每個版本自動公告：哪些店家已關店 (🔴 已永久歇業)、哪些是新審核上線 (🟢) │
│ • 地圖即時連動：已歇業店家自動灰階標註，可勾選「隱藏已歇業」維持最新清單│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 核心模組與功能說明

### 1. 讓人上傳與推薦（Crowdsourced Upload）
* 點擊頂端 **「➕ 推薦/上傳店家」** 按鈕，彈出結構化表單。
* 填寫：店名、縣市行政區、門市地址、電話、允許寵物種類（犬、貓、大型犬、特寵）及友善規範（牽繩落地、禮貌帶、寵物餐、水碗、草坪）。
* 支援 **「Google 地圖一鍵驗證」**，在提交前先預覽 Google Maps 門市地標。
* 提交後寫入 `submissions.json` 進入檢驗審核隊列。

### 2. 檢驗與回報機制（Verification & Reporting）
* 每張店家卡片與詳情彈窗皆提供 **「⚠️ 回報歇業/錯誤」** 按鈕。
* 民眾可即時通報：
  - 店家已永久停業或搬遷
  - 友善規範變更（例如原可落地改為需推車）
  - 電話或門牌地址有誤

### 3. 自動更新與關店版本追蹤（Auto-audit & Version Changelog）
* 執行自動化檢驗程式：`python check_stores_google_maps.py [GOOGLE_API_KEY]`
* 運作邏輯：
  1. 自動讀取資料庫與待審核回報。
  2. 串接 Google Places API 檢查店家 `business_status`：
     - 若為 `CLOSED_PERMANENTLY`（永久停業），系統自動標記為 `CLOSED_PERMANENTLY`。
     - 若為 `CLOSED_TEMPORARILY`，標記為暫時停業。
  3. 自動遞增版本號（如 `v1.2.0` -> `v1.3.0`），產生結構化版本歷史紀錄：
     - **🔴 經自動檢驗已關店門市清單**（明確記錄店名、所在縣市、關店原因）
     - **🟢 本版本新審核上線店家**
  4. 自動同步編譯最新版 `data.json` 與 `data.js`，讓地圖使用者立即看到最新營運動態！

### 4. 自動串接 Google Map
* **門市導航**：每家餐廳皆可一鍵呼叫 Google Maps 進行即時導航規劃。
* **Google Places API 自動查核**：可自動取得 Google 評分、Place ID 及最新營業時間。

---

## 💻 快速啟動與使用指南

### 啟動完整後端 API 與前端地圖服務
專案目錄中已內建輕量化後端伺服器（零外部套件依賴，標準 Python 即可執行）：
```bash
python C:\Users\HP\.gemini\antigravity\scratch\taiwan-pet-friendly-map\server.py
```
* **瀏覽器直接開啟**：[**http://127.0.0.1:8088/**](http://127.0.0.1:8088/)
* **測試手動執行 Google Maps 營運動態自動檢測**：
```bash
python check_stores_google_maps.py
# 若有 Google Cloud Places API Key 可帶入參數自動聯網比對：
# python check_stores_google_maps.py YOUR_GOOGLE_PLACES_API_KEY
```

---

## 📁 檔案架構

```
taiwan-pet-friendly-map/
├── index.html                  # 完整現代化前端 (含上傳、回報、版本日誌彈窗)
├── server.py                   # 零依賴 Python API 後端 (提供靜態服務與 REST API)
├── check_stores_google_maps.py # Google Maps 狀態自動檢驗與版本日誌生成腳本
├── data.js                     # 編譯後免跨域資料庫 (含歷史版本 PET_MAP_VERSIONS)
├── data.json                   # 結構化主資料庫 (含各店家 status 營運狀態)
├── versions.json               # 版本異動歷史紀錄 (記錄每次更新關閉哪間店、新增哪間店)
├── submissions.json            # 社群上傳與回報檢驗待審核隊列
├── build_database.py           # 臺中官方與全台數據抓取編譯器
├── start_map.bat               # Windows 一鍵啟動批次檔
└── README.md                   # 專案詳細說明與架構手冊
```
