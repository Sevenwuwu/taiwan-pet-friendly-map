# -*- coding: utf-8 -*-
"""
Google Maps 營運動態自動檢測與版本更新追蹤腳本
(Google Maps Place Status Auto-Checker & Version Changelog Generator)

支援功能：
1. 串接 Google Places API (Text Search / Place Details) 自動查詢店家是否「營業中 (OPERATIONAL)」或「永久歇業 (CLOSED_PERMANENTLY)」。
2. 無 API Key 時提供智慧檢測模擬與社群回報彙整模式。
3. 自動比對新舊版本資料庫，產生版本更新日誌 (version changelog)，記錄：
   - 🔴 哪些店家已經關店 (永久停業 / 暫停營業)
   - 🟢 哪些店家是最新驗證上線
   - 🟡 哪些店家的友善規則有異動
4. 自動發布新版本 data.json 與 data.js，供地圖前端即時呈現！
"""

import json, os, sys, datetime, urllib.request, urllib.parse, ssl

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

def check_store_google_places(place, api_key=None):
    if not api_key:
        return 'OPERATIONAL', None, None
        
    query = f"{place['name']} {place['address']}"
    url = f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input={urllib.parse.quote(query)}&inputtype=textquery&fields=place_id,name,business_status,rating&key={api_key}"
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'PetMapAutoBot/1.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=5) as r:
            res = json.loads(r.read().decode('utf-8'))
            candidates = res.get('candidates', [])
            if candidates:
                cand = candidates[0]
                status = cand.get('business_status', 'OPERATIONAL')
                place_id = cand.get('place_id')
                rating = cand.get('rating')
                return status, place_id, rating
    except Exception as e:
        print(f"  [API Error] {place['name']}: {e}")
        
    return 'UNKNOWN', None, None

def run_auto_audit_and_update(google_api_key=None):
    print("==================================================")
    print("🚀 啟動全台寵物友善地圖：營運動態檢測與版本自動更新系統")
    print("==================================================")
    
    places = load_json(DATA_JSON_PATH, [])
    versions = load_json(VERSIONS_JSON_PATH, [])
    submissions = load_json(SUBMISSIONS_JSON_PATH, [])
    
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    version_num = f"v1.{len(versions) + 1}.0"
    
    closed_stores = []
    reopened_stores = []
    new_verified_stores = []
    
    print(f"📊 目前資料庫共有 {len(places)} 家店家，開始比對營運狀態...")
    
    # 1. 處理待合併的新增店家 (type == 'new_store')
    new_store_submissions = [
        s for s in submissions 
        if s.get('type') == 'new_store' and s.get('status') == 'approved_pending_merge'
    ]
    for sub in new_store_submissions:
        new_id = f"user-{sub.get('id', len(places)+1)}"
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
            'features': sub.get('features', ['社群推薦友善店家']),
            'source': f"社群審核通過 ({sub.get('submitter', '毛爸媽推薦')})",
            'sourceUrl': sub.get('proofUrl', 'https://maps.google.com'),
            'verified': True,
            'status': 'OPERATIONAL',
            'highlight': False
        }
        places.append(new_place)
        sub['status'] = 'merged'
        new_verified_stores.append({
            'id': new_id,
            'name': new_place['name'],
            'city': new_place['city'],
            'category': new_place['category']
        })
        print(f"  [新上線] 審核通過並納入地圖：{new_place['name']} ({new_place['city']})")

    # 2. 檢測 Google Maps 狀態與已審核通過的歇業回報 (type == 'report_closed')
    reported_closed_map = {}
    for sub in submissions:
        if sub.get('type') == 'report_closed' and sub.get('verified') is True:
            target_id = sub.get('targetPlaceId')
            if target_id:
                reported_closed_map[target_id] = sub.get('reason') or '社群查證已歇業'
                sub['status'] = 'merged'

    for place in places:
        old_status = place.get('status', 'OPERATIONAL')
        
        # Google Places API 檢查
        if google_api_key:
            new_status, place_id, rating = check_store_google_places(place, google_api_key)
            if place_id:
                place['googlePlaceId'] = place_id
            if rating:
                place['googleRating'] = rating
        else:
            if place['id'] in reported_closed_map:
                new_status = 'CLOSED_PERMANENTLY'
            else:
                new_status = old_status

        # 狀態變更紀錄
        if old_status != new_status:
            place['status'] = new_status
            place['statusUpdatedAt'] = now_str
            if new_status in ['CLOSED_PERMANENTLY', 'CLOSED_TEMPORARILY']:
                reason_text = reported_closed_map.get(place['id']) or ('Google Maps 標註已永久停業' if google_api_key else '查驗歇業')
                closed_stores.append({
                    'id': place['id'],
                    'name': place['name'],
                    'city': place['city'],
                    'status': '已永久停業' if new_status == 'CLOSED_PERMANENTLY' else '暫時停業',
                    'reason': reason_text
                })
                print(f"  [標記關店] 🔴 {place['name']} ({place['city']}) -> {new_status} ({reason_text})")
            elif new_status == 'OPERATIONAL' and old_status in ['CLOSED_PERMANENTLY', 'CLOSED_TEMPORARILY']:
                reopened_stores.append({
                    'id': place['id'],
                    'name': place['name'],
                    'city': place['city']
                })
                print(f"  [恢復營業] 🟢 {place['name']} ({place['city']})")

    # 3. 建立版本發布日誌 (Changelog)
    version_record = {
        'version': version_num,
        'date': now_str,
        'summary': f"收錄 {len(places)} 家店家，本版本檢驗標記 {len(closed_stores)} 家歇業門市，新增 {len(new_verified_stores)} 家友善餐廳。",
        'closedStores': closed_stores,
        'reopenedStores': reopened_stores,
        'newStores': new_verified_stores,
        'totalStores': len(places),
        'activeStores': len([p for p in places if p.get('status', 'OPERATIONAL') == 'OPERATIONAL'])
    }
    
    versions.insert(0, version_record)
    
    # 4. 存檔更新
    save_json(DATA_JSON_PATH, places)
    save_json(VERSIONS_JSON_PATH, versions)
    save_json(SUBMISSIONS_JSON_PATH, submissions)
    
    # 同步編譯 data.js (免 CORS)
    with open(DATA_JS_PATH, 'w', encoding='utf-8') as f:
        f.write('// 全台寵物友善空間與餐廳數據集 (含 Google Maps 自動更新與營運狀態)\n')
        f.write('window.PET_PLACES_DATA = ')
        json.dump(places, f, ensure_ascii=False, indent=2)
        f.write(';\n')
        f.write('window.PET_MAP_VERSIONS = ')
        json.dump(versions, f, ensure_ascii=False, indent=2)
        f.write(';\n')
        
    print("\n✅ 更新完成！")
    print(f"📌 當前版本：{version_num} ({now_str})")
    print(f"📌 正常營運店家：{version_record['activeStores']} 家")
    print(f"📌 已標記關店/歇業：{len(closed_stores)} 家")
    print(f"📌 新增店家：{len(new_verified_stores)} 家")
    print(f"📌 資料庫已同步產出至 data.json 與 data.js")

if __name__ == '__main__':
    api_key = sys.argv[1] if len(sys.argv) > 1 else None
    run_auto_audit_and_update(google_api_key=api_key)
