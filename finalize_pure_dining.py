# -*- coding: utf-8 -*-
import json

with open('data.json', encoding='utf-8') as f:
    places = json.load(f)

# Comprehensive exclusion filters
exclude_terms = [
    # 住宿
    '汽車旅館', '旅館', '飯店', '酒店', '民宿', '旅棧', '旅宿', '會館', 'SPA', '客棧',
    # 寵物用品/美容/醫療/紀念
    '東森寵物', '寵物生活館', '寵物用品', '寵物美容', '動物醫院', '動物之家', '特力屋', '紀念園區',
    '犬舍', '寵物澡堂', '寵物樂活館', '養殖行', '整容屋', '大樹寵物', '大魚寵物', '永魚寵物', '喵森有限公司', '燕翬企業社',
    # 交通/車輛
    '客運', '計程車', '車隊', '租車', '車業', '修車', '汽車股份',
    # 美容美髮
    '美髮', '剪燙', '沙龍', '髮型', '造型店', '造型美學', '刺青', '美甲',
    # 其他非餐飲
    '觀光工廠', '選物店', '營業場所名稱', '書城', '書店', '新創事業', '休閒園區', '森林園區'
]

# Exceptions (genuine restaurants)
exceptions = {
    'curated-9': True,   # 甘樂文創食堂
    'curated-36': True,  # 白色戀人文創咖啡館
    'curated-39': True,  # 波波廚房
    'tpe-197': True,    # 喜寶棧 咖啡酒館
    'tpe-230': True,    # 小紅花Cafe
    'ty-gov-3': True,   # 狗老大寵物渡假會館
}

pure_places = []
excluded_list = []

for p in places:
    pid = p['id']
    name = p['name']
    
    if pid in exceptions:
        pure_places.append(p)
        continue
        
    is_ex = False
    for ex in exclude_terms:
        if ex in name:
            excluded_list.append((pid, name, ex))
            is_ex = True
            break
            
    if not is_ex:
        pure_places.append(p)

print(f"Total pure restaurants retained: {len(pure_places)}")
print(f"Total excluded non-dining: {len(excluded_list)}")

# Save to data.json and data.js
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(pure_places, f, ensure_ascii=False, indent=2)

with open('data.js', 'w', encoding='utf-8') as f:
    f.write('// 全台寵物友善餐廳資料庫 (已替除非餐飲門市，含官網/FB/IG/Google Map 連結)\n')
    f.write('window.PET_PLACES_DATA = ')
    json.dump(pure_places, f, ensure_ascii=False, indent=2)
    f.write(';\n')

print("Updated data.json and data.js successfully.")
