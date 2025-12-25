import os
import time
import requests
import html
import datetime
import math
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =========================
#       CONFIG CORE
# =========================
HEADERS = {
    'User-Agent': 'Titan-GodMode/v100 (Full-Spectrum Data Aggregator)',
    'Cache-Control': 'no-cache'
}
CACHE = {}
CACHE_TTL = 10 # Seconds (Fresh data priority)

# BITWISE FLAGS MAPPING
PUBLIC_FLAGS = {
    1: "Discord Employee",
    2: "Partnered Server Owner",
    4: "HypeSquad Events",
    8: "Bug Hunter Level 1",
    64: "House Bravery",
    128: "House Brilliance",
    256: "House Balance",
    512: "Early Supporter",
    16384: "Bug Hunter Level 2",
    131072: "Early Verified Bot Developer",
    4194304: "Active Developer"
}

# SOCIAL URL GENERATORS
CONN_TEMPLATES = {
    "github": "https://github.com/{}", 
    "twitter": "https://x.com/{}", 
    "x": "https://x.com/{}",
    "reddit": "https://reddit.com/u/{}", 
    "steam": "https://steamcommunity.com/profiles/{}", 
    "twitch": "https://twitch.tv/{}", 
    "youtube": "https://youtube.com/@{}", 
    "spotify": "https://open.spotify.com/user/{}", 
    "instagram": "https://instagram.com/{}", 
    "facebook": "https://facebook.com/{}",
    "tiktok": "https://tiktok.com/@{}",
    "linkedin": "https://linkedin.com/in/{}",
    "battlenet": "#", # Private
    "xbox": "https://account.xbox.com/en-us/Profile?GamerTag={}",
    "playstation": "https://my.playstation.com/profile/{}",
    "leagueoflegends": "#", # Region specific
    "domain": "https://{}"
}

ICON_CDN = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons"

# =========================
#       MATH & LOGIC
# =========================

def decode_flags(flag_int):
    """Convert bitwise integer to list of badge names"""
    if not flag_int: return []
    badges = []
    for flag, name in PUBLIC_FLAGS.items():
        if flag_int & flag:
            badges.append({"flag_id": flag, "name": name})
    return badges

def get_snowflake_date(snowflake):
    """Exact creation time from Discord ID"""
    try:
        sf = int(snowflake)
        timestamp = ((sf >> 22) + 1420070400000) / 1000
        dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - dt
        
        return {
            "unix": int(timestamp),
            "iso": dt.isoformat(),
            "formatted": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "account_age_days": diff.days,
            "account_age_years": round(diff.days / 365.25, 2)
        }
    except: return None

def calc_contrast(hex_code):
    """Returns readable text color (black/white) based on background brightness"""
    if not hex_code or not str(hex_code).startswith("#"): return "white"
    try:
        h = hex_code.lstrip('#')
        r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299*r + 0.587*g + 0.114*b) / 255
        return "black" if luminance > 0.5 else "white"
    except: return "white"

def get_timestamps_data(start, end):
    """Calculates progress bars, elapsed time, and duration"""
    now = time.time() * 1000
    data = {"start_unix": start, "end_unix": end, "is_active": True}
    
    if start:
        elapsed = now - start
        s = int(elapsed / 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        data['elapsed_ms'] = int(elapsed)
        data['elapsed_text'] = f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"

    if start and end:
        total = end - start
        if total > 0:
            pct = (elapsed / total) * 100
            data['percentage'] = min(max(pct, 0), 100)
            data['duration_ms'] = total
            
            rem = end - now
            rs = int(abs(rem) / 1000)
            rm, rs = divmod(rs, 60)
            prefix = "-" if rem > 0 else "+"
            data['remaining_text'] = f"{prefix}{rm}:{rs:02d}"
        else:
            data['percentage'] = 100
            
    return data

# =========================
#     ASSET RESOLVERS
# =========================

def resolve_avatar(uid, hash_val):
    if not hash_val: 
        # Default discriminator based math is deprecated, assume blue default
        return "https://cdn.discordapp.com/embed/avatars/0.png"
    ext = "gif" if hash_val.startswith("a_") else "png"
    return f"https://cdn.discordapp.com/avatars/{uid}/{hash_val}.{ext}?size=1024"

def resolve_banner(uid, hash_val):
    if not hash_val: return None
    ext = "gif" if hash_val.startswith("a_") else "png"
    return f"https://cdn.discordapp.com/banners/{uid}/{hash_val}.{ext}?size=1024"

def resolve_decoration(hash_val):
    if not hash_val: return None
    return f"https://cdn.discordapp.com/avatar-decoration-presets/{hash_val}.png?size=96&passthrough=true"

def resolve_activity_image(app_id, asset_id):
    if not asset_id: return None
    if str(asset_id).startswith("mp:"):
        return f"https://media.discordapp.net/{asset_id.replace('mp:','')}"
    if str(asset_id).startswith("spotify:"):
        return f"https://i.scdn.co/image/{asset_id.replace('spotify:','')}"
    return f"https://cdn.discordapp.com/app-assets/{app_id}/{asset_id}.png"

# =========================
#     API ROUTE
# =========================

@app.route('/api/godmode/<uid>')
def get_full_data(uid):
    start_bench = time.perf_counter()
    
    # 1. CACHE CHECK
    now = time.time()
    if uid in CACHE:
        if now - CACHE[uid]['ts'] < CACHE_TTL:
            return jsonify(CACHE[uid]['data'])

    # 2. HARVEST DATA
    lanyard = {}
    dcdn = {}
    
    try:
        r_d = requests.get(f"https://dcdn.dstn.to/profile/{uid}", headers=HEADERS, timeout=4)
        if r_d.status_code == 200: dcdn = r_d.json()
    except: pass
    
    try:
        r_l = requests.get(f"https://api.lanyard.rest/v1/users/{uid}", headers=HEADERS, timeout=4)
        if r_l.status_code == 200:
            res = r_l.json()
            if res.get('success'): lanyard = res['data']
    except: pass
    
    if not lanyard and not dcdn:
        return jsonify({"success": False, "error": "No Data Found. Is the user in api.lanyard.rest?"}), 404

    # 3. MERGE & COMPUTE
    u_lan = lanyard.get('discord_user', {})
    u_dcdn = dcdn.get('user', {})
    
    # --- IDENTITY ---
    username = u_dcdn.get('username') or u_lan.get('username')
    display = u_dcdn.get('global_name') or u_lan.get('global_name') or username
    discriminator = u_lan.get('discriminator') or u_dcdn.get('discriminator')
    
    av_hash = u_dcdn.get('avatar') or u_lan.get('avatar')
    bn_hash = u_dcdn.get('banner') # Lanyard banners are often null, trust DCDN
    deco_hash = u_dcdn.get('avatar_decoration') or u_lan.get('avatar_decoration')
    
    accent = u_dcdn.get('accent_color')
    if accent: accent_hex = f"#{accent:06x}"
    else: accent_hex = "#5865F2"
    
    # Legacy DCDN Badges
    legacy_badges = []
    for b in dcdn.get('badges', []):
        legacy_badges.append({
            "name": b['id'],
            "icon": f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png",
            "url": f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png",
            "description": b.get('description')
        })
    
    # Calculated Badges from Flags
    flags_int = u_dcdn.get('public_flags') or u_lan.get('public_flags', 0)
    flag_badges = decode_flags(flags_int)

    # Connections
    connected_accounts = []
    for c in dcdn.get('connected_accounts', []):
        ctype = c['type']
        cid = c['id']
        cname = c['name']
        url = "#"
        if ctype in LINK_TEMPLATES:
            # Handle Steam special ID case vs username case
            fill = cid if ctype == 'steam' else cname
            url = LINK_TEMPLATES[ctype].format(fill)
            
        connected_accounts.append({
            "platform": ctype,
            "username": cname,
            "id": cid,
            "verified": c.get('verified', False),
            "url": url,
            "icon_svg": f"{ICON_CDN}/{ctype.replace('.','dot')}.svg"
        })

    # --- PRESENCE & ACTIVITY ---
    # Spotify Specifics
    spotify_data = None
    if lanyard.get('spotify'):
        s = lanyard['spotify']
        spotify_data = {
            "is_active": True,
            "platform": "spotify",
            "track_id": s.get('track_id'),
            "song": s.get('song'),
            "artist": s.get('artist'),
            "album": s.get('album'),
            "album_art_url": s.get('album_art_url'),
            "timestamps": get_timestamps_data(s.get('timestamps', {}).get('start'), s.get('timestamps', {}).get('end'))
        }
    
    # Rich Presence Scanner
    activities = []
    
    # Lanyard raw activity list
    raw_acts = lanyard.get('activities', [])
    for act in raw_acts:
        # Custom Status (Type 4)
        if act['type'] == 4:
            emoji_obj = None
            if act.get('emoji'):
                e = act['emoji']
                ext = "gif" if e.get('animated') else "png"
                emoji_obj = {
                    "name": e.get('name'),
                    "id": e.get('id'),
                    "url": f"https://cdn.discordapp.com/emojis/{e['id']}.{ext}" if e.get('id') else None
                }
            activities.append({
                "type_id": 4,
                "name": "Custom Status",
                "state": act.get('state'),
                "emoji": emoji_obj,
                "created_at": act.get('created_at')
            })
            continue
            
        # Ignore Spotify duplicates if handled above
        if act.get('id') == "spotify:1": continue
        
        # General Game/App
        app_id = act.get('application_id')
        assets = act.get('assets', {})
        timestamps = act.get('timestamps', {})
        
        # Calculate Party
        party = None
        if 'party' in act:
            if 'size' in act['party']:
                cur, max_p = act['party']['size']
                party = {"current": cur, "max": max_p, "formatted": f"{cur}/{max_p}"}
            else: party = {"id": act['party'].get('id')}

        activities.append({
            "type_id": act['type'], # 0:Play, 1:Stream, 2:Listen, 3:Watch, 5:Compete
            "app_id": app_id,
            "name": act.get('name'),
            "state": act.get('state'),
            "details": act.get('details'),
            "timestamps": get_timestamps_data(timestamps.get('start'), timestamps.get('end')),
            "party": party,
            "images": {
                "large_url": resolve_activity_image(app_id, assets.get('large_image')),
                "large_text": assets.get('large_text'),
                "small_url": resolve_activity_image(app_id, assets.get('small_image')),
                "small_text": assets.get('small_text'),
            },
            "sync_id": act.get('sync_id'),
            "session_id": act.get('session_id')
        })

    # Platforms
    active_platforms = []
    for p in ['desktop', 'mobile', 'web']:
        if lanyard.get(f'active_on_discord_{p}'): active_platforms.append(p)
    
    # 4. FINAL CONSOLIDATED PAYLOAD
    response_data = {
        "meta": {
            "api_version": "v100",
            "server_latency_ms": round((time.perf_counter() - start_bench) * 1000, 2),
            "generated_at": int(time.time()),
        },
        "user": {
            "id": uid,
            "username": username,
            "display_name": display_name,
            "discriminator": discriminator,
            "bio": bio, # Merged Bio
            "created_at": get_snowflake_date(uid),
            "flags": {
                "raw_int": flags_int,
                "decoded": flag_badges
            }
        },
        "theme": {
            "avatar_url": resolve_avatar(uid, av_hash),
            "banner_url": resolve_banner(uid, bn_hash),
            "avatar_decoration_url": resolve_decoration(deco_hash),
            "accent_color_hex": accent_hex,
            "text_contrast_recommendation": calc_contrast(accent_hex)
        },
        "presence": {
            "status": lanyard.get('discord_status', 'offline'),
            "is_mobile": lanyard.get('active_on_discord_mobile', False),
            "active_platforms": active_platforms,
            "kv": lanyard.get('kv', {}) # User KV store
        },
        "profile_data": {
            "badges_visible": legacy_badges, # Visual icons from DCDN
            "connected_accounts": connected_accounts # Fully resolved Links + Icons
        },
        "activities": activities, # All games/status
        "music": spotify_data # Separate specialized object
    }

    # Cache Store
    CACHE[uid] = {'ts': now, 'data': response_data}
    return jsonify(response_data)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
