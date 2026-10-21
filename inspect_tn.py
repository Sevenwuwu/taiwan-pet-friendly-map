# -*- coding: utf-8 -*-
import json

with open('data.json', encoding='utf-8') as f:
    places = json.load(f)

with open('tn_check.txt', 'w', encoding='utf-8') as f:
    for p in places:
        if p['id'].startswith('tn-'):
            f.write(p['id'] + ' | ' + p['name'] + ' | ' + p['category'] + ' | ' + p['address'] + '\n')
