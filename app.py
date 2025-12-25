import os
import time
import json
import math
import requests
import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =======================
#    HYPER CONFIG
# =======================
CACHE = {}
CACHE_TTL = 15  # Seconds
HEADERS = {
    'User-Agent': 'Titan-GodMode/v61-Fixed'
}

LINK_TEMPLATES = {
    "github": "https://github.com/{}", "twitter": "https://x.com/{}",
    "reddit": "https://reddit.com/user/{}", "twitch": "https://twitch.tv/{}",
    "youtube": "https://youtube.com/channel/{}", "spotify": "https://open.spotify.com/user/{}",
    "steam": "https://steamcommunity.com/profiles/{}", "facebook": "https://facebook.com/{}",
    "instagram": "https://instagram.com/{}", "tiktok": "https://tiktok.com/@{}",
    "xbox": "https://account.xbox.com/en-us/Profile?GamerTag={}",
    "domain": "https://{}", "bsky": "https://bsky.app/profile/{}"
}

ICON_CDN_BASE = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons"

# =======================
#    HELPERS
# =======================

def snowflake_to_time(snowflake):
    """Calculates Account Creation Date from Discord ID"""
    try:
        snowflake = int(snowflake)
        timestamp = ((snowflake >> 22) + 1420070400000) / 1000
        dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        return {
            "iso": dt.isoformat(),
            "formatted": dt.strftime("%b %d, %Y"),
            "unix": int(timestamp),
            "age_days": (datetime.datetime.now(datetime.timezone.utc) - dt).days
        }
    except: return None

def get_luminance(hex_color):
    """Calculates if a color is 'light' or 'dark'"""
    if not hex_color or not isinstance(hex_color, str) or not hex_color.startswith('#'): 
        return "dark" # Safe default
    color = hex_color.lstrip('#')
    try:
        if len(color) == 6:
            rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
            lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2])
            return "light" if lum > 128 else "dark"
    except: pass
    return "dark"

def calc_time_math(start, end):
    now = time.time() * 1000
    try:
        s = int(start)
        e = int(end) if end else None
        
        elapsed_ms = now - s
        
        # Human Readable Elapsed
        seconds = int(elapsed_ms / 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        readable = f"{minutes:02d}:{seconds:02d}"
        if hours > 0: readable = f"{hours}:{readable}"
        
        obj = {
            "start_unix": s,
            "elapsed_ms": elapsed_ms,
            "human_elapsed": readable,
        }
        
        if e:
            total = e - s
            progress = min(max((elapsed_ms / total) * 100, 0), 100) if total > 0 else 0
            
            # Remaining
            rem_ms = e - now
            rem_s = int(rem_ms / 1000)
            rem_m, rem_s = divmod(rem_s, 60)
            
            obj.update({
                "end_unix": e,
                "total_duration_ms": total,
                "progress_percent": round(progress, 2),
                "human_remaining": f"-{rem_m}:{rem_s:02d}",
                "is_seekable": True
            })
        else:
            obj["is_seekable"] = False
            obj["progress_percent"] = 0
            
        return obj
    except:
        return None

def resolve_discord_asset(app_id, asset_id):
    if not asset_id: return None
    if asset_id.startswith("mp:"):
        return f"https://media.discordapp.net/{asset_id.replace('mp:','')}"
    if asset_id.startswith("spotify:"):
        return f"https://i.scdn.co/image/{asset_id.replace('spotify:','')}"
    return f"https://cdn.discordapp.com/app-assets/{app_id}/{asset_id}.png"

def resolve_icon(icon_type):
    slug = icon_type.replace(".", "dot").lower()
    return f"{ICON_CDN_BASE}/{slug}.svg"

def format_activity(act):
    if not act: return None
    app_id = act.get('application_id')
    assets = act.get('assets', {})
    
    # Image resolution
    large_img = resolve_discord_asset(app_id, assets.get('large_image'))
    small_img = resolve_discord_asset(app_id, assets.get('small_image'))

    # Timestamps
    time_meta = None
    timestamps = act.get('timestamps')
    if timestamps:
        time_meta = calc_time_math(timestamps.get('start'), timestamps.get('end'))

    return {
        "type_id": "rich_presence",
        "name": act.get('name'),
        "header": "PLAYING" if act.get('type')==0 else "ACTIVITY",
        "title": act.get('details'),
        "description": act.get('state'),
        "assets": {
            "large_image": large_img,
            "large_text": assets.get('large_text'),
            "small_image": small_img,
            "small_text": assets.get('small_text')
        },
        "timestamps": time_meta,
        "app_id": app_id
    }

# =======================
#    CORE PROCESSOR
# =======================

@app.route('/api/godmode/<user_id>')
def god_mode(user_id):
    start_time = time.time()
    
    # Check Cache
    if user_id in CACHE:
        if start_time - CACHE[user_id]['ts'] < CACHE_TTL:
            return jsonify(CACHE[user_id]['payload'])

    # Initialize Containers (Prevents "not defined" errors)
    dcdn_data = {}
    dcdn_root = {} # Default root if DCDN fails
    lanyard_data = {}
    
    # 1. FETCH DCDN
    try:
        r1 = requests.get(f"https://dcdn.dstn.to/profile/{user_id}", headers=HEADERS, timeout=4)
        if r1.status_code == 200: 
            dcdn_root = r1.json()
            dcdn_data = dcdn_root.get('user', {})
    except: pass

    # 2. FETCH LANYARD
    try:
        r2 = requests.get(f"https://api.lanyard.rest/v1/users/{user_id}", headers=HEADERS, timeout=4)
        if r2.status_code == 200:
            lan = r2.json()
            if lan['success']: lanyard_data = lan['data']
    except: pass

    # VALIDATION
    if not lanyard_data and not dcdn_data:
        return jsonify({"error": "User not found", "success": False}), 404

    l_user = lanyard_data.get('discord_user', {})
    
    # ==========================
    #   BUILDING DATA
    # ==========================
    
    # 1. IDENTITY (Fixing variables here)
    username = l_user.get('username') or dcdn_data.get('username')
    display_name = l_user.get('global_name') or dcdn_data.get('global_name') or username
    
    avatar_id = l_user.get('avatar') or dcdn_data.get('avatar')
    banner_id = dcdn_data.get('banner') 
    
    accent_color = dcdn_data.get('accent_color')
    if accent_color: accent_hex = f"#{accent_color:06x}"
    else: accent_hex = "#5865F2"
    
    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}" if avatar_id else None
    banner_url = None
    if banner_id:
        ext = "gif" if banner_id.startswith("a_") else "png"
        banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{banner_id}.{ext}?size=1024"
        
    created_at = snowflake_to_time(user_id) # Was named creation_meta in v60

    # 2. STATUS
    discord_status = lanyard_data.get('discord_status', 'offline')
    active_platforms = []
    for p in ['desktop', 'mobile', 'web']:
        if lanyard_data.get(f'active_on_discord_{p}'): active_platforms.append(p)

    # 3. CONNECTIONS & BADGES (Safe DCDN access)
    connections = []
    for c in dcdn_root.get('connected_accounts', []):
        c_type = c['type']
        link = LINK_TEMPLATES.get(c_type, "#").format(c['id'] if c_type=='steam' else c['name'])
        connections.append({
            "platform": c_type,
            "username": c['name'],
            "url": link,
            "icon": resolve_icon(c_type)
        })

    badges = []
    for b in dcdn_root.get('badges', []):
        badges.append({
            "id": b.get('id'),
            "icon_url": f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png",
            "name": b.get('id') # Fallback description
        })

    # 4. ACTIVITY SCANNING
    processed_activities = []
    current_spotify = None
    
    # Spotify
    if lanyard_data.get('spotify'):
        s = lanyard_data['spotify']
        time_meta = calc_time_math(s['timestamps']['start'], s['timestamps']['end'])
        
        current_spotify = {
            "track": s['song'],
            "artist": s['artist'],
            "album": s['album'],
            "art_url": s['album_art_url'],
            "timestamps": time_meta
        }
        # Add Spotify as an Activity for "Smart View" consistency
        processed_activities.append({
            "type_id": "spotify",
            "header": "LISTENING TO",
            "title": s['song'],
            "description": s['artist'],
            "assets": { "large_image": s['album_art_url'] },
            "timestamps": time_meta,
            "is_music": True
        })

    # Rich Presence
    for act in lanyard_data.get('activities', []):
        # Skip Custom Status and Spotify Mirror
        if act['type'] == 4: continue
        if act.get('id') == "spotify:1": continue
        
        processed = format_activity(act)
        processed_activities.append(processed)

    # Custom Status
    custom_status = None
    for act in lanyard_data.get('activities', []):
        if act['type'] == 4:
            emoji_url = None
            if act.get('emoji') and act['emoji'].get('id'):
                ext = "gif" if act['emoji'].get('animated') else "png"
                emoji_url = f"https://cdn.discordapp.com/emojis/{act['emoji']['id']}.{ext}"
            
            custom_status = {
                "text": act.get('state', ''),
                "emoji_url": emoji_url
            }
            break

    # 5. RESPONSE CONSTRUCTION
    payload = {
        "success": True,
        "timestamp_generated": start_time,
        "user_info": {
            "id": user_id,
            "username": username,
            "display_name": display_name,
            "created_at": created_at,
            "avatar_url": avatar_url,
            "banner_url": banner_url,
        },
        "profile": {
            "bio": d_user.get('bio', dcdn_data.get('bio')), # Double check locations
            "accent_color_hex": accent_hex,
            "badges": badges,
            "connections": connections
        },
        "status": {
            "status": discord_status,
            "active_on": active_platforms,
            "custom_status": custom_status,
            "kv": lanyard_data.get('kv', {})
        },
        "data": {
            "spotify": current_spotify,
            "activities": processed_activities
        }
    }
    
    # Cache
    CACHE[user_id] = {'ts': start_time, 'payload': payload}
    return jsonify(payload)

@app.route('/')
def doc():
    return render_template_string("<html><body><h1>Titan API God Mode</h1><p>/api/godmode/&lt;user_id&gt;</p></body></html>")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
