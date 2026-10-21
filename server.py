# -*- coding: utf-8 -*-
"""
全台寵物友善餐廳地圖 - 後端服務 (Pet Map Backend Server)
功能：
- 靜態檔案服務 (HTML/JS/CSS)
- 網站意見回饋 API: GET /api/feedback, POST /api/feedback (給本網站工具的回饋，無假資料)
- 推薦新餐廳 API: POST /api/upload (經由後台審核隊列，供管理員至 Google Maps 查驗)
- 歇業與錯誤回報 API: POST /api/report
- 管理員審核 API: POST /api/verify (管理員在 Google Maps 查驗後進行核准/駁回)
- 版本自動更新與同步 API: POST /api/auto-update (管理員專用：合併入庫、版本遞增、自動 git push)
- 版本歷史查詢 API: GET /api/versions
- 待審核清單 API: GET /api/submissions
- 餐廳即時資料 API: GET /api/places
"""

import http.server
import socketserver
import json
import os
import sys
import urllib.parse
import datetime
from ai_auditor import audit_submission
from auto_update import run_auto_update

sys.stdout.reconfigure(encoding='utf-8')

PORT = 8088
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JSON_PATH = os.path.join(BASE_DIR, 'data.json')
DATA_JS_PATH = os.path.join(BASE_DIR, 'data.js')
SUBMISSIONS_PATH = os.path.join(BASE_DIR, 'submissions.json')
VERSIONS_PATH = os.path.join(BASE_DIR, 'versions.json')
FEEDBACK_PATH = os.path.join(BASE_DIR, 'feedback.json')

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
    protocol_version = "HTTP/1.1"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path
        
        # 1. API: 版本歷史與關店紀錄
        if path == '/api/versions':
            versions = load_json(VERSIONS_PATH, [])
            self.send_json_response(versions)
            return

        # 2. API: 待審核的社群回報與上傳
        if path == '/api/submissions':
            submissions = load_json(SUBMISSIONS_PATH, [])
            self.send_json_response(submissions)
            return

        # 3. API: 網站意見回饋清單 (針對地圖網站本身的使用建議)
        if path == '/api/feedback':
            feedbacks = load_json(FEEDBACK_PATH, [])
            self.send_json_response(feedbacks)
            return

        # 4. API: 即時店家數據 (純餐飲)
        if path == '/api/places':
            places = load_json(DATA_JSON_PATH, [])
            self.send_json_response(places)
            return

        # 預設靜態檔案服務 (支援 index.html, admin.html, data.js 等)
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

        # 1. 提交「網站意見回饋」 (/api/feedback) - 給網站的體驗與功能建議
        if path == '/api/feedback':
            user_name = body.get('userName', '訪客').strip()
            comment = body.get('comment', '').strip()
            if not comment:
                self.send_json_response({'success': False, 'message': '請填寫意見回饋內容！'}, status=400)
                return

            feedbacks = load_json(FEEDBACK_PATH, [])
            new_feedback = {
                'id': f"fb-{len(feedbacks) + 1}",
                'userName': user_name or '訪客',
                'category': body.get('category', '網站使用體驗'),
                'rating': int(body.get('rating', 5)),
                'comment': comment,
                'date': now_str
            }
            feedbacks.insert(0, new_feedback)
            save_json(FEEDBACK_PATH, feedbacks)
            
            # 同步至 data.js
            places = load_json(DATA_JSON_PATH, [])
            versions = load_json(VERSIONS_PATH, [])
            with open(DATA_JS_PATH, 'w', encoding='utf-8') as f:
                f.write('// 全台寵物友善餐廳資料庫\n')
                f.write('window.PET_PLACES_DATA = ')
                json.dump(places, f, ensure_ascii=False, indent=2)
                f.write(';\n')
                f.write('window.PET_MAP_VERSIONS = ')
                json.dump(versions, f, ensure_ascii=False, indent=2)
                f.write(';\n')
                f.write('window.PET_MAP_FEEDBACKS = ')
                json.dump(feedbacks, f, ensure_ascii=False, indent=2)
                f.write(';\n')

            self.send_json_response({
                'success': True,
                'message': '感謝您的寶貴回饋！意見已成功送達。',
                'feedback': new_feedback
            })
            return

        # 2. 推薦新增餐廳 (/api/upload) -> 進入待審核隊列，建立 Google Maps 查驗連結
        if path == '/api/upload':
            name = body.get('name', '').strip()
            city = body.get('city', '').strip()
            address = body.get('address', '').strip()

            if not name or not city or not address:
                self.send_json_response({'success': False, 'message': '請完整填寫店名、縣市與門牌地址！'}, status=400)
                return

            submissions = load_json(SUBMISSIONS_PATH, [])
            sub_id = f"sub-{len(submissions)+1}"
            
            lat = float(body.get('lat') or 24.1437)
            lng = float(body.get('lng') or 120.6622)

            # 社群連結：只有使用者有填寫才保留，不自動塞假資料
            website = body.get('website', '').strip()
            facebook = body.get('facebook', '').strip()
            instagram = body.get('instagram', '').strip()

            google_map_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(name + ' ' + address)}"

            submission_payload = {
                'id': sub_id,
                'type': 'new_store',
                'name': name,
                'legalName': body.get('legalName', name).strip(),
                'category': body.get('category', '特色餐廳'),
                'city': city,
                'district': body.get('district', '').strip(),
                'address': address,
                'phone': body.get('phone', '').strip(),
                'lat': lat,
                'lng': lng,
                'petsAllowed': body.get('petsAllowed', ['犬', '貓']),
                'rules': body.get('rules', ['牽繩可落地']),
                'features': body.get('features', ['友善餐廳']),
                'submitter': body.get('submitter', '訪客推薦').strip(),
                'note': body.get('note', '').strip(),
                'website': website,
                'facebook': facebook,
                'instagram': instagram,
                'googleMapUrl': google_map_url,
                'status': 'pending_review',  # 待管理員至 Google Maps 查證
                'createdAt': now_str
            }

            # 執行後台 AI 初步格式與餐飲性檢核
            audited_sub, ai_audit_res = audit_submission(submission_payload)
            submissions.insert(0, audited_sub)
            save_json(SUBMISSIONS_PATH, submissions)

            self.send_json_response({
                'success': True,
                'submission': audited_sub,
                'message': '感謝您的推薦！店家資料已提交，管理員將於 Google Maps 查驗確認後正式發布入庫。'
            })
            return

        # 3. 社群回報店家歇業 (/api/report)
        if path == '/api/report':
            target_id = body.get('targetPlaceId')
            report_type = body.get('reportType', 'closed')
            reason = body.get('reason', '').strip()
            
            if not target_id:
                self.send_json_response({'success': False, 'message': '缺少目標店家 ID'}, status=400)
                return

            submissions = load_json(SUBMISSIONS_PATH, [])
            report_id = f"rep-{len(submissions)+1}"
            
            report_payload = {
                'id': report_id,
                'type': 'report_closed' if report_type == 'closed' else 'report_info_change',
                'targetPlaceId': target_id,
                'targetName': body.get('targetName', ''),
                'reportType': report_type,
                'reason': reason,
                'reporter': body.get('reporter', '訪客回報').strip(),
                'status': 'pending_review',
                'createdAt': now_str
            }

            audited_report, ai_audit_res = audit_submission(report_payload)
            submissions.insert(0, audited_report)
            save_json(SUBMISSIONS_PATH, submissions)

            self.send_json_response({
                'success': True,
                'report': audited_report,
                'message': '感謝您的守護回報！管理員將比對 Google Maps 營運狀態後進行標記與更新。'
            })
            return

        # 4. 管理員審核店家 (/api/verify) - 以 Google Maps 查核為依據
        if path == '/api/verify':
            sub_id = body.get('submissionId')
            action = body.get('action', 'approve') # 'approve' or 'reject'
            admin_note = body.get('note', '')
            
            submissions = load_json(SUBMISSIONS_PATH, [])
            target = None
            for s in submissions:
                if s.get('id') == sub_id:
                    target = s
                    break
                    
            if not target:
                self.send_json_response({'success': False, 'message': '查無此待審核項目'}, status=404)
                return

            if action == 'approve':
                target['status'] = 'approved_pending_merge'
                target['verified'] = True
                target['adminNote'] = admin_note or 'Google Maps 查證營業中，核准入庫'
            else:
                target['status'] = 'rejected'
                target['verified'] = False
                target['adminNote'] = admin_note or 'Google Maps 查無此店或已永久歇業'

            save_json(SUBMISSIONS_PATH, submissions)

            self.send_json_response({
                'success': True,
                'message': f"審核成功！項目狀態已更新為：{target['status']}",
                'submission': target
            })
            return

        # 5. 管理員專用：觸發自動更新與發布 (/api/auto-update)
        if path == '/api/auto-update':
            auto_git = body.get('gitPush', True)
            try:
                update_result = run_auto_update(auto_git_push=auto_git)
                self.send_json_response({
                    'success': True,
                    'result': update_result,
                    'message': f"🎉 更新發布成功！當前版本 {update_result['version']}，全台純餐廳共 {update_result['totalStores']} 家！"
                })
            except Exception as e:
                self.send_json_response({
                    'success': False,
                    'message': f"更新執行失敗：{str(e)}"
                }, status=500)
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
    server_address = ("127.0.0.1", PORT)
    with http.server.ThreadingHTTPServer(server_address, PetMapHandler) as httpd:
        print(f"🚀 全台寵物友善餐廳地圖服務 (含後台 Google Maps 審核與網站意見回饋) 啟動於 http://127.0.0.1:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服務停止。")

if __name__ == '__main__':
    run_server()
