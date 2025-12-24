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
HEADERS = {'User-Agent': 'HyperBadge/Titan-Fixed-v47'}
# 1x1 Transparent Pixel
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

CACHE = {} 
CONN_MAP = {
    "github": "github", "steam": "steam", "twitch": "twitch", "spotify": "spotify",
    "twitter": "x", "reddit": "reddit", "youtube": "youtube",
    "xbox": "xbox", "playstation": "playstation", "tiktok": "tiktok", "instagram": "instagram"
}
SIMPLE_ICONS_BASE = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/"

# Platform SVG Paths
PLATFORM_PATHS = {
    "desktop": "M4 4h16c1.1 0 2 .9 2 2v9c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zm0 2v9h16V6H4zm8 14c-.55 0-1-.45-1-1v-1h2v1c0 .55-.45 1-1 1z",
    "mobile": "M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z",
    "web": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"
}

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return html.escape(text, quote=True)

def get_base64(url, is_svg=False):
    """Downloads image -> Base64"""
    if not url: return EMPTY
    try:
        # Proxy correction
        if url.startswith("mp:"): url = f"https://media.discordapp.net/{url[3:]}"
        
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            mime = "image/svg+xml" if (is_svg or url.endswith(".svg")) else "image/png"
            return f"data:{mime};base64,{base64.b64encode(r.content).decode('utf-8')}"
    except: pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Outfit:wght@400;500;800;900&amp;family=Pacifico&amp;family=Poppins:wght@400;500;600&amp;display=swap');"
    
    keyframes = """
    @keyframes fade { 0%{opacity:0.3} 50%{opacity:0.6} 100%{opacity:0.3} }
    @keyframes d { from{transform:scale(1.02) rotate(0deg)} to{transform:scale(1.05) rotate(0.5deg)} }
    @keyframes pop { 0%{transform:scale(0); opacity:0} 100%{transform:scale(1); opacity:1} }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    @keyframes float { 0% { transform: translateY(0px); } 50% { transform: translateY(-5px); } 100% { transform: translateY(0px); } }
    """
    
    classes = ""
    if str(bg_anim).lower() != 'false': 
        classes += ".bg-drift{animation:d 40s linear infinite alternate} .pulse-bg{animation:fade 4s infinite} .vibrant{filter: saturate(1.4);}"
    if str(fg_anim).lower() != 'false': 
        classes += ".pop-in{animation:pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) backwards} .float{animation:float 6s ease-in-out infinite} .spin-slow{animation:spin 20s linear infinite}"
    return css + keyframes + classes

# ===========================
#      DATA LOGIC
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
                "detail": f"{d.get('approximate_presence_count',0):,} Online",
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY
            }

        # 2. USER MODE
        else:
            # A. Fetch Profile (DCDN)
            dcdn_user, badges_data, connections_data, banner_bg = {}, [], [], None
            
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
                        for c in prof_json.get('connected_accounts', []):
                            ctype = c['type']
                            if ctype in CONN_MAP:
                                c_url = f"{SIMPLE_ICONS_BASE}{CONN_MAP[ctype]}.svg"
                                connections_data.append(get_base64(c_url, is_svg=True))
                        # Banner
                        if dcdn_user.get('banner'):
                             banner_bg = get_base64(dcdn_user['banner'])
            except: pass

            # B. Fetch Presence (Lanyard)
            r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            lan_json = r_lan.json()
            if not lan_json.get('success'): return None
            
            d = lan_json['data']
            u = d['discord_user']
            status = d['discord_status']

            # Platforms
            platforms = []
            if d.get('active_on_discord_desktop'): platforms.append("desktop")
            if d.get('active_on_discord_mobile'): platforms.append("mobile")
            if d.get('active_on_discord_web'): platforms.append("web")

            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#ED4245", "offline": "#80848e", "spotify": "#1DB954"}
            
            main_act = None

            # 1. Spotify
            if d.get('spotify'):
                s = d['spotify']
                main_act = {
                    "header": "LISTENING TO SPOTIFY",
                    "title": s['song'],
                    "detail": s['artist'],
                    "image": s.get('album_art_url'),
                    "color": cols['spotify'],
                    "is_music": True
                }
            # 2. Rich Presence
            elif d.get('activities'):
                for act in d['activities']:
                    if act['type'] == 4: continue
                    img_url = None
                    if 'assets' in act and 'large_image' in act['assets']:
                        aid = act['application_id']
                        imid = act['assets']['large_image']
                        if imid.startswith("mp:"): img_url = f"https://media.discordapp.net/{imid[3:]}"
                        else: img_url = f"https://cdn.discordapp.com/app-assets/{aid}/{imid}.png"
                    
                    header = "PLAYING" if act['type'] == 0 else "WATCHING"
                    main_act = {
                        "header": f"{header} {act['name'].upper()}",
                        "title": act.get('details') or act['name'],
                        "detail": act.get('state') or "",
                        "image": img_url,
                        "color": cols.get(status, "#5865F2"),
                        "is_music": False
                    }
                    break
            
            # 3. Fallback
            if not main_act:
                msg = args.get('idleMessage', 'Chilling')
                for act in d.get('activities', []):
                    if act['type'] == 4: msg = act.get('state', msg); break
                
                header_stat = "OFFLINE" if status == 'offline' else "CURRENTLY"
                
                main_act = {
                    "header": header_stat, "title": msg, "detail": "Online" if status!='offline' else "Offline",
                    "image": None, "color": cols.get(status, "#555")
                }

            final_name = force_name if force_name else (dcdn_user.get('global_name') or u['global_name'] or u['username'])
            u_avatar = get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png")
            # If Banner missing, use a solid color fallback via Logic in Renderer
            
            bio_clean = sanitize_xml(dcdn_user.get('bio', 'No Bio Set.'))
            
            return {
                "type": "user",
                "name": sanitize_xml(final_name),
                "title": sanitize_xml(main_act['title']),
                "detail": sanitize_xml(main_act['detail']),
                "app_name": sanitize_xml(main_act['header']),
                "color": main_act['color'],
                "status_color": cols.get(status, "#555"),
                "avatar": u_avatar,
                "banner_image": banner_bg, # Can be None
                "act_image": get_base64(main_act['image']) if main_act['image'] else None,
                "bio": bio_clean,
                "badges": badges_data,
                "connections": connections_data,
                "platforms": platforms,
                "sub_id": u['id']
            }
    except Exception as e:
        print(f"Fetch Error: {e}")
        return None

# ===========================
#      RENDER ENGINE (V46 Fixed)
# ===========================

def render_mega_profile(d, css, radius, bg_col):
    """
    Layout: Split Design. Identity (Left), Dock (Right-Floating)
    """

    # 1. Background Logic
    if d.get('banner_image'):
         # If Banner exists
        bg_svg = f"""
        <rect width="100%" height="100%" fill="#{bg_col}" />
        <image href="{d['banner_image']}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.3" filter="url(#heavyBlur)" class="bg-drift"/>
        """
    else:
        # Fallback Abstract Gradient
        bg_svg = f"""
        <rect width="100%" height="100%" fill="#{bg_col}" />
        <circle cx="200" cy="100" r="400" fill="{d['color']}" opacity="0.2" filter="url(#heavyBlur)" class="bg-drift vibrant"/>
        <circle cx="800" cy="300" r="300" fill="{d['status_color']}" opacity="0.15" filter="url(#heavyBlur)" class="bg-drift"/>
        """
    
    # 2. Activity Image (Left side of dock)
    if d['act_image']:
        act_viz = f"""
        <image href="{d['act_image']}" x="530" y="55" width="160" height="160" rx="14" class="vibrant" />
        <rect x="530" y="55" width="160" height="160" rx="14" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="2"/>
        """
        # Dock Text Position (To the right of the big image)
        txt_x = 220 
    else:
        act_viz = f"""
        <rect x="570" y="55" width="120" height="120" rx="14" fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.1)"/>
        <text x="630" y="125" text-anchor="middle" font-family="Outfit" font-size="50" fill="{d['color']}">⚡</text>
        """
        txt_x = 20 # Align to right dock normally

    # 3. Badges Row
    badge_group = ""
    bx = 0
    if d.get('badges'):
        for i, b in enumerate(d['badges'][:8]):
            badge_group += f'<image href="{b}" x="{bx}" y="0" width="32" height="32" class="pop-in" style="animation-delay:{i*0.05}s"/>'
            bx += 38
        
    # 4. Connections Row
    conn_group = ""
    cx = 0
    if d.get('connections'):
        for i, c in enumerate(d['connections'][:5]):
             conn_group += f'<image href="{c}" x="{cx}" y="0" width="22" height="22" filter="url(#invert)" opacity="0.7"/>'
             cx += 34

    # 5. Platforms Icons
    plat_svg = ""
    px = 830
    for p in d.get('platforms', []):
        if p in PLATFORM_PATHS:
             plat_svg += f'<path transform="translate({px}, 40) scale(1.1)" d="{PLATFORM_PATHS[p]}" fill="{d["status_color"]}" opacity="0.9" />'
             px -= 30

    return f"""<svg width="900" height="350" viewBox="0 0 900 350" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}
          .title {{ font-family: 'Pacifico', cursive; fill: white; text-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
          .h1 {{ font-family: 'Outfit', sans-serif; font-weight: 800; letter-spacing: -1px; }}
          .h2 {{ font-family: 'Outfit', sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; }}
          .body {{ font-family: 'Poppins', sans-serif; font-weight: 400; }}
          .mono {{ font-family: 'JetBrains Mono', monospace; opacity: 0.5; }}
        </style>
        
        <clipPath id="cp"><rect width="900" height="350" rx="{radius}"/></clipPath>
        <clipPath id="avc"><circle cx="85" cy="85" r="85"/></clipPath>
        
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="60"/></filter>
        <filter id="invert"><feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"/></filter>
        <filter id="ds"><feDropShadow dx="0" dy="4" stdDeviation="4" flood-opacity="0.5"/></filter>
        
        <linearGradient id="vig" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stop-color="rgba(0,0,0,0.2)"/>
            <stop offset="1" stop-color="#000" stop-opacity="0.9"/>
        </linearGradient>
        
        <pattern id="noise" width="100" height="100" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="white" opacity="0.04"/></pattern>
        <pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.5" fill="white" opacity="0.03"/></pattern>
      </defs>

      <!-- 1. BASE LAYER -->
      <g clip-path="url(#cp)">
        {bg_svg}
        
        <!-- Texture & Overlays -->
        <rect width="100%" height="100%" fill="url(#noise)"/>
        <rect width="100%" height="100%" fill="url(#vig)"/>
        <rect width="896" height="346" x="2" y="2" rx="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="2"/>
      </g>
      
      <!-- 2. LEFT: IDENTITY -->
      <g transform="translate(60, 60)">
         <!-- Avatar Group -->
         <g class="float">
             <!-- Status Ring -->
             <circle cx="85" cy="85" r="92" fill="none" stroke="{d['color']}" stroke-width="2" opacity="0.5"/>
             <circle cx="85" cy="85" r="88" fill="#151515"/>
             <!-- Masked Image -->
             <g clip-path="url(#avc)"><image href="{d['avatar']}" width="170" height="170" /></g>
             
             <!-- Status Dot (Huge) -->
             <circle cx="150" cy="140" r="22" fill="#121212"/>
             <circle cx="150" cy="140" r="16" fill="{d['status_color']}" class="status-pulse"/>
         </g>

         <!-- Info Stack (Below Avatar in your design concept) -->
         <g transform="translate(200, 10)">
             <!-- Top Row Badges -->
             {badge_group}
             
             <!-- Name -->
             <text x="0" y="55" class="title" font-size="58">{d['name']}</text>
             <!-- ID -->
             <text x="5" y="80" class="mono" font-size="12">ID :: {d['sub_id']}</text>
             
             <!-- Bio (ForeignObject HTML for wrapping) -->
             <foreignObject x="5" y="90" width="300" height="60">
                 <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'Poppins',sans-serif; font-size:16px; color:#ddd; line-height:1.4; overflow:hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; opacity:0.9;">
                   {d['bio']}
                 </div>
             </foreignObject>
         </g>
      </g>
      
      <!-- Platforms Icon Row -->
      <g transform="translate(750, 40)">{plat_svg}</g>

      <!-- 3. RIGHT: FLOATING DOCK -->
      <!-- We shift the dock to the right side of the canvas -->
      <g transform="translate(520, 20)" class="slide-in">
          <!-- The Glass Card Background -->
          <rect x="0" y="0" width="360" height="310" rx="24" fill="rgba(25,25,30,0.5)" stroke="{d['color']}" stroke-opacity="0.3" stroke-width="1.5"/>
          <rect x="0" y="0" width="360" height="310" rx="24" fill="url(#dots)" opacity="0.5"/>
          
          <!-- Image Layer -->
          {act_viz}

          <!-- Activity Text (Below the image in this vertical layout) -->
          <g transform="translate(20, 240)">
             <text x="0" y="0" class="h2" font-size="10" fill="{d['color']}">{d['app_name']}</text>
             <text x="0" y="28" class="h1" font-size="22" fill="white">{d['title'][:25]}</text>
             <text x="0" y="48" class="body" font-size="13" fill="#CCC">{d['detail'][:35]}</text>
          </g>
          
          <!-- Connections (Inside Dock Bottom) -->
          <g transform="translate(20, 25)">
              {conn_group}
          </g>
      </g>

    </svg>"""

# ===========================
#        CONTROLLER
# ===========================

@app.route('/superbadge/<key>')
def handler(key):
    args = request.args
    mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    data = fetch_data(key, mode, args)
    
    if not data:
         return Response('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="350"><rect width="100%" height="100%" fill="#111"/><text x="450" y="175" fill="red" text-anchor="middle">ERROR</text></svg>', mimetype="image/svg+xml")

    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '111111').replace('#','')
    radius = args.get('borderRadius', '40').replace('px', '') 

    css = get_css(bg_an, fg_an)
    
    # We call the FIXED name: render_mega_profile
    svg = render_mega_profile(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

@app.route('/')
def home(): return "TITAN V42 FIXED ONLINE"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
