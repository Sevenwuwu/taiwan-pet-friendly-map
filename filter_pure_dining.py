# -*- coding: utf-8 -*-
import json

with open('data.json', encoding='utf-8') as f:
    places = json.load(f)

# Criteria for non-dining:
# 1. Obvious non-dining keywords
exclude_terms = [
    '汽車旅館', '旅館', '飯店', '酒店', '民宿', '旅棧', '旅宿', '會館', 'SPA', '客棧',
    '東森寵物', '寵物生活館', '寵物用品', '寵物美容', '動物醫院', '動物之家', '特力屋', '紀念園區',
    '客運', '計程車', '車隊', '租車', '車業', '修車', '觀光工廠', '選物店', '營業場所名稱', 
    '美髮', '剪燙', '沙龍', '髮型', '造型店', '造型美學', '刺青', '美甲', '書城', '書店',
    '犬舍', '寵物澡堂', '寵物樂活館', '養殖行', '整容屋', '渡假', '休閒園區', '森林園區'
]

flagged = []
keep = []

for p in places:
    name = p['name']
    
    # Exceptions that are genuine restaurants/cafes despite keywords
    # e.g., "波波廚房 Kitchen Swell（80年老醫院古宅）" is an actual famous restaurant in an old hospital building!
    # "甘樂文創食堂" is an actual dining restaurant!
    # "白色戀人文創咖啡館" is an actual cafe!
    # "喜寶棧 咖啡酒館 & 貓旅館" - has cat hotel, but serves food/drinks. Let's see if we keep or clean name.
    
    if p['id'] in ['curated-9', 'curated-36', 'curated-39']:
        keep.append(p)
        continue

    is_exclude = False
    for t in exclude_terms:
        if t in name:
            flagged.append((p['id'], name, p['city'], t))
            is_exclude = True
            break
            
    if not is_exclude:
        keep.append(p)

print(f"Total current: {len(places)}")
print(f"Flagged non-dining: {len(flagged)}")
print(f"Kept pure dining: {len(keep)}")

with open('flagged_all.txt', 'w', encoding='utf-8') as f:
    for fid, fname, fcity, ft in flagged:
        f.write(f"{fid} | {fname} | {fcity} | {ft}\n")

with open('pure_dining_places.json', 'w', encoding='utf-8') as f:
    json.dump(keep, f, ensure_ascii=False, indent=2)
