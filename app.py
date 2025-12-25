import os
import time
import json
import math
import requests
import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from dateutil import parser

app = Flask(__name__)
CORS(app)  # Allow usage in OBS/Websites/Localhost

# =======================
#    HYPER CONFIG
# =======================
CACHE = {}
CACHE_TTL = 15  # Fast refresh for live data
HEADERS = {
    'User-Agent': 'Titan-GodMode/v60 (Data Aggregator)'
}

# The Massive Link Directory
LINK_TEMPLATES = {
    "github": "https://github.com/{}",
    "twitter": "https://twitter.com/{}",
    "reddit": "https://reddit.com/user/{}",
    "twitch": "https://twitch.tv/{}",
    "youtube": "https://youtube.com/channel/{}",
    "spotify": "https://open.spotify.com/user/{}",
    "steam": "https://steamcommunity.com/profiles/{}",
    "facebook": "https://facebook.com/{}",
    "instagram": "https://instagram.com/{}",
    "tiktok": "https://tiktok.com/@{}",
    "xbox": "https://account.xbox.com/en-us/Profile?GamerTag={}",
    "battle.net": "#", # No public link
    "domain": "https://{}",
    "mastodon": "{}", # Handle usually is URL
    "bsky": "https://bsky.app/profile/{}"
}

ICON_CDN_BASE = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons"

# =======================
#    ADVANCED MATH ENGINE
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
    """Calculates if a color is 'light' or 'dark' for text contrast"""
    if not hex_color or not hex_color.startswith('#'): return "unknown"
    color = hex_color.lstrip('#')
    try:
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        # Standard Luminance Formula
        lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2])
        return "light" if lum > 128 else "dark"
    except: return "unknown"

def calc_time_math(start, end):
    """Generates detailed timeline data"""
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
            progress = min(max((elapsed_ms / total) * 100, 0), 100)
            
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

# =======================
#    ASSET RESOLVER
# =======================

def resolve_discord_asset(app_id, asset_id):
    if not asset_id: return None
    # Discord Hosted External
    if asset_id.startswith("mp:"):
        return f"https://media.discordapp.net/{asset_id.replace('mp:','')}"
    # Spotify Asset
    if asset_id.startswith("spotify:"):
        return f"https://i.scdn.co/image/{asset_id.replace('spotify:','')}"
    # Standard Rich Presence Asset
    return f"https://cdn.discordapp.com/app-assets/{app_id}/{asset_id}.png"

def resolve_icon(icon_type):
    # Mapping discord types to SimpleIcons slugs
    slug = icon_type.replace(".", "dot").lower()
    return f"{ICON_CDN_BASE}/{slug}.svg"

# =======================
#    CORE PROCESSOR
# =======================

@app.route('/api/godmode/<user_id>')
def god_mode(user_id):
    start_time = time.time()
    
    # 1. PARALLEL-ISH FETCHING
    dcdn_data = {}
    lanyard_data = {}
    
    # FETCH DCDN (Profile Data)
    try:
        r1 = requests.get(f"https://dcdn.dstn.to/profile/{user_id}", headers=HEADERS, timeout=4)
        if r1.status_code == 200: dcdn_data = r1.json().get('user', {}) or {}
        # Fetch badges list separate in dcdn structure sometimes
        dcdn_root = r1.json() if r1.status_code == 200 else {}
    except: pass

    # FETCH LANYARD (Live Data)
    try:
        r2 = requests.get(f"https://api.lanyard.rest/v1/users/{user_id}", headers=HEADERS, timeout=4)
        if r2.status_code == 200:
            lan = r2.json()
            if lan['success']: lanyard_data = lan['data']
    except: pass

    # VALIDATION
    if not lanyard_data and not dcdn_data:
        return jsonify({"error": "User could not be found via Discord APIs.", "tips": "Join discord.gg/lanyard"}), 404

    l_user = lanyard_data.get('discord_user', {})
    
    # ==========================
    #   BUILDING THE ULTRA OBJECT
    # ==========================
    
    # 1. IDENTITY & VISUALS
    username = l_user.get('username') or dcdn_data.get('username')
    display = l_user.get('global_name') or dcdn_data.get('global_name') or username
    avatar_id = l_user.get('avatar') or dcdn_data.get('avatar')
    banner_id = dcdn_data.get('banner') # Prefer DCDN for banners
    
    accent_color = dcdn_data.get('accent_color') # Int format
    if accent_color: accent_hex = f"#{accent_color:06x}"
    else: accent_hex = "#5865F2" # Default blurple
    
    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}"
    banner_url = None
    if banner_id:
        ext = "gif" if banner_id.startswith("a_") else "png"
        banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{banner_id}.{ext}?size=1024"
        
    creation_meta = snowflake_to_time(user_id)

    # 2. STATUS ANALYSIS
    discord_status = lanyard_data.get('discord_status', 'offline')
    # Determine which platform (desktop/mobile/web) is active
    active_platforms = []
    for platform in ['desktop', 'mobile', 'web']:
        if lanyard_data.get(f'active_on_discord_{platform}'):
            active_platforms.append(platform)

    # 3. CONNECTION & BADGE RESOLUTION
    # Convert DCDN connections into Rich Objects with Icons
    connections = []
    raw_conns = dcdn_root.get('connected_accounts', [])
    for c in raw_conns:
        c_type = c['type']
        c_name = c['name']
        c_id = c['id']
        
        # Link Logic
        link = "#"
        if c_type in LINK_TEMPLATES:
            # Handle special cases like steam needing ID vs Name
            fill_val = c_id if c_type == 'steam' else c_name
            link = LINK_TEMPLATES[c_type].format(fill_val)
            
        connections.append({
            "platform": c_type,
            "username": c_name,
            "identifier": c_id,
            "url": link,
            "verified": c.get('verified', False),
            "icon": resolve_icon(c_type)
        })

    # 4. DEEP ACTIVITY SCANNING
    # Merge Spotify and Activities into one "Smart List"
    processed_activities = []
    
    # -> A. Spotify (Special Handling)
    if lanyard_data.get('spotify'):
        s = lanyard_data['spotify']
        time_meta = calc_time_math(s['timestamps']['start'], s['timestamps']['end'])
        
        processed_activities.append({
            "type_id": "spotify",
            "name": "Spotify",
            "header": "LISTENING TO",
            "title": s['song'],
            "description": s['artist'],
            "sub_description": f"on {s['album']}",
            "assets": {
                "large_image": s['album_art_url'],
                "small_image": None, # Usually spotify logo, skipping for clean look
            },
            "timestamps": time_meta,
            "is_music": True
        })

    # -> B. Discord Rich Presence
    for act in lanyard_data.get('activities', []):
        # Skip Custom Status (Type 4) here, handled separate
        if act['type'] == 4: continue
        if act['id'] == "spotify:1": continue # Already handled
        
        # Asset resolving
        assets = act.get('assets', {})
        large_img = resolve_discord_asset(act['application_id'], assets.get('large_image'))
        small_img = resolve_discord_asset(act['application_id'], assets.get('small_image'))
        
        # Timestamps
        time_meta = None
        if 'timestamps' in act:
            start = act['timestamps'].get('start')
            end = act['timestamps'].get('end')
            if start: time_meta = calc_time_math(start, end)
            
        # Determine "Verb"
        verb = "PLAYING"
        if act['type'] == 3: verb = "WATCHING"
        if act['type'] == 2: verb = "LISTENING TO"
        if act['type'] == 5: verb = "COMPETING IN"
        if act['type'] == 1: verb = "STREAMING"

        processed_activities.append({
            "type_id": "rich_presence",
            "name": act['name'],
            "header": verb,
            "title": act.get('details', act['name']),
            "description": act.get('state', ''),
            "assets": {
                "large_image": large_img,
                "large_text": assets.get('large_text'),
                "small_image": small_img,
                "small_text": assets.get('small_text')
            },
            "timestamps": time_meta,
            "app_id": act['application_id']
        })

    # -> C. Custom Status
    custom_status = None
    for act in lanyard_data.get('activities', []):
        if act['type'] == 4:
            emoji_url = None
            if act.get('emoji'):
                if act['emoji'].get('id'):
                     ext = "gif" if act['emoji'].get('animated') else "png"
                     emoji_url = f"https://cdn.discordapp.com/emojis/{act['emoji']['id']}.{ext}"
            
            custom_status = {
                "text": act.get('state'),
                "emoji_char": act.get('emoji', {}).get('name'),
                "emoji_url": emoji_url
            }
            break

    # ==========================
    #     FINAL RESPONSE
    # ==========================
    response = {
        "success": True,
        "process_time_ms": round((time.time() - start_time) * 1000, 2),
        "data": {
            "identity": {
                "id": user_id,
                "username": username,
                "display_name": display_name,
                "avatar_url": avatar_url,
                "banner_url": banner_url,
                "accent_color": accent_hex,
                "text_contrast": get_luminance(accent_hex),
                "account_created": creation_meta
            },
            "bio": d_user.get('bio'),
            "connections": connections,
            "badges_raw": dcdn_root.get('badges', []), # Returns full object array
            
            "presence": {
                "status": discord_status,
                "active_on": active_platforms,
                "custom_status": custom_status,
                "is_mobile": lanyard_data.get('active_on_discord_mobile', False),
                "kv": lanyard_data.get('kv', {})
            },
            
            "activities": processed_activities,
            
            "smart_view": {
                # Pre-calculated field for what to show on a card
                "primary_image": processed_activities[0]['assets']['large_image'] if processed_activities else banner_url or avatar_url,
                "primary_title": processed_activities[0]['title'] if processed_activities else (custom_status['text'] if custom_status else "Idling"),
                "primary_subtitle": processed_activities[0]['description'] if processed_activities else "No active tasks"
            }
        }
    }
    
    return jsonify(response)

@app.route('/')
def home():
    return """<style>body{background:#111;color:#eee;font-family:sans-serif;}</style>
    <h1>TITAN API: GOD MODE ACTIVE</h1>
    <p>Endpoint: <code>/api/godmode/[USER_ID]</code></p>
    <p>Use this JSON data to build ANY overlay you want.</p>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
