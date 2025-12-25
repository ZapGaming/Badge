import os
import time
import math
import requests
import datetime
import re
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Enables usage from any website/obs

# =======================
#    SYSTEM CONFIG
# =======================
HEADERS = {'User-Agent': 'Titan-API/v60-DataCore'}
CACHE = {}
CACHE_TTL = 5 # Aggressive caching for 5 seconds

# Knowledge Base for Connections
CONN_URLS = {
    "github": "https://github.com/{}", 
    "twitter": "https://x.com/{}", "x": "https://x.com/{}",
    "reddit": "https://reddit.com/user/{}", 
    "steam": "https://steamcommunity.com/profiles/{}", # Accepts ID
    "twitch": "https://twitch.tv/{}", 
    "youtube": "https://youtube.com/@{}", 
    "spotify": "https://open.spotify.com/user/{}",
    "tiktok": "https://tiktok.com/@{}",
    "instagram": "https://instagram.com/{}",
    "facebook": "https://facebook.com/{}",
    "xbox": "https://account.xbox.com/en-us/Profile?GamerTag={}",
    "domain": "https://{}",
    "bsky": "https://bsky.app/profile/{}"
}

ICON_BASE = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons"

# =======================
#    COMPUTE ENGINE
# =======================

def solve_snowflake(sf):
    """Bitwise calculation to extract account creation date from Discord ID"""
    try:
        sf_int = int(sf)
        # Discord Epoch: 1420070400000
        ms = (sf_int >> 22) + 1420070400000
        dt = datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - dt
        years = diff.days // 365
        
        return {
            "unix_ms": ms,
            "iso": dt.isoformat(),
            "friendly": dt.strftime("%B %d, %Y"),
            "account_age_days": diff.days,
            "account_age_years": f"{years:.1f}"
        }
    except:
        return None

def calc_contrast(hex_code):
    """Calculates perceptive luminance to recommend text color (black vs white)"""
    if not hex_code or not hex_code.startswith('#'): return "light"
    try:
        h = hex_code.lstrip('#')
        rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        # Standard Rec. 709 Luminance
        lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
        return "black" if lum > 0.5 else "white"
    except: return "white"

def parse_time_window(start, end):
    """Complex Time Delta Math for Progress Bars"""
    now = time.time() * 1000
    
    obj = {
        "start": start, "end": end,
        "is_active": True
    }

    # Elapsed
    if start:
        el_ms = now - start
        s = int(el_ms / 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        obj['elapsed_ms'] = el_ms
        obj['elapsed_human'] = f"{m}:{s:02d}" if h==0 else f"{h}:{m:02d}:{s:02d}"
    
    # Progress & Remaining
    if start and end:
        total = end - start
        if total > 0:
            pct = (el_ms / total) * 100
            obj['progress'] = min(max(pct, 0), 100)
            
            rem_ms = end - now
            rs = int(rem_ms / 1000)
            rm, rs = divmod(rs, 60)
            obj['remaining_human'] = f"-{rm}:{rs:02d}"
            obj['duration_human'] = f"{int(total/1000//60)}:{int(total/1000%60):02d}"

    return obj

def resolve_asset(app_id, hash_val):
    if not hash_val: return None
    # External Proxy handling
    if hash_val.startswith("mp:"): 
        return f"https://media.discordapp.net/{hash_val.replace('mp:','')}"
    # Spotify handling
    if hash_val.startswith("spotify:"):
        return f"https://i.scdn.co/image/{hash_val.replace('spotify:','')}"
    # Standard Asset
    return f"https://cdn.discordapp.com/app-assets/{app_id}/{hash_val}.png"

# =======================
#    DATA AGGREGATOR
# =======================

@app.route('/api/data/<uid>')
def fetch_user_data(uid):
    start_bench = time.perf_counter()
    
    # 1. Cache Layer
    if uid in CACHE:
        if time.time() - CACHE[uid]['ts'] < CACHE_TTL:
            return jsonify(CACHE[uid]['data'])

    # 2. Source Harvesting (Parallel-simulated)
    # LANYARD (Live)
    lanyard = {}
    try:
        r_l = requests.get(f"https://api.lanyard.rest/v1/users/{uid}", headers=HEADERS, timeout=4)
        if r_l.status_code == 200: lanyard = r_l.json().get('data', {})
    except: pass
    
    # DCDN (Profile Meta)
    dcdn = {}
    dcdn_meta = {}
    try:
        r_d = requests.get(f"https://dcdn.dstn.to/profile/{uid}", headers=HEADERS, timeout=4)
        if r_d.status_code == 200:
            json_d = r_d.json()
            dcdn = json_d.get('user', {})
            dcdn_meta = json_d # root for badges/conns
    except: pass
    
    if not lanyard and not dcdn:
        return jsonify({"success": False, "error": "User not found via Lanyard or DCDN"}), 404

    # 3. Intelligent Parsing
    l_u = lanyard.get('discord_user', {})
    
    # Identity Logic (DCDN takes precedence for assets)
    username = dcdn.get('username') or l_u.get('username')
    global_name = dcdn.get('global_name') or l_u.get('global_name') or username
    
    # Advanced Asset Resolution (Avatars, Banners, Decorations)
    av_hash = dcdn.get('avatar') or l_u.get('avatar')
    av_ext = "gif" if av_hash and av_hash.startswith("a_") else "png"
    av_url = f"https://cdn.discordapp.com/avatars/{uid}/{av_hash}.{av_ext}?size=1024" if av_hash else None
    
    bn_hash = dcdn.get('banner') 
    bn_url = f"https://cdn.discordapp.com/banners/{uid}/{bn_hash}.{ 'gif' if bn_hash and bn_hash.startswith('a_') else 'png' }?size=2048" if bn_hash else None
    
    # Profile Color Math
    acc_color = dcdn.get('accent_color')
    acc_hex = f"#{acc_color:06x}" if acc_color else "#5865F2" # default blurple
    text_color_suggest = calc_contrast(acc_hex)
    
    # Account Age Calculation
    age_meta = solve_snowflake(uid)
    
    # Presence & Platforms
    status = lanyard.get('discord_status', 'offline')
    platforms = [k for k in ['desktop','mobile','web'] if lanyard.get(f'active_on_discord_{k}')]
    
    # Connection Normalization
    connections = []
    for c in dcdn_meta.get('connected_accounts', []):
        t = c['type']
        url = LINK_TEMPLATES.get(t, "#").format(c['id'] if t=='steam' else c['name'])
        connections.append({
            "type": t,
            "name": c['name'],
            "verified": c.get('verified', False),
            "url": url,
            "icon_svg_url": f"{ICON_BASE}/{t.replace('.','dot')}.svg"
        })

    # Badge Normalization
    badges = []
    for b in dcdn_meta.get('badges', []):
        badges.append({
            "id": b['id'],
            "description": b.get('description'),
            "icon": f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png"
        })

    # Deep Activity Analysis
    activities = []
    
    # A. Spotify Processing
    if lanyard.get('spotify'):
        s = lanyard['spotify']
        timers = parse_time_window(s['timestamps']['start'], s['timestamps']['end'])
        activities.append({
            "type": "spotify",
            "name": "Spotify",
            "header": "LISTENING TO",
            "title": s['song'],
            "state": s['artist'],
            "details": s['album'],
            "assets": { "large_image": s['album_art_url'] },
            "timestamps": timers
        })

    # B. RPC Processing
    for act in lanyard.get('activities', []):
        if act['type'] == 4: continue # custom status skip
        if act['id'] == 'spotify:1': continue # skip dup spotify

        ts = act.get('timestamps', {})
        timers = parse_time_window(ts.get('start'), ts.get('end'))
        
        # Verb Determination
        verbs = {0: "PLAYING", 1: "STREAMING", 2: "LISTENING TO", 3: "WATCHING", 5: "COMPETING IN"}
        
        assets = act.get('assets', {})
        app_id = act.get('application_id')
        
        activities.append({
            "type": "game",
            "app_id": app_id,
            "name": act['name'],
            "header": verbs.get(act['type'], "ACTIVITY"),
            "title": act.get('details', act['name']),
            "state": act.get('state'),
            "details": act.get('details'),
            "assets": {
                "large_image": resolve_asset(app_id, assets.get('large_image')),
                "large_text": assets.get('large_text'),
                "small_image": resolve_asset(app_id, assets.get('small_image')),
            },
            "timestamps": timers,
            "is_rich_presence": True
        })
        
    # C. Custom Status
    custom = next((a for a in lanyard.get('activities', []) if a['type'] == 4), None)
    status_text = custom.get('state') if custom else None
    
    # 4. Final Payload Assembly
    response = {
        "meta": {
            "success": True,
            "server_time": time.time(),
            "execution_ms": round((time.perf_counter() - start_bench) * 1000, 2)
        },
        "user": {
            "id": uid,
            "username": username,
            "global_name": display_name,
            "bio": d_user.get('bio') or lanyard.get('kv', {}).get('bio'),
            "created_at": age_meta
        },
        "assets": {
            "avatar": av_url,
            "banner": bn_url,
            "accent_color": acc_hex,
            "ui_theme": text_color_suggest
        },
        "presence": {
            "status": status,
            "active_platforms": platforms,
            "custom_status": status_text
        },
        "connections": connections,
        "badges": badges,
        "activities": activities
    }
    
    CACHE[uid] = {'ts': time.time(), 'data': response}
    return jsonify(response)

@app.route('/')
def home():
    return jsonify({
        "system": "Titan Data Aggregator v60",
        "status": "Online",
        "endpoints": ["/api/data/<user_id>"],
        "info": "This API processes Discord, Lanyard, and DCDN data into a unified schema."
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
