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
HEADERS = {'User-Agent': 'HyperBadge/Stable-v38'}
# 1x1 Transparent Pixel
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

CACHE = {} 
# Icon Cache
CONN_MAP = {
    "github": "github", "steam": "steam", "twitch": "twitch", "spotify": "spotify",
    "twitter": "x", "reddit": "reddit", "youtube": "youtube",
    "xbox": "xbox", "playstation": "playstation", "tiktok": "tiktok", "instagram": "instagram"
}
SIMPLE_ICONS_BASE = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/"

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text)
    # Remove control chars (0-31) except newline
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    # Standard XML escaping
    return html.escape(text, quote=True)

def get_base64(url, is_svg=False):
    """Robust image fetcher"""
    if not url: return EMPTY
    try:
        # Convert Discord MP Urls
        if url.startswith("mp:"): url = f"https://media.discordapp.net/{url[3:]}"
        
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            mime = "image/svg+xml" if (is_svg or url.endswith(".svg")) else "image/png"
            return f"data:{mime};base64,{base64.b64encode(r.content).decode('utf-8')}"
    except: pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Outfit:wght@400;500;800;900&amp;family=Pacifico&amp;family=Poppins:wght@400;600&amp;display=swap');"
    keyframes = """
    @keyframes d { from{transform:scale(1.02) rotate(0deg)} to{transform:scale(1.05) rotate(0.5deg)} }
    @keyframes slide { 0%{transform:translateX(-10px);opacity:0} 100%{transform:translateX(0);opacity:1} }
    @keyframes pop { 0%{transform:scale(0); opacity:0} 100%{transform:scale(1); opacity:1} }
    @keyframes pulse { 0%{opacity:0.6} 50%{opacity:1} 100%{opacity:0.6} }
    @keyframes glint { 0% {transform:translateX(-100%)} 100% {transform:translateX(100%)} }
    """
    classes = ""
    if str(bg_anim).lower() != 'false': classes += ".bg-drift{animation:d 40s linear infinite alternate} .pulsing{animation:pulse 3s infinite} .shiny{animation:glint 5s infinite}"
    if str(fg_anim).lower() != 'false': classes += ".slide-in{animation:slide 0.8s ease-out} .badge-pop{animation:pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) backwards}"
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
            # --- A. Fetch Profile (DCDN) ---
            dcdn_user = {}
            badges_data = []
            connections_data = []
            
            try:
                r_prof = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=3)
                if r_prof.status_code == 200:
                    prof_json = r_prof.json()
                    if 'user' in prof_json:
                        dcdn_user = prof_json['user']
                        # Badges
                        for b in prof_json.get('badges', []):
                            badges_data.append(get_base64(f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png"))
                        # Connections
                        seen_types = set()
                        for c in prof_json.get('connected_accounts', []):
                            ctype = c['type']
                            if ctype in CONN_MAP and ctype not in seen_types:
                                c_url = f"{SIMPLE_ICONS_BASE}{CONN_MAP[ctype]}.svg"
                                connections_data.append(get_base64(c_url, is_svg=True))
                                seen_types.add(ctype)
            except: pass

            # --- B. Fetch Presence (Lanyard) ---
            r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            lan_json = r_lan.json()
            if not lan_json.get('success'): 
                return None 
            
            d = lan_json['data']
            u = d['discord_user']
            status = d['discord_status']
            
            # --- COLOR & ACTIVITY LOGIC ---
            cols = {"online": "#23a55a", "idle": "#f0b232", "dnd": "#f23f42", "offline": "#80848e", "spotify": "#1DB954"}
            main_act = None

            # 1. Spotify
            if d.get('spotify'):
                s = d['spotify']
                main_act = {
                    "header": "LISTENING TO SPOTIFY",
                    "title": s['song'],
                    "detail": s['artist'],
                    "image": s.get('album_art_url'),
                    "color": cols['spotify']
                }
            # 2. Rich Presence
            elif d.get('activities'):
                for act in d['activities']:
                    if act['type'] == 4: continue 
                    img_url = None
                    if 'assets' in act and 'large_image' in act['assets']:
                        app_id = act['application_id']
                        img_id = act['assets']['large_image']
                        if img_id.startswith("mp:"): img_url = f"https://media.discordapp.net/{img_id[3:]}"
                        else: img_url = f"https://cdn.discordapp.com/app-assets/{app_id}/{img_id}.png"
                    
                    header = "PLAYING" if act['type'] == 0 else "WATCHING"
                    main_act = {
                        "header": f"{header} {act['name'].upper()}",
                        "title": act.get('details') or act['name'],
                        "detail": act.get('state') or "",
                        "image": img_url,
                        "color": cols.get(status, "#5865F2")
                    }
                    break
            
            # 3. Idle / Custom
            if not main_act:
                msg = args.get('idleMessage', 'Chilling')
                for act in d.get('activities', []):
                    if act['type'] == 4: msg = act.get('state', msg); break
                
                header_stat = "OFFLINE" if status == 'offline' else "CURRENTLY"
                
                main_act = {
                    "header": header_stat, "title": msg, "detail": "",
                    "image": None, "color": cols.get(status, "#555")
                }

            # Naming & Assets
            final_name = force_name if force_name else (dcdn_user.get('global_name') or u['global_name'] or u['username'])
            u_avatar = get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png")
            
            banner_final = None
            if dcdn_user.get('banner'):
                banner_final = get_base64(dcdn_user['banner'])
            
            # Use Avatar as BG if Banner Missing
            final_bg = banner_final if banner_final else u_avatar

            return {
                "type": "user",
                "name": sanitize_xml(final_name),
                "title": sanitize_xml(main_act['title']),
                "detail": sanitize_xml(main_act['detail']),
                "app_name": sanitize_xml(main_act['header']),
                "color": main_act['color'],
                "status_color": cols.get(status, "#80848e"),
                "avatar": u_avatar,
                "banner_image": final_bg,
                "act_image": get_base64(main_act['image']) if main_act['image'] else None,
                "bio": sanitize_xml(dcdn_user.get('bio', 'No Bio Set.')),
                "badges": badges_data,
                "connections": connections_data,
                "sub_id": u['id']
            }

    except Exception as e:
        print(f"Fetch Error: {e}")
        return None

# ===========================
#      RENDER ENGINE
# ===========================

def render_mega_profile(d, css, radius, bg_col):
    """Titan V38: Fixed Variable names"""
    
    # 1. BG
    bg_svg = f"""
    <rect width="100%" height="100%" fill="#{bg_col}" />
    <image href="{d['banner_image']}" width="100%" height="150%" y="-15%" preserveAspectRatio="xMidYMid slice" opacity="0.4" filter="url(#heavyBlur)" class="bg-drift"/>
    <rect width="100%" height="100%" fill="url(#vig)"/>
    """

    # 2. Activity Image Logic
    if d['act_image']:
        act_viz = f"""
        <image href="{d['act_image']}" x="20" y="165" width="80" height="80" rx="12" />
        <rect x="20" y="165" width="80" height="80" rx="12" fill="none" stroke="rgba(255,255,255,0.15)"/>
        """
        # THE FIX: DEFINING THE VARIABLE HERE
        txt_start_x = 115
    else:
        act_viz = f"""
        <rect x="20" y="165" width="80" height="80" rx="12" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.1)"/>
        <text x="60" y="215" text-anchor="middle" font-size="28" fill="{d['color']}">⚡</text>
        """
        # THE FIX: DEFINING THE VARIABLE HERE TOO
        txt_start_x = 115

    # 3. Badges Row
    badge_group = ""
    bx = 0
    for i, b in enumerate(d.get('badges', [])[:6]):
        badge_group += f'<image href="{b}" x="{bx}" y="0" width="22" height="22" class="badge-pop" style="animation-delay:{i*0.05}s"/>'
        bx += 26
        
    # 4. Connections Row
    conn_group = ""
    cx = 0
    for i, c in enumerate(d.get('connections', [])[:5]):
         conn_group += f'<image href="{c}" x="{cx}" y="0" width="20" height="20" filter="url(#invert)" opacity="0.7"/>'
         cx += 28

    t_tit = d['title'][:32] + (".." if len(d['title']) > 32 else "")

    return f"""<svg width="600" height="290" viewBox="0 0 600 290" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}
          .b {{ font-family: 'Outfit', sans-serif; font-weight: 800; }}
          .m {{ font-family: 'JetBrains Mono', monospace; font-weight: 500; }}
          .s {{ font-family: 'Pacifico', cursive; }}
          .p {{ font-family: 'Poppins', sans-serif; font-weight: 400; }}
        </style>
        
        <clipPath id="cp"><rect width="600" height="290" rx="{radius}"/></clipPath>
        <clipPath id="avc"><circle cx="65" cy="65" r="65"/></clipPath>
        
        <!-- Filters -->
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="30"/></filter>
        <filter id="invert"><feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"/></filter>
        <filter id="ds"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.6"/></filter>
        <linearGradient id="vig" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="black" stop-opacity="0.3"/><stop offset="1" stop-color="#000" stop-opacity="0.95"/></linearGradient>
        <linearGradient id="glint" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="white" stop-opacity="0.05"/><stop offset="0.5" stop-color="white" stop-opacity="0"/></linearGradient>
      </defs>

      <!-- BASE -->
      <g clip-path="url(#cp)">
        {bg_svg}
        <rect width="600" height="290" fill="url(#glint)" class="shiny"/>
        <rect width="596" height="286" x="2" y="2" rx="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="2"/>
      </g>
      
      <!-- TOP LEFT -->
      <g transform="translate(30, 30)">
         <circle cx="65" cy="65" r="70" fill="none" stroke="{d['color']}" stroke-width="3" stroke-dasharray="20 10" opacity="0.6" class="bg-drift"/>
         <g clip-path="url(#avc)"><image href="{d['avatar']}" width="130" height="130"/></g>
         <circle cx="110" cy="110" r="16" fill="#121212"/>
         <circle cx="110" cy="110" r="11" fill="{d['status_color']}" class="pulsing"/>
      </g>
      
      <!-- TOP RIGHT: Name / Bio / Badges -->
      <g transform="translate(180, 40)">
          <text x="0" y="25" class="s" font-size="44" fill="white" filter="url(#ds)">{d['name']}</text>
          
          <g transform="translate(5, -20)">{badge_group}</g>
          
          <foreignObject x="0" y="45" width="380" height="40">
             <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'Poppins',sans-serif; font-size:12px; color:#ccc; line-height:1.4; overflow:hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">
               {d['bio']}
             </div>
          </foreignObject>
      </g>
      
      <!-- BOTTOM: Activity + Connections -->
      <g transform="translate(30, 190)" class="slide-in">
          <rect width="540" height="85" rx="16" fill="rgba(30,30,35,0.5)" stroke="{d['color']}" stroke-opacity="0.3" stroke-width="1.5"/>
          
          {act_viz}
          
          <!-- Fix: Using the Correct txt_start_x Variable -->
          <g transform="translate({txt_start_x}, 22)">
             <text x="0" y="0" class="m" font-size="9" fill="{d['color']}" letter-spacing="1.5" font-weight="bold">{d['app_name']}</text>
             <text x="0" y="25" class="b" font-size="20" fill="white">{t_tit}</text>
             <text x="0" y="44" class="p" font-size="12" fill="#BBB">{d['detail'][:40]}</text>
             
             <!-- Connection Icons -->
             <g transform="translate(350, 0)">{conn_group}</g>
          </g>
      </g>

    </svg>"""

# ===========================
#        CONTROLLER
# ===========================
@app.route('/superbadge/<key>')
def handler(key):
    args = request.args
    # Detect Mode
    mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    data = fetch_data(key, mode, args)
    
    if not data:
         return Response('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="100"><rect width="100%" height="100%" fill="#111"/><text x="20" y="60" fill="red" font-family="sans-serif">LOAD ERROR</text></svg>', mimetype="image/svg+xml")

    # Render settings
    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '111111').replace('#','')
    radius = args.get('borderRadius', '30').replace('px', '') 

    css = get_css(bg_an, fg_an)
    svg = render_mega_profile(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

@app.route('/')
def home(): return "TITAN HYBRID V38 ONLINE"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
