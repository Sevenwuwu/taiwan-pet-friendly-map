# 台灣毛孩趴趴走・全台寵物友善餐廳地圖 🐾
### （純餐飲嚴選・AI 後台審核・旅人回饋專區・社群 IG/FB 串接・Google Maps 自動更新發布）

🔗 **線上即時體驗（GitHub Pages）**：[https://sevenwuwu.github.io/taiwan-pet-friendly-map/](https://sevenwuwu.github.io/taiwan-pet-friendly-map/)  
📦 **GitHub 開源倉庫**：[https://github.com/Sevenwuwu/taiwan-pet-friendly-map](https://github.com/Sevenwuwu/taiwan-pet-friendly-map)

---

## 🌟 五大核心升級亮點

### 1. 🍽️ 嚴格剔除非餐廳門市（純餐飲空間嚴選）
* 全面過濾並剔除非餐飲機構：美髮造型沙龍、純住宿旅宿/飯店/民宿、寵物美容用品店、五金家具賣場、客運計程車行、觀光工廠與行政表格標題。
* **保留全台 480+ 家純正寵物友善餐飲空間**（涵蓋早午餐、咖啡館、甜點、義式餐酒館、日式拉麵/居酒屋、火鍋燒肉及特色美食）。

### 2. 💬 毛孩旅人回饋與評價專區（Feedback Zone）
* **旅人經驗分享瀑布流**：顯示家長暱稱、毛孩品種標籤（柴犬、柯基、米克斯、貓咪等）、用餐滿意星級（1~5 星）、心得標籤與真實探店反饋。
* **線上即時發表**：
  - 支援針對特定餐廳撰寫回饋（於店家卡片或詳情點擊「✍️ 評價」自動帶入店名）。
  - 亦可發表全台地圖功能建議。
  - 完整串接 `/api/feedback` 並具備離線暫存機制，GitHub Pages 靜態環境無縫支援。

### 3. 🤖 AI 後台智慧審核引擎（AI Restaurant Auditor）
* 使用者推薦新餐廳 (`/api/upload`) 或回報歇業 (`/api/report`) 時，自動觸發 `ai_auditor.py`：
  - **餐飲性質檢驗**：自動比對餐飲關鍵字與非餐飲黑名單，嚴格杜絕沙龍、旅店與用品店混入。
  - **地理門牌合法性**：檢驗台灣 22 縣市行政區、路街段與門牌號結構，驗證經緯度在台灣有效範圍內。
  - **寵物友善合理性**：檢驗牽繩、提籠、推車、水碗與寵物餐等規範。
  - **AI 即時判決**：產出 `APPROVED` / `NEEDS_MANUAL_REVIEW` / `REJECTED`、信心分數與詳細中文審核說明。審核通過之店家自動排入版本更新佇列！

### 4. ⚡ 一鍵與排程自動更新發布（Auto-Update & Git Push）
* 支援前端按鈕 **「⚡ AI 自動更新」** 或後端 CLI 執行 `python auto_update.py`。
* **全自動化流水線**：
  1. 🤖 執行 AI 後台佇列審核。
  2. 🗺️ 比對 Google Maps 營運動態與歇業回報，標記關店門市 (`CLOSED_PERMANENTLY`)。
  3. 📦 合併審核通過的餐廳入庫，自動遞增版本號（如 `v1.4.0` -> `v1.5.0`）並生成 Changelog。
  4. 🚀 **自動執行 `git commit` 與 `git push origin main`**，GitHub Pages 於數秒內全網同步發布上線！

### 5. 🌐 每家餐廳皆具備四大社群與定位外連
* 📍 **Google Maps 定位與即時導航**：一鍵開啟手機 Google 地圖 App 或網頁版規劃路線。
* 📸 **Instagram 探店打卡標籤**：一鍵查看 IG 上的網友實拍美照、菜單與毛孩打卡動態。
* 📘 **Facebook 官方粉專搜尋**：快速查詢店家最新公休公告與私訊訂位。
* 🌐 **官方網站 / 訂位連結**：快速瀏覽完整菜單與門市資訊。

---

## 🏗️ 系統運作架構圖

```
┌────────────────────────────────────────────────────────────────────────┐
│                        全台寵物友善地圖 自動化閉環體系                   │
├─────────────────┬──────────────────────┬───────────────────────────────┤
│ 1. 前端社群推薦 │ 2. AI 後台智慧審核   │ 3. 自動更新與 GitHub 同步     │
│ • 推薦純餐飲店家│ • 餐飲屬性深度驗證   │ • Google Maps 營運比對 (關店) │
│ • 旅人意見與評分│ • 門牌與地理座標校驗 │ • 版本號遞增與 Changelog 產出  │
│ • 店家歇業回報  │ • 自動補全 IG/FB/定位│ • 自動 git commit & git push   │
└─────────────────┴──────────────────────┴───────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. 成果即時發布                                                        │
│ • GitHub Pages 靜態網站自動重新構建上線                                  │
│ • 本地 Python 輕量服務即時更新 (http://localhost:8088/)                 │
│ • 地圖自動更新餐廳狀態，已歇業店家標示灰階或隱藏                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 💻 本地啟動與操作指南

### 1. 啟動本機伺服器
```bash
cd C:\Users\HP\.gemini\antigravity\scratch\taiwan-pet-friendly-map
python server.py
```
啟動後瀏覽器開啟：[**http://localhost:8088/**](http://localhost:8088/)

### 2. 手動觸發 AI 自動審核與發布更新
```bash
python auto_update.py
```

---

## 📁 專案檔案結構

```
taiwan-pet-friendly-map/
├── index.html                  # 現代化響應式前端 (含地圖、社群按鈕、回饋專區、AI審核彈窗)
├── server.py                   # 零依賴 Python 後端 (提供靜態服務與完整 RESTful API)
├── ai_auditor.py               # AI 後台智慧審核引擎 (餐飲屬性/地址校驗/社群連結補全)
├── auto_update.py              # 自動更新發布引擎 (AI 審核合併/關店標記/版本遞增/git push)
├── check_stores_google_maps.py # Google Maps 狀態查核輔助腳本
├── data.js                     # 編譯後前端免跨域資料庫 (含 PET_PLACES_DATA, VERSIONS, FEEDBACKS)
├── data.json                   # 480+ 家純正寵物友善餐廳主資料庫
├── feedback.json               # 旅人回饋心得與星級評價資料庫
├── versions.json               # 完整版本歷史與歇業/新上線門市 Changelog
├── submissions.json            # 待審核與已合併之社群回報/推薦隊列
└── README.md                   # 系統技術文件與架構說明手冊
```
