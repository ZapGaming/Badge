import os
import time
import requests
import html
import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =========================
#       CONFIG CORE
# =========================
HEADERS = {
    'User-Agent': 'Titan-GodMode/v101-Fixed',
    'Cache-Control': 'no-cache'
}
CACHE = {}
CACHE_TTL = 15 # Refresh every 15s

# BITWISE FLAGS MAP
PUBLIC_FLAGS = {
    1: "Discord Employee", 2: "Partnered Server Owner", 4: "HypeSquad Events",
    8: "Bug Hunter Level 1", 64: "House Bravery", 128: "House Brilliance",
    256: "House Balance", 512: "Early Supporter", 16384: "Bug Hunter Level 2",
    131072: "Early Verified Bot Developer", 4194304: "Active Developer"
}

# LINK TEMPLATES (Variable name fixed!)
LINK_TEMPLATES = {
    "github": "https://github.com/{}", 
    "twitter": "https://x.com/{}", "x": "https://x.com/{}",
    "reddit": "https://reddit.com/u/{}", 
    "steam": "https://steamcommunity.com/profiles/{}", 
    "twitch": "https://twitch.tv/{}", 
    "youtube": "https://youtube.com/@{}", 
    "spotify": "https://open.spotify.com/user/{}", 
    "instagram": "https://instagram.com/{}", 
    "facebook": "https://facebook.com/{}",
    "tiktok": "https://tiktok.com/@{}",
    "linkedin": "https://linkedin.com/in/{}",
    "battlenet": "#", 
    "xbox": "https://account.xbox.com/en-us/Profile?GamerTag={}",
    "playstation": "https://my.playstation.com/profile/{}",
    "leagueoflegends": "#", 
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
        return "https://cdn.discordapp.com/embed/avatars/0.png"
    ext = "gif" if str(hash_val).startswith("a_") else "png"
    return f"https://cdn.discordapp.com/avatars/{uid}/{hash_val}.{ext}?size=512"

def resolve_banner(uid, hash_val):
    if not hash_val: return None
    ext = "gif" if str(hash_val).startswith("a_") else "png"
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
#     API ROUTES
# =========================

@app.route('/api/godmode/<uid>')
@app.route('/api/data/<uid>') # Dual-route support
def get_full_data(uid):
    start_bench = time.perf_counter()
    
    # 1. CACHE CHECK
    now_ts = time.time()
    if uid in CACHE:
        if now_ts - CACHE[uid]['ts'] < CACHE_TTL:
            return jsonify(CACHE[uid]['data'])

    # 2. HARVEST DATA
    lanyard = {}
    dcdn = {}
    
    # Fetch DCDN
    try:
        r_d = requests.get(f"https://dcdn.dstn.to/profile/{uid}", headers=HEADERS, timeout=4)
        if r_d.status_code == 200: dcdn = r_d.json()
    except: pass
    
    # Fetch Lanyard
    try:
        r_l = requests.get(f"https://api.lanyard.rest/v1/users/{uid}", headers=HEADERS, timeout=4)
        if r_l.status_code == 200:
            res = r_l.json()
            if res.get('success'): lanyard = res['data']
    except: pass
    
    # Fail Check
    if not lanyard and not dcdn:
        return jsonify({"success": False, "error": "No Data Found. Is user in Lanyard server?"}), 404

    # 3. MERGE & COMPUTE
    u_lan = lanyard.get('discord_user', {})
    u_dcdn = dcdn.get('user', {})
    
    # --- IDENTITY ---
    username = u_dcdn.get('username') or u_lan.get('username')
    display_name = u_dcdn.get('global_name') or u_lan.get('global_name') or username
    discriminator = u_lan.get('discriminator') or u_dcdn.get('discriminator')
    
    av_hash = u_dcdn.get('avatar') or u_lan.get('avatar')
    bn_hash = u_dcdn.get('banner') 
    deco_hash = u_dcdn.get('avatar_decoration_data', {}).get('asset') # try nested data first
    if not deco_hash: deco_hash = u_dcdn.get('avatar_decoration')

    accent = u_dcdn.get('accent_color')
    accent_hex = f"#{accent:06x}" if accent else "#5865F2"
    
    # Legacy DCDN Badges
    badges_visual = []
    for b in dcdn.get('badges', []):
        badges_visual.append({
            "name": b['id'],
            "icon_url": f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png",
            "description": b.get('description', b['id'])
        })
    
    # Decoded Flags
    flags_int = u_dcdn.get('public_flags') or u_lan.get('public_flags', 0)
    
    # Connections
    connections = []
    for c in dcdn.get('connected_accounts', []):
        ctype = c['type']
        cid = c['id']
        cname = c['name']
        
        # Link Logic (Fixed variable reference here)
        link = "#"
        if ctype in LINK_TEMPLATES:
            # Handle Steam special case
            fill_val = cid if ctype == 'steam' else cname
            link = LINK_TEMPLATES[ctype].format(fill_val)
            
        connections.append({
            "platform": ctype,
            "username": cname,
            "id": cid,
            "verified": c.get('verified', False),
            "url": link,
            "icon_svg": f"{ICON_CDN}/{ctype.replace('.','dot')}.svg"
        })

    # --- PRESENCE ---
    platforms = []
    if lanyard.get('active_on_discord_desktop'): platforms.append('desktop')
    if lanyard.get('active_on_discord_mobile'): platforms.append('mobile')
    if lanyard.get('active_on_discord_web'): platforms.append('web')
    
    activities_rich = []
    spotify = None
    
    # A. Spotify
    if lanyard.get('spotify'):
        s = lanyard['spotify']
        timers = get_timestamps_data(s['timestamps']['start'], s['timestamps']['end'])
        spotify = {
            "type_id": "spotify",
            "name": "Spotify",
            "track": s['song'],
            "artist": s['artist'],
            "album": s['album'],
            "assets": { "large_image": s['album_art_url'] },
            "timestamps": timers,
            "is_music": True
        }
        # Add to main activity list for compatibility
        activities_rich.append(spotify)

    # B. Rich Presence
    for act in lanyard.get('activities', []):
        if act['type'] == 4: continue # custom status skip
        if act.get('id') == 'spotify:1': continue # dupe skip
        
        app_id = act.get('application_id')
        assets = act.get('assets', {})
        
        # Verb
        type_str = "PLAYING"
        if act['type'] == 1: type_str = "STREAMING"
        if act['type'] == 2: type_str = "LISTENING"
        if act['type'] == 3: type_str = "WATCHING"
        if act['type'] == 5: type_str = "COMPETING"
        
        # Timestamps
        t_meta = None
        ts_raw = act.get('timestamps', {})
        if ts_raw:
             t_meta = get_timestamps_data(ts_raw.get('start'), ts_raw.get('end'))

        activities_rich.append({
            "type_id": act['type'],
            "type_text": type_str,
            "name": act.get('name'),
            "state": act.get('state'),
            "details": act.get('details'),
            "app_id": app_id,
            "assets": {
                "large_image": resolve_activity_image(app_id, assets.get('large_image')),
                "large_text": assets.get('large_text'),
                "small_image": resolve_activity_image(app_id, assets.get('small_image')),
                "small_text": assets.get('small_text')
            },
            "timestamps": t_meta,
            "is_rich_presence": True
        })

    # C. Custom Status
    custom_status = None
    for act in lanyard.get('activities', []):
        if act['type'] == 4:
            emoji_url = None
            if act.get('emoji'):
                e_id = act['emoji'].get('id')
                ext = "gif" if act['emoji'].get('animated') else "png"
                if e_id: emoji_url = f"https://cdn.discordapp.com/emojis/{e_id}.{ext}"
                
            custom_status = {
                "text": act.get('state'),
                "emoji_name": act.get('emoji', {}).get('name'),
                "emoji_url": emoji_url
            }
            break

    # 4. FINAL RESPONSE
    response = {
        "success": True,
        "meta": {
            "version": "Titan v101",
            "latency": round((time.perf_counter() - start_bench) * 1000, 2),
            "cached": False
        },
        "user": {
            "id": uid,
            "username": username,
            "display_name": display_name,
            "avatar_url": resolve_avatar(uid, av_hash),
            "banner_url": resolve_banner(uid, bn_hash),
            "avatar_decoration": resolve_decoration(deco_hash),
            "created_at": get_snowflake_date(uid),
            "bio": bio, # Lanyard KV + DCDN merged
        },
        "theme": {
            "accent_color": accent_hex,
            "text_contrast": calc_contrast(accent_hex)
        },
        "status": {
            "status": lanyard.get('discord_status', 'offline'),
            "active_on": platforms,
            "is_mobile": lanyard.get('active_on_discord_mobile', False),
            "custom": custom_status
        },
        "profile": {
            "badges_array": badges_visual, # URLs
            "badges_flags": decode_flags(flags_int), # Names
            "connections": connected_accounts # Rich Objects with Links
        },
        "activities": {
            "current_spotify": spotify,
            "all": activities_rich
        },
        # Simplified keys for frontend ease
        "smart": {
             "art": spotify['assets']['large_image'] if spotify else (activities_rich[0]['assets']['large_image'] if activities_rich else None)
        }
    }
    
    CACHE[uid] = {'ts': now_ts, 'data': response}
    # Update cache marker
    response['meta']['cached'] = True 
    return jsonify(response)

@app.route('/')
def index():
    return """
    <html>
      <body style='background:#111;color:#eee;font-family:sans-serif;text-align:center;'>
        <h1 style='color:#0f0'>TITAN API: GOD MODE</h1>
        <p>Unified Discord Data Aggregator Online</p>
        <p>GET <a style='color:#0ff' href='/api/data/1173155162093785099'>/api/data/&lt;user_id&gt;</a></p>
      </body>
    </html>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
