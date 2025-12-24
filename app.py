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
HEADERS = {'User-Agent': 'HyperBadge/VisualFix-v37'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
CACHE = {}

# Icon Mapping (Standardizing filenames for SimpleIcons)
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
    # Strip invisible control chars (0-31) except tab/newline
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    # Strip Raw Discord Emoji syntax to keep text clean
    text = re.sub(r'<a?:.+?:\d+>', '', text)
    return html.escape(text, quote=True)

def get_base64(url, is_svg=False):
    """Robust image fetcher"""
    if not url: return EMPTY
    try:
        # Resolve Discord Media Proxy URLs
        if url.startswith("mp:"): url = f"https://media.discordapp.net/{url[3:]}"
        
        # Check cache logic could go here
        
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            mime = "image/svg+xml" if (is_svg or url.endswith(".svg")) else "image/png"
            return f"data:{mime};base64,{base64.b64encode(r.content).decode('utf-8')}"
    except: pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Outfit:wght@400;500;800;900&amp;family=Pacifico&amp;family=Poppins:wght@400;600&amp;display=swap');"
    
    keyframes = """
    @keyframes d { from{transform:scale(1.0) translateY(0)} to{transform:scale(1.1) translateY(-10px)} }
    @keyframes slide { 0%{transform:translateY(15px);opacity:0} 100%{transform:translateY(0);opacity:1} }
    @keyframes pop { 0%{transform:scale(0); opacity:0} 100%{transform:scale(1); opacity:1} }
    @keyframes shine { 0% { transform: translateX(-200%); } 100% { transform: translateX(200%); } }
    @keyframes float { 0% { transform: translateY(0px); } 50% { transform: translateY(-4px); } 100% { transform: translateY(0px); } }
    """
    
    classes = ""
    # Always include basic positioning classes
    classes += ".card-glass { fill: rgba(20,20,20,0.6); stroke: rgba(255,255,255,0.1); stroke-width: 1.5; }"
    
    if str(bg_anim).lower() != 'false': 
        classes += ".bg-anim { animation: d 20s infinite alternate linear; transform-origin: center; } .shimmer { animation: shine 6s infinite linear; }"
    if str(fg_anim).lower() != 'false': 
        classes += ".slide-in { animation: slide 0.6s cubic-bezier(0, 0, 0.2, 1); } .pop-in { animation: pop 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); } .float { animation: float 6s ease-in-out infinite; }"

    return css + keyframes + classes

# ===========================
#      DATA LOGIC
# ===========================

def fetch_data(key, type_mode, args):
    try:
        force_name = args.get('name')

        # 1. SERVER MODE
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
            # A. Lanyard (Status) - Base Validity Check
            r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            lan_json = r_lan.json()
            if not lan_json.get('success'): return None
            
            lanyard = lan_json['data']
            u = lanyard['discord_user']
            status = lanyard['discord_status']

            # B. DCDN (Profile Assets)
            dcdn_user = {}
            badges_data = []
            connections_data = []
            banner_bg = None
            
            try:
                r_dcdn = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=4)
                if r_dcdn.status_code == 200:
                    d_json = r_dcdn.json()
                    dcdn_user = d_json.get('user', {})
                    
                    # 1. Badges
                    for b in d_json.get('badges', []):
                        badges_data.append(get_base64(b['icon']))
                    
                    # 2. Connections (The missing part from your image)
                    for c in d_json.get('connected_accounts', []):
                        if c['type'] in CONN_MAP:
                            c_url = f"{SIMPLE_ICONS_BASE}{CONN_MAP[c['type']]}.svg"
                            connections_data.append(get_base64(c_url, is_svg=True))
                    
                    # 3. Banner
                    if dcdn_user.get('banner'):
                        banner_bg = get_base64(dcdn_user['banner'])
            except: pass

            # --- PARSING ---
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#ED4245", "offline": "#80848e", "spotify": "#1DB954"}
            
            # Name & Avatar
            final_name = force_name if force_name else (dcdn_user.get('global_name') or u['global_name'] or u['username'])
            u_avatar = get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png")
            
            # If Banner missing, use a solid color fallback derived from status or user accent if available
            final_bg = banner_bg # Can be None, renderer will handle
            
            # Bio cleaning
            bio_clean = sanitize_xml(dcdn_user.get('bio', ''))
            
            # Activity Logic
            main_act = None
            # Spotify
            if lanyard.get('spotify'):
                s = lanyard['spotify']
                main_act = {
                    "header": "LISTENING TO SPOTIFY",
                    "title": s['song'],
                    "detail": s['artist'],
                    "image": s.get('album_art_url'),
                    "color": cols['spotify']
                }
            # Game / Rich Presence
            elif lanyard.get('activities'):
                for act in lanyard['activities']:
                    if act['type'] == 4: continue
                    img_url = None
                    if 'assets' in act and 'large_image' in act['assets']:
                        aid = act['application_id']
                        imid = act['assets']['large_image']
                        if imid.startswith("mp:"): img_url = f"https://media.discordapp.net/{imid[3:]}"
                        else: img_url = f"https://cdn.discordapp.com/app-assets/{aid}/{imid}.png"
                    
                    h_text = "PLAYING" if act['type'] == 0 else "WATCHING" if act['type'] == 3 else "ACTIVITY"
                    
                    main_act = {
                        "header": f"{h_text} {act['name'].upper()}",
                        "title": act.get('details', act['name']),
                        "detail": act.get('state', ''),
                        "image": img_url,
                        "color": cols.get(status, "#5865F2")
                    }
                    break
            
            # Fallback
            if not main_act:
                custom = args.get('idleMessage', 'Chilling')
                for act in lanyard.get('activities', []):
                    if act['type'] == 4: custom = act.get('state', custom); break
                
                main_act = {
                    "header": "CURRENT STATUS",
                    "title": custom,
                    "detail": "Online" if status!='offline' else "Offline",
                    "image": None,
                    "color": cols.get(status, "#555")
                }

            return {
                "type": "user",
                "name": sanitize_xml(final_name),
                "title": sanitize_xml(main_act['title']),
                "detail": sanitize_xml(main_act['detail']),
                "app_name": sanitize_xml(main_act['header']),
                "color": main_act['color'],
                "status_color": cols.get(status, "#555"),
                "avatar": u_avatar,
                "banner_image": final_bg,
                "act_image": get_base64(main_act['image']) if main_act['image'] else None,
                "bio": bio_clean,
                "badges": badges_data,
                "connections": connections_data,
                "sub_id": u['id']
            }

    except Exception as e:
        print(f"Data Error: {e}")
        return None

# ===========================
#      RENDER ENGINE
# ===========================

def render_profile(d, css, radius, bg_col):
    """Titan v37 Mega Profile"""

    # 1. Banner Logic (Critical Fix)
    if d.get('banner_image'):
        # Banner is fetched. Blur it slightly, darken bottom half.
        bg_svg = f"""
        <image href="{d['banner_image']}" width="100%" height="150%" y="-15%" preserveAspectRatio="xMidYMid slice" opacity="0.9" class="bg-anim"/>
        <rect width="100%" height="100%" fill="url(#vig)"/>
        """
    else:
        # Fallback Abstract Gradient
        bg_svg = f"""
        <rect width="100%" height="100%" fill="#{bg_col}" />
        <circle cx="500" cy="0" r="300" fill="{d['color']}" opacity="0.15" filter="url(#b)" />
        <circle cx="0" cy="300" r="300" fill="#5865F2" opacity="0.1" filter="url(#b)" />
        <rect width="100%" height="100%" fill="url(#noise)"/>
        """

    # 2. Badges Row
    badge_group = ""
    bx = 0
    # Add status dot into badge row visually or separate
    for i, b in enumerate(d.get('badges', [])[:6]):
        badge_group += f'<image href="{b}" x="{bx}" y="0" width="22" height="22" class="pop-in" style="animation-delay:{i*0.05}s"/>'
        bx += 28

    # 3. Connections (Invert color to white for visibility on dark BG)
    conn_group = ""
    cx = 0
    for c in d.get('connections', [])[:6]:
        conn_group += f'<image href="{c}" x="{cx}" y="0" width="18" height="18" filter="url(#invert)" class="pop-in"/>'
        cx += 28

    # 4. Activity Thumb
    if d['act_image']:
        act_viz = f'<image href="{d["act_image"]}" x="20" y="165" width="80" height="80" rx="12" /><rect x="20" y="165" width="80" height="80" rx="12" fill="none" stroke="white" stroke-opacity="0.1"/>'
        txt_pos = 115
    else:
        # Just text, no image
        act_viz = ""
        txt_pos = 20

    t_tit = d['title'][:32]
    
    return f"""<svg width="600" height="270" viewBox="0 0 600 270" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}
          .title {{ font-family: 'Pacifico', cursive; fill: white; text-shadow: 0 4px 8px rgba(0,0,0,0.6); }}
          .head {{ font-family: 'Outfit', sans-serif; font-weight: 800; }}
          .sub {{ font-family: 'Poppins', sans-serif; font-weight: 400; opacity: 0.9; }}
          .mono {{ font-family: 'JetBrains Mono', monospace; opacity: 0.5; }}
        </style>
        
        <clipPath id="cp"><rect width="600" height="270" rx="{radius}"/></clipPath>
        <clipPath id="av"><circle cx="65" cy="65" r="55"/></clipPath>
        
        <!-- Filters -->
        <filter id="b"><feGaussianBlur stdDeviation="40"/></filter>
        <!-- Invert black icons to white for visibility -->
        <filter id="invert"><feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0" /></filter>
        <linearGradient id="vig" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stop-color="black" stop-opacity="0.3"/>
            <stop offset="0.6" stop-color="#0b0b0e" stop-opacity="0.9"/>
            <stop offset="1" stop-color="#050505" stop-opacity="1"/>
        </linearGradient>
        <linearGradient id="glint" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="white" stop-opacity="0.05"/><stop offset="100%" stop-color="white" stop-opacity="0"/></linearGradient>
        <pattern id="noise" width="60" height="60" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="white" opacity="0.05"/></pattern>
      </defs>

      <!-- MAIN CONTAINER -->
      <g clip-path="url(#cp)">
        {bg_svg}
        
        <!-- Top Half Glint -->
        <path d="M0 0 L600 0 L600 130 Q 300 160 0 130 Z" fill="url(#glint)"/>
      </g>
      
      <!-- BORDER -->
      <rect x="2" y="2" width="596" height="266" rx="{radius}" fill="none" stroke="#222" stroke-width="2"/>

      <!-- AVATAR STACK (Left Top) -->
      <g transform="translate(30, 30)">
         <circle cx="65" cy="65" r="61" fill="#111"/>
         <circle cx="65" cy="65" r="59" fill="none" stroke="{d['color']}" stroke-width="3" stroke-dasharray="10 5" class="bg-anim"/>
         <g clip-path="url(#av)"><image href="{d['avatar']}" width="130" height="130" /></g>
         <circle cx="108" cy="108" r="14" fill="#000" />
         <circle cx="108" cy="108" r="10" fill="{d['status_color']}" class="status-pulse"/>
      </g>

      <!-- TEXT HEADER (Right Top) -->
      <g transform="translate(170, 45)">
          <g transform="translate(0, -10)">{badge_group}</g>
          
          <text x="0" y="45" class="title" font-size="42">{d['name']}</text>
          
          <foreignObject x="0" y="55" width="400" height="40">
             <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'Poppins';font-size:12px;color:#bbb;line-height:1.3;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;">
                 {d['bio']}
             </div>
          </foreignObject>
      </g>

      <!-- CONNECTIONS BAR (Below Bio) -->
      <g transform="translate(170, 115)">
          {conn_group}
      </g>

      <!-- BOTTOM GLASS: ACTIVITY -->
      <g transform="translate(20, 160)" class="slide-in">
          <!-- Glass Panel -->
          <rect width="560" height="100" rx="16" class="card-glass"/>
          
          {act_viz}
          
          <g transform="translate({txt_pos}, 26)">
              <text x="0" y="0" class="mono" font-size="9" fill="{d['color']}" font-weight="bold" letter-spacing="1">
                  {d['app_name']}
              </text>
              <text x="0" y="24" class="head" font-size="20" fill="white">
                  {t_tit}
              </text>
              <text x="0" y="42" class="sub" font-size="12" fill="#999">
                  {d['detail'][:45]}
              </text>
              <!-- Small UID footer -->
              <text x="440" y="65" text-anchor="end" class="mono" font-size="8">ID: {d['sub_id']}</text>
          </g>
      </g>

    </svg>"""

@app.route('/superbadge/<key>')
def handler(key):
    args = request.args
    mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    data = fetch_data(key, mode, args)
    
    if not data: return Response('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="290"><rect width="100%" height="100%" fill="black"/><text x="50" y="150" fill="red" font-family="sans-serif">USER FETCH ERROR</text></svg>', mimetype="image/svg+xml")

    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '111111').replace('#','')
    radius = args.get('borderRadius', '30').replace('px', '')
    
    css = get_css(bg_an, fg_an)
    
    if mode == 'discord': # Reuse User renderer but basic
        svg = render_mega_profile(data, css, radius, bg_col)
    else:
        svg = render_mega_profile(data, css, radius, bg_col)

    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
