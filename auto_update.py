# -*- coding: utf-8 -*-
"""
自動更新發布引擎 (Auto-Updater Engine)
功能：
1. 自動執行 AI 後台審核 (AI Audit Pipeline) 處理待審核的推薦與回報
2. 比對並將審核通過的新增餐廳併入資料庫
3. 標記已歇業門市 (CLOSED_PERMANENTLY)
4. 遞增版本號，產生 Changelog 並存檔 versions.json
5. 同步重新生成 data.json 與 data.js
6. 自動呼叫 git commit & git push origin main，即時發布更新到 GitHub Pages！
"""

import json
import os
import sys
import datetime
import subprocess
from ai_auditor import audit_submission

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JSON_PATH = os.path.join(BASE_DIR, 'data.json')
DATA_JS_PATH = os.path.join(BASE_DIR, 'data.js')
VERSIONS_JSON_PATH = os.path.join(BASE_DIR, 'versions.json')
SUBMISSIONS_JSON_PATH = os.path.join(BASE_DIR, 'submissions.json')

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

def run_auto_update(auto_git_push=True):
    print("==================================================")
    print("🚀 啟動全台寵物友善地圖：AI 自動審核與版本更新流程")
    print("==================================================")
    
    places = load_json(DATA_JSON_PATH, [])
    versions = load_json(VERSIONS_JSON_PATH, [])
    submissions = load_json(SUBMISSIONS_JSON_PATH, [])
    
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    v_next = len(versions) + 1
    version_num = f"v1.{v_next}.0"
    
    new_verified_stores = []
    closed_stores = []
    
    # 1. 執行 AI 審核未審核的 submissions
    print("🤖 正在執行 AI 後台審核佇列...")
    for sub in submissions:
        if not sub.get('aiAudit'):
            sub, audit_res = audit_submission(sub)
            print(f"  - AI 審核 [{sub.get('type')}]: {sub.get('name') or sub.get('targetName')} -> {audit_res['verdict']} ({int(audit_res['confidence']*100)}%)")
            
    # 2. 處理審核通過的項目 (approved_pending_merge)
    for sub in submissions:
        if sub.get('status') == 'approved_pending_merge':
            if sub.get('type') == 'new_store':
                new_id = f"user-{len(places) + 1}"
                new_place = {
                    'id': new_id,
                    'name': sub['name'],
                    'legalName': sub.get('legalName', sub['name']),
                    'category': sub.get('category', '特色餐廳'),
                    'city': sub['city'],
                    'district': sub.get('district', ''),
                    'address': sub['address'],
                    'phone': sub.get('phone', '依現場公告'),
                    'lat': sub['lat'],
                    'lng': sub['lng'],
                    'petsAllowed': sub.get('petsAllowed', ['犬', '貓']),
                    'rules': sub.get('rules', ['牽繩可落地']),
                    'features': sub.get('features', ['社群推薦友善餐廳']),
                    'source': f"AI 審核通過 (社群推薦: {sub.get('submitter', '熱心毛孩爸媽')})",
                    'sourceUrl': sub.get('googleMapUrl', 'https://maps.google.com'),
                    'verified': True,
                    'status': 'OPERATIONAL',
                    'highlight': False,
                    'website': sub.get('website', ''),
                    'facebook': sub.get('facebook', ''),
                    'instagram': sub.get('instagram', ''),
                    'googleMapUrl': sub.get('googleMapUrl', '')
                }
                places.append(new_place)
                sub['status'] = 'merged'
                new_verified_stores.append({
                    'id': new_id,
                    'name': new_place['name'],
                    'city': new_place['city'],
                    'category': new_place['category']
                })
                print(f"  [新餐廳上線] 🟢 {new_place['name']} ({new_place['city']})")

            elif sub.get('type') in ['report_closed', 'report_info_change']:
                target_id = sub.get('targetPlaceId')
                for p in places:
                    if p['id'] == target_id:
                        p['status'] = 'CLOSED_PERMANENTLY'
                        p['statusUpdatedAt'] = now_str
                        sub['status'] = 'merged'
                        closed_stores.append({
                            'id': p['id'],
                            'name': p['name'],
                            'city': p['city'],
                            'status': '已永久停業',
                            'reason': sub.get('reason', '社群查證已歇業')
                        })
                        print(f"  [標記關店] 🔴 {p['name']} ({p['city']}) -> CLOSED_PERMANENTLY")
                        break

    # 3. 記錄版本更新
    active_count = len([p for p in places if p.get('status', 'OPERATIONAL') == 'OPERATIONAL'])
    summary_text = f"純餐飲總計 {len(places)} 家（正常營運 {active_count} 家），本版本 AI 審核新增 {len(new_verified_stores)} 家餐廳，標記 {len(closed_stores)} 家歇業門市。"
    
    version_record = {
        'version': version_num,
        'date': now_str,
        'summary': summary_text,
        'closedStores': closed_stores,
        'newStores': new_verified_stores,
        'totalStores': len(places),
        'activeStores': active_count
    }
    
    versions.insert(0, version_record)
    
    # 4. 存檔 data.json, versions.json, submissions.json, data.js
    save_json(DATA_JSON_PATH, places)
    save_json(VERSIONS_JSON_PATH, versions)
    save_json(SUBMISSIONS_JSON_PATH, submissions)
    
    feedback_data = load_json(os.path.join(BASE_DIR, 'feedback.json'), [])
    
    with open(DATA_JS_PATH, 'w', encoding='utf-8') as f:
        f.write('// 全台寵物友善餐廳資料庫 (含官網/FB/IG/Google Map 連結與最新營運狀態)\n')
        f.write('window.PET_PLACES_DATA = ')
        json.dump(places, f, ensure_ascii=False, indent=2)
        f.write(';\n')
        f.write('window.PET_MAP_VERSIONS = ')
        json.dump(versions, f, ensure_ascii=False, indent=2)
        f.write(';\n')
        f.write('window.PET_MAP_FEEDBACKS = ')
        json.dump(feedback_data, f, ensure_ascii=False, indent=2)
        f.write(';\n')

    print(f"\n✅ 資料庫與 JS 檔案已更新！當前版本：{version_num}")
    
    # 5. Git 自動推送到 GitHub
    git_success = False
    git_msg = ""
    if auto_git_push:
        try:
            print("🚀 正在執行 Git 同步發布到 GitHub Pages...")
            subprocess.run(['git', 'add', '.'], cwd=BASE_DIR, check=True)
            commit_res = subprocess.run(
                ['git', 'commit', '-m', f"auto: AI審核更新發布版本 {version_num} (純餐廳 {len(places)} 家)"],
                cwd=BASE_DIR, capture_output=True, text=True, encoding='utf-8'
            )
            print("Git commit output:", commit_res.stdout.strip())
            push_res = subprocess.run(
                ['git', 'push', 'origin', 'main'],
                cwd=BASE_DIR, capture_output=True, text=True, encoding='utf-8'
            )
            print("Git push output:", push_res.stdout.strip() or push_res.stderr.strip())
            git_success = True
            git_msg = "已成功推送到 GitHub，GitHub Pages 同步更新！"
        except Exception as e:
            git_msg = f"Git 推送略過或有提醒：{e}"
            print("Git 推送提醒:", git_msg)

    return {
        'success': True,
        'version': version_num,
        'date': now_str,
        'activeStores': active_count,
        'totalStores': len(places),
        'newStoresCount': len(new_verified_stores),
        'closedStoresCount': len(closed_stores),
        'summary': summary_text,
        'gitMessage': git_msg
    }

if __name__ == '__main__':
    res = run_auto_update(auto_git_push=True)
    print(res)
