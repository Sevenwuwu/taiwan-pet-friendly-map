# -*- coding: utf-8 -*-
"""
資料庫清洗與社群/定位連結增強腳本 (Clean Non-Dining & Enrich Links)
1. 替除掉所有非餐飲場所（美髮沙龍、純住宿旅宿、寵物美容用品店、五金賣場、展覽館、客運等）
2. 為每家餐廳全面增補：
   - 官方網站 (website)
   - 臉書專頁 (facebook)
   - Instagram (instagram)
   - Google Maps 定位與即時導航連結 (googleMapUrl)
"""

import json, re, urllib.parse, sys

sys.stdout.reconfigure(encoding='utf-8')

DATA_JSON_PATH = 'data.json'
DATA_JS_PATH = 'data.js'

with open(DATA_JSON_PATH, 'r', encoding='utf-8') as f:
    places = json.load(f)

# Non-dining exclude keywords
exclude_words = [
    'HAIR', '美髮', '沙龍', '剪燙', '造型美學', '美甲', '美睫', '刺青', 
    '旅店', '文旅', '飯店', '酒店', 'Hotel', 'hotel', 'B&B', '民宿', '客棧',
    '通運', '客運', '計程車', '租車', '車業', '修車',
    '博物館', '美術館', '工作室', '紙膠帶', '特力屋', '居家', '寢飾', '用品專賣',
    '寵物生活館', '寵物美容', '寵物用品', '動物醫院', '動物之家', '診所',
    '公車', '運動公園', '活動區', '溜狗區'
]

clean_places = []
removed_places = []

for p in places:
    name = p['name']
    cat = p.get('category', '')
    orig_cat = p.get('originalCat', '')
    
    # Check if explicitly non-dining in Taichung originalCat
    if orig_cat in ['交通', '住宿', '娛樂', '其他'] and not any(k in name for k in ['茶', '咖啡', '餐', '館', '店', '鍋']):
        removed_places.append((p['id'], name, 'Non-dining orig_cat: ' + orig_cat))
        continue
        
    is_excluded = False
    for ew in exclude_words:
        if ew.lower() in name.lower():
            if not any(dw in name for dw in ['餐廳', '咖啡', '食堂', '廚房', '鍋物', '早午餐', '茶餐', '餐酒']):
                removed_places.append((p['id'], name, f'Matches exclude word: {ew}'))
                is_excluded = True
                break
                
    if is_excluded:
        continue

    # Enrich with Links (Website, FB, IG, Google Map URL)
    clean_name = re.sub(r'[\s\(\)（）/]+', ' ', name).strip()
    encoded_name = urllib.parse.quote(f"{clean_name} {p['city']}")
    tag_name = re.sub(r'[^\w\u4e00-\u9fff]+', '', clean_name)
    
    # 1. Google Maps Navigation / Place URL
    p['googleMapUrl'] = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(clean_name + ' ' + p['address'])}"
    
    # 2. Facebook Page / Search URL
    if not p.get('facebook'):
        p['facebook'] = f"https://www.facebook.com/search/top?q={urllib.parse.quote(clean_name)}"
        
    # 3. Instagram Search URL
    if not p.get('instagram'):
        p['instagram'] = f"https://www.instagram.com/explore/tags/{urllib.parse.quote(tag_name)}/"
        
    # 4. Website
    if not p.get('website'):
        if p.get('sourceUrl') and 'gov.tw' not in p.get('sourceUrl'):
            p['website'] = p['sourceUrl']
        else:
            p['website'] = p['googleMapUrl'] # default to Google Maps profile

    # Update category if it was labeled as accommodation
    if p['category'] in ['友善住宿/露營', '休閒娛樂/空間']:
        p['category'] = '特色餐廳'

    clean_places.append(p)

print(f"Original total: {len(places)}")
print(f"Removed non-dining places: {len(removed_places)}")
print(f"Pure restaurants & cafes retained: {len(clean_places)}")

# Statistics by city
by_city = {}
for p in clean_places:
    by_city[p['city']] = by_city.get(p['city'], 0) + 1

print("\nCity breakdown for pure restaurants:")
for c, cnt in sorted(by_city.items(), key=lambda x: -x[1]):
    print(f"  {c}: {cnt}")

with open(DATA_JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(clean_places, f, ensure_ascii=False, indent=2)

with open(DATA_JS_PATH, 'w', encoding='utf-8') as f:
    f.write('// 全台寵物友善餐廳資料庫 (已替除非餐飲門市，含官網/FB/IG/Google Map 連結)\n')
    f.write('window.PET_PLACES_DATA = ')
    json.dump(clean_places, f, ensure_ascii=False, indent=2)
    f.write(';\n')

print("\nSuccessfully updated data.json and data.js.")
