@echo off
chcp 65001 >nul
echo ========================================================
echo  台灣毛孩趴趴走・全台寵物友善餐廳地圖
echo  (收錄臺中市動保處 186 處官方認證與全台 485+ 友善空間)
echo ========================================================
echo.
echo 正在開啟瀏覽器地圖服務...
start http://localhost:8088/
if errorlevel 1 (
    start "" "%~dp0index.html"
)
echo.
echo 若尚未啟動本機伺服器，您也可以直接以瀏覽器開啟 index.html。
echo.
pause
