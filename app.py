import os
import time
import requests
import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =======================
#    CONFIGURATION
# =======================
HEADERS = {'User-Agent': 'Titan-API/v63-Stable'}
CACHE = {}
CACHE_TTL = 15

# DEFINED: Link Templates (Fixed NameError)
LINK_TEMPLATES = {
    "github": "https://github.com/{}", 
    "twitter": "https://x.com/{}", "x": "https://x.com/{}",
    "reddit": "https://reddit.com/user/{}", 
    "twitch": "https://twitch.tv/{}", 
    "youtube": "https://youtube.com/channel/{}", 
    "spotify": "https://open.spotify.com/user/{}",
    "steam": "https://steamcommunity.com/profiles/{}", # Usually ID
    "tiktok": "https://tiktok.com/@{}",
    "instagram": "https://instagram.com/{}",
    "facebook": "https://facebook.com/{}",
    "xbox": "https://account.xbox.com/en-us/Profile?GamerTag={}",
    "domain": "https://{}",
    "bsky": "https://bsky.app/profile/{}"
}

ICON_BASE = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons"

# =======================
#    LOGIC ENGINE
# =======================

def solve_snowflake(sf):
    """Calculate Account Age from ID"""
    try:
        sf = int(sf)
        timestamp = ((sf >> 22) + 1420070400000) / 1000
        dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - dt
        return {
            "iso": dt.isoformat(),
            "pretty": dt.strftime("%B %d, %Y"),
            "unix": int(timestamp),
            "age_years": f"{diff.days / 365:.1f}"
        }
    except: return None

def calc_contrast(hex_code):
    """Determine text color (black/white) based on background hex"""
    if not hex_code or not str(hex_code).startswith('#'): return "light"
    try:
        h = hex_code.lstrip('#')
        rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        lum = (0.299*rgb[0] + 0.587*rgb[1] + 0.114*rgb[2]) / 255
        return "black" if lum > 0.5 else "white"
    except: return "white"

def parse_timestamps(start, end):
    """Progress Bar Math"""
    now = time.time() * 1000
    obj = {"start": start, "end": end}
    
    if start:
        el = now - start
        s = int(el / 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        obj['elapsed'] = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        
        if end:
            tot = end - start
            if tot > 0:
                pct = min(max((el / tot) * 100, 0), 100)
                obj['percent'] = round(pct, 2)
                
                rem = end - now
                rs = int(abs(rem) / 1000)
                rm, rs = divmod(rs, 60)
                obj['remaining'] = f"-{rm}:{rs:02d}"
    return obj

# =======================
#    MAIN API ROUTE
# =======================

@app.route('/api/data/<uid>')
def fetch_user_data(uid):
    start_bench = time.perf_counter()
    
    # 1. CACHE CHECK
    if uid in CACHE:
        if time.time() - CACHE[uid]['ts'] < CACHE_TTL:
            return jsonify(CACHE[uid]['data'])

    # 2. FETCHING
    dcdn = {}
    lanyard = {}
    
    try:
        r = requests.get(f"https://dcdn.dstn.to/profile/{uid}", headers=HEADERS, timeout=4)
        if r.status_code == 200: dcdn = r.json()
    except: pass
    
    try:
        r = requests.get(f"https://api.lanyard.rest/v1/users/{uid}", headers=HEADERS, timeout=4)
        if r.status_code == 200: 
            dat = r.json()
            if dat.get('success'): lanyard = dat['data']
    except: pass

    # If absolutely nothing found
    if not lanyard and not dcdn:
        return jsonify({"success": False, "error": "User Not Found"}), 404

    # 3. PROCESSING
    l_u = lanyard.get('discord_user', {})
    d_u = dcdn.get('user', {})
    
    # Identity
    user_id = str(uid)
    username = l_u.get('username') or d_u.get('username') or "Unknown"
    global_name = l_u.get('global_name') or d_u.get('global_name') or username
    
    # Avatar/Banner
    av = l_u.get('avatar') or d_u.get('avatar')
    bn = d_u.get('banner') # DCDN preferred for banner
    av_url = f"https://cdn.discordapp.com/avatars/{uid}/{av}.png" if av else "https://cdn.discordapp.com/embed/avatars/0.png"
    bn_url = f"https://cdn.discordapp.com/banners/{uid}/{bn}.png?size=1024" if bn else None
    
    # Color
    color = d_u.get('accent_color')
    hex_col = f"#{color:06x}" if color else "#5865F2"
    
    # Connections (Fixed logic here)
    connections = []
    # Loop over DCDN 'connected_accounts' list
    raw_conns = dcdn.get('connected_accounts', []) 
    for c in raw_conns:
        t = c.get('type')
        n = c.get('name')
        i = c.get('id')
        
        # Link Builder
        link = "#"
        if t in LINK_TEMPLATES:
            # Some platforms like steam use ID in url, others use Name
            arg = i if t == 'steam' else n
            link = LINK_TEMPLATES[t].format(arg)
            
        connections.append({
            "type": t,
            "name": n,
            "url": link,
            "icon": f"{ICON_BASE}/{t.replace('.','dot')}.svg"
        })

    # Activity Processing
    acts = []
    
    # Spotify
    spot = lanyard.get('spotify')
    if spot:
        acts.append({
            "type": "spotify",
            "name": "Spotify",
            "line1": spot['song'],
            "line2": spot['artist'],
            "line3": spot['album'],
            "image": spot['album_art_url'],
            "timestamps": parse_time_window(spot['timestamps']['start'], spot['timestamps']['end'])
        })
        
    # Games
    for a in lanyard.get('activities', []):
        if a['type'] == 4: continue # skip status
        if a['id'] == 'spotify:1': continue 
        
        # Image Resolve
        img = None
        if a.get('assets') and a['assets'].get('large_image'):
            raw = a['assets']['large_image']
            app_id = a['application_id']
            if raw.startswith("mp:"): img = f"https://media.discordapp.net/{raw[3:]}"
            else: img = f"https://cdn.discordapp.com/app-assets/{app_id}/{raw}.png"
            
        acts.append({
            "type": "game",
            "name": a['name'],
            "line1": a.get('details', a['name']),
            "line2": a.get('state', ''),
            "image": img,
            "timestamps": parse_time_window(a.get('timestamps', {}).get('start'), a.get('timestamps', {}).get('end'))
        })

    # Final Payload
    payload = {
        "success": True,
        "ts": time.time(),
        "user": {
            "id": user_id,
            "username": username,
            "display": global_name,
            "avatar": av_url,
            "banner": bn_url,
            "bio": d_user.get('bio') or lanyard.get('kv', {}).get('bio'),
            "age": solve_snowflake(uid),
            "theme": {
                "color": hex_col,
                "text": calc_contrast(hex_col)
            }
        },
        "connections": connections,
        "presence": {
            "status": lanyard.get('discord_status', 'offline'),
            "platforms": [k for k in ['desktop','mobile','web'] if lanyard.get(f'active_on_discord_{k}')],
        },
        "activities": acts
    }
    
    CACHE[uid] = {'ts': time.time(), 'data': payload}
    return jsonify(payload)

@app.route('/')
def home():
    return jsonify({
        "status": "Online",
        "system": "Titan Data Aggregator v63",
        "endpoints": ["/api/data/<user_id>"]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
