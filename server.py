# -*- coding: utf-8 -*-
"""
寵物友善地圖服務後端 (Zero-dependency Python Backend)
提供：
- 靜態檔案伺服 (相容前端 SPA)
- API: 使用者上傳新增餐廳 (/api/upload)
- API: 社群回報店家歇業或資訊錯誤 (/api/report)
- API: 審核與驗證 (/api/verify)
- API: 版本異動歷史與關店清單 (/api/versions)
- 串接 Google Map 導航與快速驗證
"""

import http.server
import socketserver
import json
import os
import sys
import urllib.parse
import datetime

sys.stdout.reconfigure(encoding='utf-8')

PORT = 8088
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JSON_PATH = os.path.join(BASE_DIR, 'data.json')
DATA_JS_PATH = os.path.join(BASE_DIR, 'data.js')
SUBMISSIONS_PATH = os.path.join(BASE_DIR, 'submissions.json')
VERSIONS_PATH = os.path.join(BASE_DIR, 'versions.json')

def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class PetMapHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path
        
        # API: 版本歷史與關店紀錄
        if path == '/api/versions':
            versions = load_json(VERSIONS_PATH, [])
            self.send_json_response(versions)
            return

        # API: 待審核的社群回報與上傳
        if path == '/api/submissions':
            submissions = load_json(SUBMISSIONS_PATH, [])
            self.send_json_response(submissions)
            return

        # API: 即時店家數據 (含最新營運狀態)
        if path == '/api/places':
            places = load_json(DATA_JSON_PATH, [])
            self.send_json_response(places)
            return

        # 預設靜態檔案服務
        return super().do_GET()

    def do_POST(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            body = json.loads(post_data) if post_data else {}
        except Exception:
            body = {}

        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        # 1. 使用者上傳新增寵物友善店家
        if path == '/api/upload':
            if not body.get('name') or not body.get('city') or not body.get('address'):
                self.send_json_response({'success': False, 'message': '請完整填寫店名、縣市與地址！'}, status=400)
                return

            submissions = load_json(SUBMISSIONS_PATH, [])
            sub_id = f"sub-{len(submissions)+1}"
            
            # 若無輸入座標，以預設或概略座標暫代
            lat = float(body.get('lat') or 24.1437)
            lng = float(body.get('lng') or 120.6622)

            new_submission = {
                'id': sub_id,
                'type': 'new_store',
                'name': body['name'],
                'legalName': body.get('legalName', body['name']),
                'category': body.get('category', '特色餐廳'),
                'city': body['city'],
                'district': body.get('district', ''),
                'address': body['address'],
                'phone': body.get('phone', ''),
                'lat': lat,
                'lng': lng,
                'petsAllowed': body.get('petsAllowed', ['犬', '貓']),
                'rules': body.get('rules', ['牽繩可落地']),
                'features': body.get('features', ['社群推薦友善空間']),
                'submitter': body.get('submitter', '熱心毛爸媽'),
                'note': body.get('note', ''),
                'googleMapUrl': body.get('googleMapUrl', ''),
                'status': 'pending_review', # pending_review -> approved -> merged
                'createdAt': now_str,
                'votes': 1
            }

            submissions.insert(0, new_submission)
            save_json(SUBMISSIONS_PATH, submissions)

            self.send_json_response({
                'success': True,
                'message': '感謝推薦！店家已成功提交進入「社群檢驗審核隊列」，管理員或社群驗證後將立即納入正式地圖與版本更新日誌！',
                'submission': new_submission
            })
            return

        # 2. 使用者回報店家已歇業或資訊錯誤
        if path == '/api/report':
            target_id = body.get('targetPlaceId')
            report_type = body.get('reportType', 'closed') # 'closed', 'rule_change', 'phone_error'
            reason = body.get('reason', '')
            
            if not target_id:
                self.send_json_response({'success': False, 'message': '缺少目標店家 ID'}, status=400)
                return

            submissions = load_json(SUBMISSIONS_PATH, [])
            report_id = f"rep-{len(submissions)+1}"
            
            new_report = {
                'id': report_id,
                'type': 'report_closed' if report_type == 'closed' else 'report_info_change',
                'targetPlaceId': target_id,
                'targetName': body.get('targetName', ''),
                'reportType': report_type,
                'reason': reason,
                'reporter': body.get('reporter', '熱心回報者'),
                'proofUrl': body.get('proofUrl', ''),
                'verified': False,
                'createdAt': now_str
            }

            submissions.insert(0, new_report)
            save_json(SUBMISSIONS_PATH, submissions)

            self.send_json_response({
                'success': True,
                'message': '回報已收到！我們將比對 Google Maps 營運狀態並於下一次自動版本更新中標記已歇業。',
                'report': new_report
            })
            return

        # 3. 審核通過並觸發自動發布版本
        if path == '/api/verify':
            sub_id = body.get('submissionId')
            action = body.get('action', 'approve') # 'approve' or 'reject'
            
            submissions = load_json(SUBMISSIONS_PATH, [])
            found = False
            for s in submissions:
                if s.get('id') == sub_id:
                    found = True
                    if action == 'approve':
                        s['status'] = 'approved_pending_merge'
                        s['verified'] = True
                    else:
                        s['status'] = 'rejected'
                    break
                    
            if not found:
                self.send_json_response({'success': False, 'message': '找不到該回報紀錄'}, status=404)
                return
                
            save_json(SUBMISSIONS_PATH, submissions)
            
            # 觸發自動更新腳本
            import subprocess
            subprocess.run([sys.executable, os.path.join(BASE_DIR, 'check_stores_google_maps.py')])

            self.send_json_response({
                'success': True,
                'message': f'審核成功 ({action})！已自動更新資料庫並發布新版本！'
            })
            return

        self.send_json_response({'error': 'Not Found'}, status=404)

    def send_json_response(self, data, status=200):
        response_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), PetMapHandler) as httpd:
        print(f"🚀 全台寵物友善地圖服務 (含上傳、檢驗、版本追蹤 API) 啟動於 http://localhost:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服務停止。")

if __name__ == '__main__':
    run_server()
