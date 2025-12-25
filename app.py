import os
import time
import requests
import datetime
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =======================
#    CONFIGURATION
# =======================
HEADERS = {
    'User-Agent': 'Titan-API/v63 (Hyper-Aggregator)'
}

CACHE = {}
CACHE_TTL = 15  # 15 seconds cache

# 1. ICON SOURCE
ICON_BASE = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons"

# 2. DEEP LINKING MAP
# This builds real URLs for connections found in the profile
LINK_PATTERNS = {
    "github": "https://github.com/{}",
    "twitter": "https://x.com/{}",
    "x": "https://x.com/{}",
    "reddit": "https://reddit.com/u/{}",
    "twitch": "https://twitch.tv/{}",
    "youtube": "https://youtube.com/{}",
    "steam": "https://steamcommunity.com/profiles/{}", # DCDN typically returns ID for Steam
    "spotify": "https://open.spotify.com/user/{}",
    "instagram": "https://instagram.com/{}",
    "tiktok": "https://tiktok.com/@{}",
    "facebook": "https://facebook.com/{}",
    "xbox": "https://account.xbox.com/en-us/Profile?GamerTag={}",
    "paypal": "https://paypal.me/{}",
    "ebay": "https://www.ebay.com/usr/{}",
    "domain": "https://{}",
    "bsky": "https://bsky.app/profile/{}"
}

# =======================
#    MATH & HELPERS
# =======================

def get_cdn_url(cat, id, hash_val, anim=False, size=512):
    if not hash_val: return None
    ext = "gif" if (anim and str(hash_val).startswith("a_")) else "png"
    return f"https://cdn.discordapp.com/{cat}/{id}/{hash_val}.{ext}?size={size}"

def get_calc_time(start, end):
    """Generates progress math for Music/Movies"""
    now = time.time() * 1000
    
    obj = {
        "start_unix": start,
        "end_unix": end,
        "now_unix": now
    }
    
    if start:
        elapsed = now - start
        obj['elapsed_ms'] = elapsed
        obj['elapsed_str'] = time.strftime('%H:%M:%S', time.gmtime(elapsed/1000)) if elapsed > 3600000 else time.strftime('%M:%S', time.gmtime(elapsed/1000))

    if start and end:
        total = end - start
        if total > 0:
            pct = min(max((elapsed / total) * 100, 0), 100)
            obj['duration_ms'] = total
            obj['progress_percent'] = round(pct, 4) # Precision for smooth bars
            
            # Remaining time
            left = end - now
            prefix = "-" if left > 0 else "+"
            obj['remaining_str'] = prefix + time.strftime('%M:%S', time.gmtime(abs(left)/1000))
    
    return obj

def resolve_rp_img(app_id, img_id):
    if not img_id: return None
    if str(img_id).startswith("mp:"): return f"https://media.discordapp.net/{img_id.replace('mp:','')}"
    if str(img_id).startswith("spotify:"): return f"https://i.scdn.co/image/{img_id.replace('spotify:','')}"
    return f"https://cdn.discordapp.com/app-assets/{app_id}/{img_id}.png"

# =======================
#    MAIN ENDPOINT
# =======================

@app.route('/api/data/<uid>')
def get_user_full(uid):
    now_ts = time.time()
    
    # --- CACHE CHECK ---
    if uid in CACHE:
        if now_ts - CACHE[uid]['time'] < CACHE_TTL:
            return jsonify(CACHE[uid]['data'])

    # --- 1. FETCH RAW DATA ---
    lanyard = {}
    dcdn = {}
    
    # Fetch DCDN (Profile Meta)
    try:
        r1 = requests.get(f"https://dcdn.dstn.to/profile/{uid}", headers=HEADERS, timeout=4)
        if r1.status_code == 200: dcdn = r1.json()
    except: pass
    
    # Fetch Lanyard (Presence)
    try:
        r2 = requests.get(f"https://api.lanyard.rest/v1/users/{uid}", headers=HEADERS, timeout=4)
        if r2.status_code == 200: lanyard = r2.json().get('data', {})
    except: pass
    
    if not lanyard and not dcdn:
        return jsonify({"success": False, "error": "USER_NOT_FOUND"}), 404

    u_lan = lanyard.get('discord_user', {})
    u_dcdn = dcdn.get('user', {})

    # --- 2. IDENTITY PROCESSING ---
    user_id = uid
    username = u_lan.get('username') or u_dcdn.get('username')
    display_name = u_lan.get('global_name') or u_dcdn.get('global_name') or username
    discriminator = u_lan.get('discriminator') or "0"

    # Avatar
    av_hash = u_lan.get('avatar') or u_dcdn.get('avatar')
    avatar_url = get_cdn_url("avatars", uid, av_hash, anim=True) or "https://cdn.discordapp.com/embed/avatars/0.png"
    
    # Banner
    bn_hash = u_dcdn.get('banner') # Lanyard banners often buggy, use DCDN
    banner_url = get_cdn_url("banners", uid, bn_hash, anim=True, size=1024)
    if not banner_url and u_dcdn.get('banner_color'):
        # Fallback to solid color logic handled by client
        banner_url = None

    # Avatar Decoration (Frame)
    deco_hash = u_dcdn.get('avatar_decoration')
    deco_url = f"https://cdn.discordapp.com/avatar-decoration-presets/{deco_hash}.png" if deco_hash else None

    # Bio
    bio = u_dcdn.get('bio') or lanyard.get('kv', {}).get('bio')
    
    # Color
    color_int = u_dcdn.get('accent_color')
    accent_hex = f"#{color_int:06x}" if color_int else "#5865F2"

    # --- 3. PLATFORM & STATUS DETECTION ---
    status_overall = lanyard.get('discord_status', 'offline')
    
    # Specific Platform status (e.g. { "mobile": "online", "desktop": "dnd" })
    # Lanyard provides 'active_on_discord_X'. If true, assume it shares the main status
    platforms = {}
    if lanyard.get('active_on_discord_desktop'): platforms['desktop'] = status_overall
    if lanyard.get('active_on_discord_mobile'): platforms['mobile'] = status_overall
    if lanyard.get('active_on_discord_web'): platforms['web'] = status_overall
    
    is_mobile = bool(lanyard.get('active_on_discord_mobile'))

    # --- 4. CONNECTIONS (SMART LINKING) ---
    connections = []
    # Combine DCDN (best for list) with manual mapping
    for conn in dcdn.get('connected_accounts', []):
        c_type = conn.get('type')
        c_name = conn.get('name')
        c_id = conn.get('id')
        
        # Build URL
        c_url = "#"
        if c_type in LINK_PATTERNS:
            # Steam usually requires ID, others use Name
            identifier = c_id if c_type == 'steam' else c_name
            c_url = LINK_PATTERNS[c_type].format(identifier)

        connections.append({
            "type": c_type,
            "name": c_name,
            "id": c_id,
            "url": c_url,
            "is_verified": conn.get('verified', False),
            "icon_url": f"{ICON_BASE}/{c_type.replace('.','dot')}.svg"
        })

    # --- 5. ACTIVITY SCANNER (Rich) ---
    activities_parsed = []
    
    # A. Spotify Object
    if lanyard.get('spotify'):
        s = lanyard['spotify']
        timers = get_calc_time(s['timestamps']['start'], s['timestamps']['end'])
        activities_parsed.append({
            "type": "spotify",
            "name": "Spotify",
            "state": s['artist'],
            "details": s['song'],
            "album": s['album'],
            "assets": {
                "large_image": s['album_art_url'],
                "large_text": s['album']
            },
            "timers": timers,
            "is_listening": True
        })

    # B. Game / Apps
    for act in lanyard.get('activities', []):
        if act['id'] == 'spotify:1': continue # Duplicate skip
        
        # Custom Status (Type 4)
        if act['type'] == 4:
            # We add it, but frontends usually treat it separately
            emoji = None
            if act.get('emoji'):
                emoji_url = f"https://cdn.discordapp.com/emojis/{act['emoji']['id']}.png" if act['emoji'].get('id') else None
                emoji = {"name": act['emoji'].get('name'), "url": emoji_url}
            
            activities_parsed.append({
                "type": "custom",
                "state": act.get('state'),
                "emoji": emoji,
                "name": "Custom Status"
            })
            continue

        # Regular Rich Presence
        t_meta = None
        if 'timestamps' in act:
            t_meta = get_calc_time(act['timestamps'].get('start'), act['timestamps'].get('end'))

        # Party Info
        party_info = None
        if 'party' in act and 'size' in act['party']:
            # [current, max]
            p_cur, p_max = act['party']['size']
            party_info = f"{p_cur}/{p_max}"

        activities_parsed.append({
            "type": "game",
            "name": act.get('name'),
            "details": act.get('details'),
            "state": act.get('state'),
            "assets": {
                "large_image": resolve_rp_img(act['application_id'], act.get('assets',{}).get('large_image')),
                "large_text": act.get('assets',{}).get('large_text'),
                "small_image": resolve_rp_img(act['application_id'], act.get('assets',{}).get('small_image')),
            },
            "timestamps": t_meta,
            "party": party_info,
            "is_listening": act['type'] == 2 or act['type'] == 0
        })

    # --- 6. BADGES ---
    badges_formatted = []
    for b in dcdn.get('badges', []):
        badges_formatted.append({
            "id": b.get('id'),
            "description": b.get('description'),
            "icon_url": f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png"
        })

    # === PAYLOAD ===
    payload = {
        "success": True,
        "ts": time.time(),
        "user": {
            "id": uid,
            "username": username,
            "global_name": display_name,
            "discriminator": discriminator,
            "avatar_url": avatar_url,
            "avatar_decoration": deco_url,
            "banner_url": banner_url,
            "accent_color": accent_hex,
            "bio": bio
        },
        "presence": {
            "status": status_overall,
            "platform_status": platforms,
            "is_mobile_web": is_mobile
        },
        "connections": connections,
        "badges": badges_formatted,
        "activities": activities_parsed
    }
    
    CACHE[uid] = {'time': now_ts, 'data': payload}
    return jsonify(payload)

@app.route('/')
def home():
    return jsonify({"status": "Titan API v63 Online", "endpoint": "/api/data/<user_id>"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
