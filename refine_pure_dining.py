# -*- coding: utf-8 -*-
import json

with open('data.json', encoding='utf-8') as f:
    places = json.load(f)

# Non-dining keywords
exclude_terms = [
    '汽車旅館', '旅館', '飯店', '酒店', '民宿', '旅棧', '旅宿', '會館', 'SPA', '客棧',
    '東森寵物', '寵物生活館', '寵物用品', '寵物美容', '動物醫院', '動物之家', '特力屋', '紀念園區',
    '客運', '計程車', '車隊', '租車', '車業', '修車', '觀光工廠', '選物店', '營業場所名稱', 
    '美髮', '剪燙', '沙龍', '髮型', '造型店', '造型美學', '刺青', '美甲', '書城', '書店',
    '犬舍', '寵物澡堂', '寵物樂活館', '養殖行', '整容屋', '休閒園區', '森林園區',
    '花水木新創事業', '喬善興業有限公司', '大魚寵物', '永魚寵物', '喵森有限公司', '燕翬企業社'
]

# Genuine restaurants/cafes that might contain some keywords
exceptions = {
    'curated-9': True,   # 甘樂文創食堂
    'curated-36': True,  # 白色戀人文創咖啡館
    'curated-39': True,  # 波波廚房
    'tpe-197': True,    # 喜寶棧 咖啡酒館
    'tpe-230': True,    # 小紅花Cafe
    'ty-gov-3': True,   # 狗老大寵物渡假會館 (有景觀餐廳與寵物餐)
}

final_places = []
removed = []

for p in places:
    pid = p['id']
    name = p['name']
    
    if pid in exceptions:
        final_places.append(p)
        continue
        
    is_ex = False
    for ex in exclude_terms:
        if ex in name:
            removed.append((pid, name, ex))
            is_ex = True
            break
            
    if not is_ex:
        final_places.append(p)

print(f"Original: {len(places)}")
print(f"Removed: {len(removed)}")
print(f"Remaining Pure Restaurants: {len(final_places)}")

with open('final_removed.txt', 'w', encoding='utf-8') as f:
    for r in removed:
        f.write(f"{r[0]} | {r[1]} | keyword: {r[2]}\n")

# Check remaining Tainan places
tn_remaining = [p for p in final_places if p['id'].startswith('tn-')]
print(f"Tainan remaining pure dining places: {len(tn_remaining)}")
with open('tn_remaining.txt', 'w', encoding='utf-8') as f:
    for p in tn_remaining:
        f.write(f"{p['id']} | {p['name']} | {p['category']} | {p['address']}\n")
