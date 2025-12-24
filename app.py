import base64
import requests
import os
import html
import re
import time
from flask import Flask, Response, request

app = Flask(__name__)

# ===========================
#        CONFIGURATION
# ===========================
HEADERS = {'User-Agent': 'HyperBadge/Hybrid-v36'}
# 1x1 Transparent Pixel
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
CACHE = {}

# Mappings for Connected Accounts (Icons)
CONN_MAP = {
    "github": "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/github.svg",
    "steam": "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/steam.svg",
    "twitch": "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/twitch.svg",
    "spotify": "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/spotify.svg",
    "twitter": "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/x.svg",
    "reddit": "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/reddit.svg",
    "youtube": "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/youtube.svg",
    "xbox": "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/xbox.svg",
    "playstation": "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/playstation.svg",
}

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text)
    # Strip invisible control characters (ASCII 0-31 except tab/newline)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    # Escape
    return html.escape(text, quote=True)

def get_base64(url, is_svg=False):
    """Robust image fetcher"""
    if not url: return EMPTY
    try:
        # Convert Discord MP Urls
        if url.startswith("mp:"): url = f"https://media.discordapp.net/{url[3:]}"
        
        r = requests.get(url, headers=HEADERS, timeout=3)
        if r.status_code == 200:
            mime = "image/svg+xml" if is_svg or url.endswith(".svg") else "image/png"
            return f"data:{mime};base64,{base64.b64encode(r.content).decode('utf-8')}"
    except: pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Outfit:wght@400;500;800&amp;family=Pacifico&amp;family=Poppins:wght@400;600&amp;display=swap');"
    keyframes = """
    @keyframes d { from{transform:scale(1.02) rotate(0deg)} to{transform:scale(1.05) rotate(0.5deg)} }
    @keyframes slide { 0%{transform:translateY(10px);opacity:0} 100%{transform:translateY(0);opacity:1} }
    @keyframes pop { 0%{transform:scale(0); opacity:0} 100%{transform:scale(1); opacity:1} }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    @keyframes p { 0%{stroke-opacity:0.8} 50%{stroke-opacity:0.4} 100%{stroke-opacity:0.8} }
    """
    classes = ""
    if str(bg_anim).lower() != 'false': classes += ".bg-drift{animation:d 40s linear infinite alternate}"
    if str(fg_anim).lower() != 'false': classes += ".slide-in{animation:slide 0.8s ease-out} .badge-pop{animation:pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) backwards} .status-pulse{animation:p 2s infinite}"
    return css + keyframes + classes

# ===========================
#      DATA LOGIC (HYBRID)
# ===========================

def fetch_data(key, type_mode, args):
    try:
        force_name = args.get('name')

        # 1. DISCORD SERVER
        if type_mode == 'discord':
            r = requests.get(f"https://discord.com/api/v10/invites/{key}?with_counts=true", headers=HEADERS, timeout=4)
            d = r.json(); g = d.get('guild')
            if not g: return None
            return {
                "type": "discord",
                "name": sanitize_xml(force_name or g['name']), 
                "title": f"{d.get('approximate_member_count', 0):,} Members",
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY
            }

        # 2. USER MODE
        else:
            # --- FETCH LANYARD (Live Activity) ---
            # Used for: Spotify, Games, Status Color, Online Status
            lan_data = {}
            try:
                r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
                if r_lan.status_code == 200:
                    lan_json = r_lan.json()
                    if lan_json.get('success'): lan_data = lan_json['data']
            except: pass
            
            if not lan_data: return None # Must have Lanyard to work

            u = lan_data['discord_user']
            status = lan_data['discord_status']

            # --- FETCH DCDN (Profile Enrichment) ---
            # Used for: Banner, Bio, Badges, Connected Accounts
            dcdn_user = {}
            try:
                r_prof = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=4)
                if r_prof.status_code == 200: dcdn_user = r_prof.json()
            except: pass
            
            # --- ASSET PROCESSING ---
            
            # 1. Banner (Prefer DCDN, Fallback to User Color logic later)
            banner_url = dcdn_user.get('user', {}).get('banner') 
            banner_img = get_base64(banner_url) if banner_url else None
            
            # 2. Bio (Prefer DCDN, Fallback to Lanyard KV)
            bio_text = dcdn_user.get('user', {}).get('bio')
            if not bio_text and lan_data.get('kv'):
                bio_text = lan_data['kv'].get('bio', '')
            if not bio_text: bio_text = "No bio available."

            # 3. Badges (Iterate DCDN badges which have icon URLs)
            user_badges = []
            for b in dcdn_user.get('badges', []):
                user_badges.append(get_base64(b['icon']))
            
            # 4. Connections (Iterate DCDN connected_accounts)
            user_conns = []
            seen_conns = set()
            for c in dcdn_user.get('connected_accounts', []):
                ctype = c['type']
                if ctype in CONN_MAP and ctype not in seen_conns:
                    user_conns.append(get_base64(CONN_MAP[ctype], is_svg=True))
                    seen_conns.add(ctype)
                    if len(user_conns) >= 4: break # Max 4 connections

            # 5. Platforms (Lanyard)
            platforms = []
            if lan_data.get('active_on_discord_desktop'): platforms.append("desktop")
            if lan_data.get('active_on_discord_mobile'): platforms.append("mobile")
            if lan_data.get('active_on_discord_web'): platforms.append("web")

            # --- ACTIVITY LOGIC ---
            cols = {"online": "#23a55a", "idle": "#f0b232", "dnd": "#f23f42", "offline": "#80848e", "spotify": "#1DB954"}
            main_act = None

            # A. Spotify
            if lan_data.get('spotify'):
                s = lan_data['spotify']
                main_act = {
                    "header": "LISTENING TO SPOTIFY",
                    "title": s['song'],
                    "detail": s['artist'],
                    "image": s.get('album_art_url'),
                    "color": cols['spotify']
                }
            # B. Rich Presence
            elif lan_data.get('activities'):
                for act in lan_data['activities']:
                    if act['type'] == 4: continue
                    img_url = None
                    if 'assets' in act and 'large_image' in act['assets']:
                        app_id = act['application_id']
                        img_id = act['assets']['large_image']
                        if img_id.startswith("mp:"): img_url = f"https://media.discordapp.net/{img_id[3:]}"
                        else: img_url = f"https://cdn.discordapp.com/app-assets/{app_id}/{img_id}.png"
                    
                    header = f"PLAYING {act['name'].upper()}" if act['type']==0 else "ACTIVITY"
                    main_act = {
                        "header": header,
                        "title": act.get('details', act['name']),
                        "detail": act.get('state', ''),
                        "image": img_url,
                        "color": cols.get(status, "#5865F2")
                    }
                    break
            
            # C. Idle
            if not main_act:
                msg = args.get('idleMessage', 'Chilling')
                for act in lan_data.get('activities', []):
                    if act['type'] == 4: msg = act.get('state', msg); break
                
                main_act = {
                    "header": "CURRENT STATUS",
                    "title": msg, "detail": "", "image": None, 
                    "color": cols.get(status, "#555")
                }

            # Naming
            final_name = force_name if force_name else (u.get('global_name') or u['username'])
            u_avatar = get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png")
            final_bg = banner_img if banner_img else u_avatar

            return {
                "type": "user",
                "name": sanitize_xml(final_name),
                "title": sanitize_xml(main_act['title']),
                "detail": sanitize_xml(main_act['detail']),
                "app_name": sanitize_xml(main_act['header']),
                "color": main_act['color'],
                "avatar": u_avatar,
                "banner_image": final_bg,
                "act_image": get_base64(main_act['image']) if main_act['image'] else None,
                "bio": sanitize_xml(bio_text),
                "badges": user_badges,
                "connections": user_conns,
                "platforms": platforms,
                "sub_id": u['id'],
                "status_color": cols.get(status, "#80848e")
            }

    except Exception as e:
        print(f"Hybrid Fetch Error: {e}")
        return None

# ===========================
#      MEGA RENDERER
# ===========================

def render_mega_profile(d, css, radius, bg_col):
    """
    Visuals:
    1. Banner + Blur.
    2. Overlapping Avatar + Status.
    3. Badges (Top Right).
    4. Bio + Name.
    5. Bottom: Connections (Left) + Activity (Center/Right).
    """

    # 1. Background
    bg_svg = f"""
    <rect width="100%" height="100%" fill="#{bg_col}" />
    <image href="{d['banner_image']}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.4" filter="url(#heavyBlur)" class="bg-drift"/>
    <rect width="100%" height="100%" fill="url(#vig)"/>
    """

    # 2. Rows for Icons
    # Badges
    badges_svg = ""
    bx = 0
    for i, b in enumerate(d.get('badges', [])): 
        badges_svg += f'<image href="{b}" x="{bx}" y="0" width="20" height="20" class="badge-pop" style="animation-delay:{i*0.1}s"/>'
        bx += 24
        
    # Connections
    conns_svg = ""
    cx = 0
    for i, c in enumerate(d.get('connections', [])):
        conns_svg += f'<rect x="{cx}" y="0" width="22" height="22" rx="4" fill="#222"/><image href="{c}" x="{cx+3}" y="3" width="16" height="16" opacity="0.8"/>'
        cx += 28

    # Activity Visual
    if d['act_image']:
        act_vis = f"""<image href="{d['act_image']}" x="20" y="15" width="60" height="60" rx="10" />"""
        txt_pos = 95
    else:
        act_vis = f"""<rect x="20" y="15" width="60" height="60" rx="10" fill="rgba(255,255,255,0.05)"/><text x="50" y="55" text-anchor="middle" font-family="Outfit" font-size="24" fill="{d['color']}">⚡</text>"""
        txt_pos = 95

    t_tit = d['title'][:32] + ".." if len(d['title']) > 32 else d['title']

    return f"""<svg width="600" height="290" viewBox="0 0 600 290" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}
          .b {{ font-family: 'Outfit', sans-serif; font-weight: 800; }}
          .m {{ font-family: 'JetBrains Mono', monospace; font-weight: 500; }}
          .bio {{ font-family: 'Poppins', sans-serif; font-weight: 400; opacity: 0.8; }}
          .script {{ font-family: 'Pacifico', cursive; }}
        </style>
        
        <clipPath id="cp"><rect width="600" height="290" rx="{radius}"/></clipPath>
        <clipPath id="avc"><circle cx="60" cy="60" r="60"/></clipPath>
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="30"/></filter>
        <filter id="ds"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.5"/></filter>
        <linearGradient id="vig" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="black" stop-opacity="0.3"/><stop offset="1" stop-color="black" stop-opacity="0.8"/></linearGradient>
      </defs>

      <g clip-path="url(#cp)">
        {bg_svg}
        <rect width="596" height="286" x="2" y="2" rx="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="2"/>
      </g>
      
      <!-- TOP: Avatar + Identity -->
      <g transform="translate(30, 30)">
         <circle cx="60" cy="60" r="66" fill="none" stroke="{d['color']}" stroke-width="3" stroke-dasharray="20 10" opacity="0.6" class="bg-drift"/>
         <g clip-path="url(#avc)"><image href="{d['avatar']}" width="120" height="120"/></g>
         <circle cx="105" cy="105" r="16" fill="#121212"/>
         <circle cx="105" cy="105" r="10" fill="{d['status_color']}" class="status-pulse"/>
      </g>

      <g transform="translate(170, 45)">
         <!-- Badges Row -->
         <g transform="translate(0, -15)">{badge_svg}</g>
         
         <text x="0" y="25" class="script" font-size="44" fill="white" filter="url(#ds)">{d['name']}</text>
         
         <text x="5" y="48" class="m" font-size="10" fill="#AAA">UID: {d['sub_id']}</text>
         
         <foreignObject x="0" y="60" width="400" height="45">
             <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'Poppins';font-size:12px;color:#ccc;line-height:1.3;overflow:hidden;text-overflow:ellipsis;white-space:normal;max-height:42px">
                {d['bio']}
             </div>
         </foreignObject>
      </g>

      <!-- BOTTOM: Activity Panel -->
      <g transform="translate(30, 190)" class="slide-in">
          <rect width="540" height="85" rx="16" fill="rgba(15,15,20,0.6)" stroke="{d['color']}" stroke-opacity="0.3" stroke-width="1.5"/>
          {act_vis}
          <g transform="translate({txt_pos}, 22)">
             <text x="0" y="0" class="m" font-size="9" fill="{d['color']}" letter-spacing="1.5" font-weight="bold">{d['app_name']}</text>
             <text x="0" y="25" class="b" font-size="20" fill="white">{t_tit}</text>
             <text x="0" y="44" class="bio" font-size="12" fill="#999">{d['detail'][:40]}</text>
          </g>
          
          <!-- Connections Bottom Right -->
          <g transform="translate(430, 50)">
             {conns_svg}
          </g>
      </g>

    </svg>"""

@app.route('/superbadge/<key>')
def handler(key):
    args = request.args
    # Detect
    mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    
    data = fetch_data(key, mode, args)
    if not data: return Response('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="100"><rect width="100%" height="100%" fill="#111"/><text x="20" y="60" fill="red">DATA FAILURE</text></svg>
