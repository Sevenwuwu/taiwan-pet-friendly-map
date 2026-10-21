# -*- coding: utf-8 -*-
import json

with open('data.json', encoding='utf-8') as f:
    places = json.load(f)

suspects = []
for p in places:
    name = p['name']
    orig = p.get('originalCat', '')
    cat = p.get('category', '')
    for k in ['會館', '文創', '園區', '旅', '宿', '工作室', 'SPA', '醫院', '診所', '美容', '美甲', '沙龍']:
        if k in name:
            suspects.append({'id': p['id'], 'name': name, 'cat': cat, 'orig': orig, 'matched': k})

with open('suspect_list.json', 'w', encoding='utf-8') as f:
    json.dump(suspects, f, ensure_ascii=False, indent=2)

print(f"Found {len(suspects)} suspect places.")
