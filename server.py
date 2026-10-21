# -*- coding: utf-8 -*-
"""
全台寵物友善餐廳地圖 - 後端服務 (Pet Map Backend Server)
功能：
- 靜態檔案服務 (HTML/JS/CSS)
- 意見回饋 API: GET /api/feedback, POST /api/feedback
- 推薦與上傳 API: POST /api/upload (經由 AI 後台審核)
- 歇業與錯誤回報 API: POST /api/report (經由 AI 後台審核)
- 自動更新 API: POST /api/auto-update (AI 批量審核、合併入庫、版本遞增、自動 git push)
- 版本歷史查詢 API: GET /api/versions
- 審核隊列查詢 API: GET /api/submissions
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

        # 3. API: 旅人回饋意見清單
        if path == '/api/feedback':
            feedbacks = load_json(FEEDBACK_PATH, [])
            self.send_json_response(feedbacks)
            return

        # 4. API: 即時店家數據
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

        # 1. 使用者提交回饋意見 (/api/feedback)
        if path == '/api/feedback':
            user_name = body.get('userName', '毛孩旅人').strip()
            comment = body.get('comment', '').strip()
            if not comment:
                self.send_json_response({'success': False, 'message': '請填寫意見回饋內容！'}, status=400)
                return

            feedbacks = load_json(FEEDBACK_PATH, [])
            new_feedback = {
                'id': f"fb-{len(feedbacks) + 1}",
                'userName': user_name or '熱心毛孩爸媽',
                'targetPlace': body.get('targetPlace', '全台寵物友善地圖'),
                'rating': int(body.get('rating', 5)),
                'category': body.get('category', '友善體驗心得'),
                'comment': comment,
                'petType': body.get('petType', '毛孩小夥伴'),
                'date': now_str,
                'likes': 0
            }
            feedbacks.insert(0, new_feedback)
            save_json(FEEDBACK_PATH, feedbacks)
            
            # 更新 data.js 的 window.PET_MAP_FEEDBACKS
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
                'message': '感謝您的寶貴回饋！意見已成功發布於旅人回饋區。',
                'feedback': new_feedback
            })
            return

        # 2. 推薦新增餐廳 (/api/upload) -> 經 AI 後台即時審核
        if path == '/api/upload':
            if not body.get('name') or not body.get('city') or not body.get('address'):
                self.send_json_response({'success': False, 'message': '請完整填寫店名、縣市與門牌地址！'}, status=400)
                return

            submissions = load_json(SUBMISSIONS_PATH, [])
            sub_id = f"sub-{len(submissions)+1}"
            
            lat = float(body.get('lat') or 24.1437)
            lng = float(body.get('lng') or 120.6622)

            submission_payload = {
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
                'features': body.get('features', ['社群推薦友善餐廳']),
                'submitter': body.get('submitter', '熱心毛孩爸媽'),
                'note': body.get('note', ''),
                'website': body.get('website', ''),
                'facebook': body.get('facebook', ''),
                'instagram': body.get('instagram', ''),
                'googleMapUrl': body.get('googleMapUrl', ''),
                'createdAt': now_str
            }

            # 呼叫 AI 後台審核模組
            audited_sub, ai_audit_res = audit_submission(submission_payload)
            submissions.insert(0, audited_sub)
            save_json(SUBMISSIONS_PATH, submissions)

            self.send_json_response({
                'success': True,
                'aiVerdict': ai_audit_res['verdict'],
                'aiConfidence': ai_audit_res['confidence'],
                'aiReasoning': ai_audit_res['reasoning'],
                'submission': audited_sub,
                'message': f"【AI 審核完成：{ai_audit_res['verdict']}】{ai_audit_res['reasoning']}"
            })
            return

        # 3. 社群回報店家已歇業或資訊有誤 (/api/report) -> 經 AI 後台審核
        if path == '/api/report':
            target_id = body.get('targetPlaceId')
            report_type = body.get('reportType', 'closed')
            reason = body.get('reason', '')
            
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
                'reporter': body.get('reporter', '熱心毛爸媽'),
                'proofUrl': body.get('proofUrl', ''),
                'createdAt': now_str
            }

            audited_report, ai_audit_res = audit_submission(report_payload)
            submissions.insert(0, audited_report)
            save_json(SUBMISSIONS_PATH, submissions)

            self.send_json_response({
                'success': True,
                'aiVerdict': ai_audit_res['verdict'],
                'aiConfidence': ai_audit_res['confidence'],
                'aiReasoning': ai_audit_res['reasoning'],
                'report': audited_report,
                'message': f"【AI 審核完成：{ai_audit_res['verdict']}】{ai_audit_res['reasoning']}"
            })
            return

        # 4. 觸發 AI 自動審核與版本更新 (/api/auto-update)
        if path == '/api/auto-update':
            auto_git = body.get('gitPush', True)
            try:
                update_result = run_auto_update(auto_git_push=auto_git)
                self.send_json_response({
                    'success': True,
                    'result': update_result,
                    'message': f"🎉 自動更新成功！已生成新版本 {update_result['version']}，同步維護全台純餐廳 {update_result['totalStores']} 家！"
                })
            except Exception as e:
                self.send_json_response({
                    'success': False,
                    'message': f"自動更新執行失敗：{str(e)}"
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
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), PetMapHandler) as httpd:
        print(f"🚀 全台純寵物友善餐廳地圖服務 (含 AI 後台審核、意見回饋、版本自動發布) 啟動於 http://localhost:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服務停止。")

if __name__ == '__main__':
    run_server()
