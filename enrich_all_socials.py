# -*- coding: utf-8 -*-
import sys
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
import re
import time
import urllib.parse
from curl_cffi import requests
from bs4 import BeautifulSoup
import os
import subprocess
import unicodedata

CACHE_FILE = 'social_cache.json'
DATA_JSON = 'data.json'
DATA_JS = 'data.js'

FB_BAD_SLUGS = {
    'instagram', 'facebook', 'policies', 'help', 'login', 'recover',
    'legal', 'about', 'privacy', 'security', 'terms', 'careers',
    'sharer', 'dialog', 'hashtag', 'events', 'groups', 'pages',
    'settings', 'index.php', 'watch', 'marketplace', 'gaming',
    'photo.php', 'video.php', 'directory', 'ads', 'business', 'r.php',
    'plugins', 'tr', 'v2.0', 'dialog'
}

IG_BAD_SLUGS = {
    'platform', 'applink', 'about', 'legal', 'privacy', 'terms',
    'explore', 'accounts', 'directory', 'developer', 'press',
    'stories', 'direct', 'web', 'reel', 'reels', 'tv', 'p', 'help',
    'support', 'download', 'live', 'tags', 'locations', 'graphql'
}

EXCLUDED_WEB_DOMAINS = [
    'yahoo.com', 'google.com', 'bing.com', 'facebook.com', 'instagram.com',
    'pixnet.net', 'walkerland.com.tw', 'tripadvisor', 'foodpanda',
    'ubereats', 'threads.net', 'youtube.com', 'wikipedia.org',
    'icook.tw', 'ipeen.com.tw', 'openrice.com', 'gov.tw', 'taiwangov.com',
    'popdaily.com.tw', 'funtime.com.tw', 'udn.com', 'ltn.com.tw', 'chinatimes.com',
    'ettoday.net', 'fonfood.com', 'ifoodie.tw', 'story-viewer.co', 'instadp.com',
    'picuki.com', 'dumpor.com', 'greatck.com', 'blog', 'travel', 'news', 'line.me',
    'x.com', 'twitter.com', 'threads.com', 'footprintiq.app', 'talesfromthecollection.com',
    'kenji.life', 'candylife.tw', 'lyes.tw', 'dalang.tw', 'aileelife.com', 'mecocute.com',
    'shhjusttellyou.com', 'elina0419.com', 'gotoformosa.com', 'taiwan17go.com', 'papacat.xyz'
]

def clean_store_name(name):
    # Normalize unicode (e.g. math bold 𝐇𝐎𝐖𝐖Ｏ𝐖 -> HOWWOW)
    name = unicodedata.normalize('NFKC', name)
    # Remove subtitles in brackets, parentheses, notes
    clean = re.sub(r'（.*?）|\(.*?\)|【.*?】', '', name).strip()
    # Remove branch suffix if hyphens
    clean = re.sub(r'[-－—_].*$', '', clean).strip()
    return clean if clean else name

def query_search_links(query):
    url = f"https://tw.search.yahoo.com/search?p={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        r = requests.get(url, headers=headers, impersonate="chrome120", timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for a in soup.select("a"):
            h = a.get("href", "")
            m = re.search(r'/RU=(https?[^/]+)/', h)
            if not m:
                continue
            target_url = urllib.parse.unquote(m.group(1))
            title = a.get_text(strip=True)
            items.append({"title": title, "url": target_url})
        return items
    except Exception as e:
        print(f"  [Search Error] {query}: {e}")
        return []

def extract_socials_for_store(city, name):
    clean = clean_store_name(name)
    items = query_search_links(f"{city} {clean} facebook")
    time.sleep(0.7)
    items += query_search_links(f"{city} {clean} instagram")
    
    fb = None
    ig = None
    web = None
    
    # Extract brand tokens for website domain matching
    name_tokens = [tok.lower() for tok in re.findall(r'[a-zA-Z0-9]{3,}', clean)]
    
    for item in items:
        u = item['url']
        parsed = urllib.parse.urlparse(u)
        domain = parsed.netloc.lower()
        path = parsed.path.strip('/')
        parts = [p for p in path.split('/') if p]
        
        # 1. Facebook Check
        if not fb and 'facebook.com' in domain:
            if parts:
                slug = parts[0].lower()
                if slug not in FB_BAD_SLUGS:
                    if slug == 'p' and len(parts) >= 2:
                        fb = f"https://www.facebook.com/p/{parts[1]}/"
                    elif len(parts) == 1:
                        fb = f"https://www.facebook.com/{parts[0]}/"
            elif 'profile.php' in parsed.path and 'id=' in parsed.query:
                fb = u.split('&')[0]
                
        # 2. Instagram Check
        if not ig and 'instagram.com' in domain:
            if len(parts) == 1:
                username = parts[0].lower()
                if username not in IG_BAD_SLUGS and re.match(r'^[a-zA-Z0-9._]{3,30}$', username):
                    ig = f"https://www.instagram.com/{parts[0]}/"
                    
        # 3. Official Website / Inline Check
        if not web:
            if 'inline.app' in domain and ('booking' in parsed.path or 'groups' in parsed.path):
                web = f"https://inline.app{parsed.path}"
            elif not any(ex in domain for ex in EXCLUDED_WEB_DOMAINS):
                # Only accept independent domain if it matches brand tokens or has clear brand connection
                if parsed.scheme in ['http', 'https'] and len(parts) <= 1:
                    clean_domain = domain.replace('www.', '').split('.')[0]
                    # Check if domain name matches store name tokens
                    if any(tok in clean_domain for tok in name_tokens if len(tok) >= 4):
                        web = f"{parsed.scheme}://{parsed.netloc}/"
                        
    return fb, ig, web

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def sync_data(places, cache):
    for p in places:
        pid = p['id']
        if pid in cache:
            entry = cache[pid]
            if entry.get('facebook'):
                p['facebook'] = entry['facebook']
            if entry.get('instagram'):
                p['instagram'] = entry['instagram']
            if entry.get('website'):
                p['website'] = entry['website']
                
    with open(DATA_JSON, 'w', encoding='utf-8') as f:
        json.dump(places, f, ensure_ascii=False, indent=2)
        
    with open(DATA_JS, 'w', encoding='utf-8') as f:
        f.write("// 全台寵物友善餐廳資料庫\nwindow.PET_PLACES_DATA = ")
        json.dump(places, f, ensure_ascii=False, indent=2)
        f.write(";\n")

def main():
    with open(DATA_JSON, 'r', encoding='utf-8') as f:
        places = json.load(f)
        
    cache = load_cache()
    total = len(places)
    print(f"=== Starting Social Links Enrichment for {total} Places ===")
    print(f"Already cached: {len(cache)} stores")
    
    found_fb = sum(1 for v in cache.values() if v.get('facebook'))
    found_ig = sum(1 for v in cache.values() if v.get('instagram'))
    found_web = sum(1 for v in cache.values() if v.get('website'))
    
    for idx, p in enumerate(places):
        pid = p['id']
        name = p['name']
        city = p['city']
        
        # Check if already processed with high confidence
        if pid in cache and (cache[pid].get('facebook') or cache[pid].get('instagram')):
            continue
            
        display_name = unicodedata.normalize('NFKC', name)
        try:
            print(f"[{idx+1}/{total}] Searching: ({city}) {display_name} ...", end=" ", flush=True)
        except:
            print(f"[{idx+1}/{total}] Searching: ({city}) [store] ...", end=" ", flush=True)
            
        fb, ig, web = extract_socials_for_store(city, name)
        
        cache[pid] = {
            "name": name,
            "city": city,
            "facebook": fb or "",
            "instagram": ig or "",
            "website": web or ""
        }
        
        if fb: found_fb += 1
        if ig: found_ig += 1
        if web: found_web += 1
        
        print(f"-> FB: {'YES' if fb else 'NO'} | IG: {'YES' if ig else 'NO'} | Web: {'YES' if web else 'NO'}")
        
        # Save cache and sync data every 10 stores
        if (idx + 1) % 10 == 0:
            save_cache(cache)
            sync_data(places, cache)
            print(f"  >>> [Auto-Sync Checkpoint {idx+1}/{total}] FB: {found_fb}, IG: {found_ig}, Web: {found_web}")
            
        time.sleep(1.0)
        
    # Final save
    save_cache(cache)
    sync_data(places, cache)
    print(f"\n=== Enrichment Complete! ===")
    print(f"Total Places: {total}")
    print(f"Total FB Pages Found: {found_fb}")
    print(f"Total IG Accounts Found: {found_ig}")
    print(f"Total Official Websites Found: {found_web}")

    # Auto push to GitHub
    try:
        subprocess.run(["git", "add", "data.json", "data.js", "social_cache.json"], check=True)
        subprocess.run(["git", "commit", "-m", f"feat(socials): enriched authentic FB/IG/Web for {found_fb} stores"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print(">>> Successfully committed and pushed enriched data to GitHub!")
    except Exception as ge:
        print(f"Git push note: {ge}")

if __name__ == '__main__':
    main()
