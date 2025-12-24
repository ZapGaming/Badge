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
CACHE = {}
HEADERS = {'User-Agent': 'HyperBadge/Titan-v37'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# Platform & Social Icons (Base64 cache maps)
ICON_CACHE = {} 
SIMPLE_ICONS_BASE = "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/"

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text)
    # Remove control chars (0-31) except newline/tab
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return html.escape(text, quote=True)

def get_base64(url, is_svg=False):
    if not url: return EMPTY
    try:
        if url.startswith("mp:"): url = f"https://media.discordapp.net/{url[3:]}"
        
        # Internal Cache to speed up repeat requests
        if url in ICON_CACHE: return ICON_CACHE[url]
        
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            # Handle SVGs from SimpleIcons
            mime = "image/svg+xml" if (is_svg or url.endswith(".svg")) else "image/png"
            b64 = f"data:{mime};base64,{base64.b64encode(r.content).decode('utf-8')}"
            
            # Simple in-memory LRU cache concept (limit size in real prod)
            if len(ICON_CACHE) > 50: ICON_CACHE.clear()
            ICON_CACHE[url] = b64
            return b64
    except: pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Outfit:wght@400;500;800&amp;family=Pacifico&amp;family=Poppins:wght@400;600&amp;display=swap');"
    
    keyframes = """
    @keyframes d { from{transform:scale(1.02) rotate(0deg)} to{transform:scale(1.05) rotate(0.5deg)} }
    @keyframes slide { 0%{transform:translateX(-10px);opacity:0} 100%{transform:translateX(0);opacity:1} }
    @keyframes pop { 0%{transform:scale(0); opacity:0} 100%{transform:scale(1); opacity:1} }
    @keyframes pulse { 0%{opacity:0.6} 50%{opacity:1} 100%{opacity:0.6} }
    """
    
    classes = ""
    if str(bg_anim).lower() != 'false': classes += ".bg-drift{animation:d 40s linear infinite alternate} .pulsing{animation:pulse 3s infinite}"
    if str(fg_anim).lower() != 'false': classes += ".slide-in{animation:slide 0.8s ease-out} .badge-pop{animation:pop 0.5s backwards}"

    return css + keyframes + classes

# ===========================
#      DATA LOGIC
# ===========================

def fetch_data(key, type_mode, args):
    try:
        force_name = args.get('name')

        # 1. DISCORD SERVER (Minimal mode)
        if type_mode == 'discord':
            r = requests.get(f"https://discord.com/api/v10/invites/{key}?with_counts=true", headers=HEADERS, timeout=4)
            d = r.json(); g = d.get('guild')
            if not g: return None
            
            # Default to compact "MEMBERS" text for servers
            display_title = force_name if force_name else "TOTAL MEMBERS"
            
            return {
                "type": "discord",
                "name": sanitize_xml(display_title), 
                "l1": f"{d.get('approximate_member_count', 0):,}", 
                "l2": "",
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY
            }

        # 2. USER MODE (Hybrid DCDN + Lanyard)
        else:
            # A. Fetch Profile (DCDN) - Banner, Bio, Badges, Connections
            dcdn_user = {}
            badges_data = []
            connections_data = []
            
            try:
                # Based on your HTML example: https://dcdn.dstn.to/profile/{USER_ID}
                r_prof = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=3)
                if r_prof.status_code == 200:
                    prof_json = r_prof.json()
                    if 'user' in prof_json:
                        dcdn_user = prof_json['user']
                        # Badges List
                        for b in prof_json.get('badges', []):
                            # URL scheme from your HTML: cdn.discordapp.com/badge-icons/ICON.png
                            badges_data.append(get_base64(f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png"))
                        # Connections
                        for c in prof_json.get('connected_accounts', []):
                            # HTML used simple-icons
                            c_url = f"{SIMPLE_ICONS_BASE}{c['type']}.svg"
                            connections_data.append(get_base64(c_url, is_svg=True))
            except: pass

            # B. Fetch Presence (Lanyard) - Live Status
            r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            lan_json = r_lan.json()
            if not lan_json.get('success'): 
                return None # Fail if no presence
            
            d = lan_json['data']
            u = d['discord_user']
            status = d['discord_status']
            
            # --- PLATFORM ICONS ---
            # Green dot if active on platform
            platforms = []
            for p in ['desktop', 'mobile', 'web']:
                if d.get(f'active_on_discord_{p}'):
                    platforms.append(p)
            
            # --- COLORS & ACTIVITY ---
            # Colors from your HTML
            cols = {"online": "#23a55a", "idle": "#f0b232", "dnd": "#f23f42", "offline": "#80848e", "spotify": "#1DB954", "crunchyroll": "#f47521"}
            main_act = None

            # 1. Crunchyroll (Specific Check like HTML)
            # Find specific crunchyroll activity ID or name
            crunchy_act = next((a for a in d.get('activities', []) if a.get('application_id') == '802969115042414612' or a['name'] == 'Crunchyroll'), None)
            
            if crunchy_act:
                img_url = None
                if 'assets' in crunchy_act and 'large_image' in crunchy_act['assets']:
                    # Poster handling
                    img = crunchy_act['assets']['large_image']
                    if img.startswith("mp:"): img_url = f"https://media.discordapp.net/{img[3:]}"
                    else: img_url = f"https://cdn.discordapp.com/app-assets/{crunchy_act['application_id']}/{img}.png"

                main_act = {
                    "header": "WATCHING CRUNCHYROLL",
                    "title": crunchy_act.get('details') or crunchy_act['name'],
                    "detail": crunchy_act.get('state', ''),
                    "image": get_base64(img_url),
                    "color": cols['crunchyroll'],
                    "is_poster": True
                }

            # 2. Spotify (If no Crunchy)
            if not main_act and d.get('spotify'):
                s = d['spotify']
                main_act = {
                    "header": "LISTENING TO SPOTIFY",
                    "title": s['song'],
                    "detail": s['artist'],
                    "image": get_base64(s.get('album_art_url')),
                    "color": cols['spotify'],
                    "is_poster": False
                }

            # 3. Game/Other (Fallback)
            if not main_act:
                for act in d.get('activities', []):
                    if act['type'] == 4: continue # Custom status logic below
                    
                    app_id = act.get('application_id')
                    img_url = None
                    if 'assets' in act and 'large_image' in act['assets']:
                        img = act['assets']['large_image']
                        if img.startswith("mp:"): img_url = f"https://media.discordapp.net/{img[3:]}"
                        else: img_url = f"https://cdn.discordapp.com/app-assets/{app_id}/{img}.png"
                    
                    head = "WATCHING" if act['type'] == 3 else "PLAYING"
                    main_act = {
                        "header": f"{head} {act['name'].upper()}",
                        "title": act.get('details', act['name']),
                        "detail": act.get('state', ''),
                        "image": get_base64(img_url),
                        "color": cols.get(status, "#5865F2"),
                        "is_poster": False
                    }
                    break

            # 4. Idle/Custom Status
            if not main_act:
                idle_txt = args.get('idleMessage', 'Chilling')
                # Find custom status
                for act in d.get('activities', []):
                    if act['type'] == 4 and act.get('state'):
                        idle_txt = act['state']
                
                header_stat = "OFFLINE" if status == 'offline' else "CURRENTLY"
                
                main_act = {
                    "header": header_stat, "title": idle_txt, "detail": "",
                    "image": None, "color": cols.get(status, "#555"), "is_poster": False
                }

            # Names & Assets
            f_name = force_name if force_name else (dcdn_user.get('global_name') or u['global_name'] or u['username'])
            u_bio = dcdn_user.get('bio', '')
            
            # Avatar & Banner Logic
            raw_av = f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"
            final_avatar = get_base64(raw_av)
            
            # Banner Priority: DCDN -> Fallback Lanyard/None
            banner_final = None
            if dcdn_user.get('banner'):
                # DCDN returns banner hash
                b_hash = dcdn_user['banner']
                ext = "gif" if b_hash.startswith("a_") else "png"
                banner_final = get_base64(f"https://cdn.discordapp.com/banners/{u['id']}/{b_hash}.{ext}?size=600")

            return {
                "type": "user",
                "name": sanitize_xml(f_name),
                "title": sanitize_xml(main_act['title']),
                "detail": sanitize_xml(main_act['detail']),
                "app_name": sanitize_xml(main_act['header']),
                "color": main_act['color'],
                "status_color": cols.get(status, "#80848e"),
                "avatar": final_avatar,
                "banner": banner_final, # Could be None, Renderer handles it
                "act_image": main_act['image'], # Already base64
                "bio": sanitize_xml(u_bio),
                "badges": badges_data, # List of b64 strings
                "connections": connections_data, # List of b64 strings
                "platforms": platforms, # List of strings ['mobile', 'web']
                "sub_id": u['id'],
                "is_poster": main_act['is_poster']
            }
    except Exception as e:
        print(f"Data Fetch: {e}")
        return None

# ===========================
#      RENDER ENGINE (V37)
# ===========================

def render_titan_profile(d, css, radius, bg_col):
    
    # 1. Background (Banner -> Blur -> Fallback)
    if d.get('banner'):
        bg_fill = f'<image href="{d["banner"]}" width="100%" height="180" preserveAspectRatio="xMidYMid slice" opacity="0.8" filter="url(#heavyBlur)" class="bg-drift"/>'
    else:
        # Fallback Gradient based on status color
        bg_fill = f'<rect width="100%" height="150" fill="url(#gradFall)" /><linearGradient id="gradFall" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{d["status_color"]}" stop-opacity="0.3"/><stop offset="1" stop-color="black"/></linearGradient>'

    # 2. Activity Image Handling
    if d.get('act_image') and d['act_image'] != EMPTY:
        if d['is_poster']: # Crunchyroll vertical
            act_viz = f'<image href="{d["act_image"]}" x="25" y="160" width="70" height="100" rx="8" preserveAspectRatio="xMidYMid slice" />'
            txt_start_x = 110
        else: # Standard Square
            act_viz = f'<image href="{d["act_image"]}" x="25" y="170" width="80" height="80" rx="12" />'
            txt_start_x = 120
    else:
        # Fallback if no activity image -> Shows a generic 'Bolt' icon
        act_viz = f'<rect x="25" y="170" width="80" height="80" rx="12" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.1)"/><text x="65" y="220" text-anchor="middle" font-size="30" fill="{d["color"]}">⚡</text>'
        txt_start_x = 120

    # 3. Badges Row
    badge_group = ""
    bx = 0
    for b64 in d.get('badges', [])[:7]: # Limit 7
        badge_group += f'<image href="{b64}" x="{bx}" y="0" width="22" height="22" class="badge-pop"/>'
        bx += 26
    
    # 4. Connections Row
    conn_group = ""
    cx = 0
    for c64 in d.get('connections', [])[:4]:
        # Filter white icon to grey? SVG can utilize opacity
        conn_group += f'<image href="{c64}" x="{cx}" y="0" width="18" height="18" opacity="0.7"/>'
        cx += 24

    # 5. Platforms Indicators
    # Draw simple paths for Desktop/Mobile/Web based on logic
    # (Icons would be defined as <defs> or drawn paths. For compactness using emoji text approximation or simple shapes)
    plat_svg = ""
    # Only if present
    px = 530
    if 'mobile' in d['platforms']: plat_svg += f'<text x="{px}" y="25" fill="#DDD" font-size="16">📱</text>'; px -= 25
    if 'desktop' in d['platforms']: plat_svg += f'<text x="{px}" y="25" fill="#DDD" font-size="16">🖥️</text>'; px -= 25
    if 'web' in d['platforms']: plat_svg += f'<text x="{px}" y="25" fill="#DDD" font-size="16">🌐</text>'

    return f"""<svg width="600" height="290" viewBox="0 0 600 290" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}
          .name-f {{ font-family: 'Outfit', sans-serif; font-weight: 800; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }}
          .mono {{ font-family: 'JetBrains Mono', monospace; }}
          .head {{ font-family: 'Rajdhani', sans-serif; font-weight: 700; letter-spacing: 1px; }}
          .popp {{ font-family: 'Poppins', sans-serif; font-weight: 400; }}
        </style>
        <clipPath id="cp"><rect width="600" height="290" rx="{radius}"/></clipPath>
        <clipPath id="ac"><circle cx="65" cy="65" r="65"/></clipPath>
        
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="30"/></filter>
        <linearGradient id="v" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#111" stop-opacity="0.3"/><stop offset="1" stop-color="#000" stop-opacity="0.95"/></linearGradient>
      </defs>

      <!-- CARD BASE -->
      <g clip-path="url(#cp)">
         <!-- Solid BG Fallback -->
         <rect width="600" height="290" fill="#{bg_col}"/>
         
         <!-- Dynamic Top Banner -->
         {bg_fill}
         
         <!-- Vignette Overlay -->
         <rect width="100%" height="100%" fill="url(#v)"/>
         
         <!-- Outline -->
         <rect width="596" height="286" x="2" y="2" rx="{radius}" fill="none" stroke="white" stroke-opacity="0.1" stroke-width="2"/>
      </g>

      <!-- 1. HEADER SECTION -->
      <g transform="translate(30, 30)">
         <!-- Profile Pic -->
         <g>
            <circle cx="65" cy="65" r="70" fill="#18181c" />
            <circle cx="65" cy="65" r="66" fill="none" stroke="{d['status_color']}" stroke-width="3" stroke-dasharray="12 6" opacity="0.6"/>
            <g clip-path="url(#ac)">
               <image href="{d['avatar']}" width="130" height="130" />
            </g>
            <!-- Status Dot Cutout -->
            <circle cx="110" cy="110" r="16" fill="#18181c"/> 
            <circle cx="110" cy="110" r="11" fill="{d['status_color']}"/>
         </g>
         
         <!-- Badges Row -->
         <g transform="translate(150, 0)">
            {badge_group}
         </g>

         <!-- Name & Bio -->
         <g transform="translate(150, 40)">
            <text x="0" y="10" class="name-f" font-size="36" fill="white">{d['name']}</text>
            <text x="2" y="30" class="mono" font-size="10" fill="#AAA">ID: {d['sub_id']}</text>
            
            <foreignObject x="2" y="45" width="380" height="40">
               <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'Poppins';font-size:12px;color:#ccc;line-height:1.2;overflow:hidden;text-overflow:ellipsis;">
                 {d['bio']}
               </div>
            </foreignObject>
         </g>
         
         <!-- Platforms (Top Right) -->
         <g>{plat_svg}</g>
      </g>
      
      <!-- 2. BOTTOM ACTIVITY PANEL -->
      <g transform="translate(0, 0)"> <!-- Anchor point reset -->
          {act_vis}
          
          <g transform="translate({txt_start_x}, 180)">
             <!-- Activity Header (Red/Green etc) -->
             <text x="0" y="0" class="head" font-size="11" fill="{d['color']}">
                 {d['app_name']}
             </text>
             
             <!-- Song/Game Name -->
             <text x="0" y="26" class="name-f" font-size="22" fill="white">
                 {d['title'][:25]}
             </text>
             
             <!-- State -->
             <text x="0" y="46" class="popp" font-size="12" fill="#BBB">
                 {d['detail'][:35]}
             </text>
             
             <!-- Connections Row (Bottom Right) -->
             <g transform="translate(350, 60)" opacity="0.8">
                 {conn_group}
             </g>
          </g>
      </g>
      
    </svg>"""

# ===========================
#        ROUTE
# ===========================
@app.route('/superbadge/<key>')
def handler(key):
    # Syntax fix: user mode logic
    mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    args = request.args
    
    # 1. FETCH DATA
    data = fetch_data(key, mode, args)

    if not data:
         # Syntax Error fix: String properly closed
         return Response("""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="100"><rect width="100%" height="100%" fill="#111"/><text x="20" y="60" fill="red" font-family="sans-serif">USER FETCH FAILED</text></svg>""", mimetype="image/svg+xml")

    # 2. RENDER SETTINGS
    bg_col = args.get('bg', '111111').replace('#','')
    radius = args.get('borderRadius', '30').replace('px', '')
    
    # Animations Config
    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')

    css = get_css(bg_an, fg_an)
    
    if mode == 'discord':
        # Simple server render logic if needed (reuse user layout but simplified)
        svg = render_mega_profile(data, css, radius, bg_col)
    else:
        svg = render_mega_profile(data, css, radius, bg_col)

    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
