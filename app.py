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
HEADERS = {'User-Agent': 'HyperBadge/Titan-v43-NoBanner'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
CACHE = {}

# ICONS
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
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return html.escape(text, quote=True)

def get_base64(url, is_svg=False):
    if not url: return EMPTY
    try:
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
    @keyframes d { from{transform:scale(1.02) rotate(0deg)} to{transform:scale(1.05) rotate(0.5deg)} }
    @keyframes slide { 0%{transform:translateX(-15px);opacity:0} 100%{transform:translateX(0);opacity:1} }
    @keyframes pop { 0%{transform:scale(0); opacity:0} 100%{transform:scale(1); opacity:1} }
    @keyframes pulse { 0%{opacity:0.6} 50%{opacity:1} 100%{opacity:0.6} }
    @keyframes glint { 0% {transform:translateX(-200%)} 100% {transform:translateX(200%)} }
    @keyframes breathe { 0%{r:12px} 50%{r:16px} 100%{r:12px} }
    """
    
    classes = ""
    # Animations Config
    if str(bg_anim).lower() != 'false': 
        classes += ".bg-drift{animation:d 40s linear infinite alternate} .pulsing{animation:pulse 3s infinite} .shiny{animation:glint 6s infinite cubic-bezier(0.4, 0, 0.2, 1)}"
    if str(fg_anim).lower() != 'false': 
        classes += ".slide-in{animation:slide 0.8s ease-out} .badge-pop{animation:pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) backwards} .status-breathe{animation:breathe 3s infinite}"

    return css + keyframes + classes

# ===========================
#      DATA FETCHING
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
            dcdn_user, badges_data, connections_data = {}, [], []
            
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
                        seen = set()
                        for c in prof_json.get('connected_accounts', []):
                            ctype = c['type']
                            if ctype in CONN_MAP and ctype not in seen:
                                c_url = f"{SIMPLE_ICONS_BASE}{CONN_MAP[ctype]}.svg"
                                connections_data.append(get_base64(c_url, is_svg=True))
                                seen.add(ctype)
            except: pass

            # B. Fetch Presence (Lanyard)
            r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            lan_json = r_lan.json()
            if not lan_json.get('success'): return None
            
            d = lan_json['data']
            u = d['discord_user']
            status = d['discord_status']

            # --- COLOR LOGIC ---
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#ed4245", "offline": "#80848e", "spotify": "#1DB954"}
            status_col = cols.get(status, "#555")

            # --- ACTIVITY PARSING ---
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
                        "color": cols.get(status, "#5865F2")
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
                    "image": None, "color": status_col
                }

            final_name = force_name if force_name else (dcdn_user.get('global_name') or u['global_name'] or u['username'])
            u_avatar = get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png")
            
            return {
                "type": "user",
                "name": sanitize_xml(final_name),
                "title": sanitize_xml(main_act['title']),
                "detail": sanitize_xml(main_act['detail']),
                "app_name": sanitize_xml(main_act['header']),
                "color": main_act['color'],
                "status_color": status_col,
                "avatar": u_avatar,
                # Force banner image to None to ensure clean background rendering
                "banner_image": None,
                "act_image": get_base64(main_act['image']) if main_act['image'] else None,
                "bio": sanitize_xml(dcdn_user.get('bio', '')),
                "badges": badges_data,
                "connections": connections_data,
                "sub_id": u['id']
            }

    except Exception as e:
        print(f"Data Error: {e}")
        return None

# ===========================
#      RENDER ENGINE (V43)
# ===========================

def render_mega_profile(d, css, radius, bg_col):
    """
    Titan V43: No Banner. Clean Abstract Gradient.
    """
    
    # 1. Clean Abstract Background (Generated Code)
    # Uses User Status color for the main blob glow
    bg_svg = f"""
    <rect width="100%" height="100%" fill="#{bg_col}" />
    <!-- Main Glow -->
    <circle cx="150" cy="50" r="300" fill="{d['status_color']}" opacity="0.15" filter="url(#heavyBlur)" class="bg-drift"/>
    <!-- Secondary Glow (Purple accent) -->
    <circle cx="700" cy="250" r="300" fill="#5865F2" opacity="0.12" filter="url(#heavyBlur)" class="bg-drift"/>
    
    <rect width="100%" height="100%" fill="url(#vig)"/>
    <rect width="100%" height="100%" fill="url(#noise)"/>
    """

    # 2. Activity Visual
    if d.get('act_image') and d['act_image'] != EMPTY:
        act_viz = f"""
        <image href="{d['act_image']}" x="30" y="210" width="80" height="80" rx="14" preserveAspectRatio="xMidYMid slice" />
        <rect x="30" y="210" width="80" height="80" rx="14" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>
        """
        txt_pos = 135
    else:
        # Text Icon
        act_viz = f"""
        <rect x="30" y="210" width="80" height="80" rx="14" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.1)"/>
        <text x="70" y="258" text-anchor="middle" font-family="Outfit" font-size="32" fill="{d['color']}">⚡</text>
        """
        txt_pos = 135

    # 3. Badges Row
    badge_group = ""
    bx = 0
    if d.get('badges'):
        for i, b in enumerate(d['badges'][:10]):
            badge_group += f'<image href="{b}" x="{bx}" y="0" width="28" height="28" class="badge-pop" style="animation-delay:{i*0.05}s"/>'
            bx += 34
        
    # 4. Connections Row
    conn_group = ""
    cx = 0
    if d.get('connections'):
        for i, c in enumerate(d['connections'][:8]):
             conn_group += f'<image href="{c}" x="{cx}" y="0" width="24" height="24" filter="url(#invert)" opacity="0.6"/>'
             cx += 34
             
    # Truncate Title if needed
    t_tit = d['title']
    if len(t_tit) > 42: t_tit = t_tit[:40] + ".."

    return f"""<svg width="880" height="320" viewBox="0 0 880 320" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}
          .title {{ font-family: 'Pacifico', cursive; fill: white; text-shadow: 2px 4px 10px rgba(0,0,0,0.6); }}
          .head {{ font-family: 'Outfit', sans-serif; font-weight: 800; }}
          .sub {{ font-family: 'Poppins', sans-serif; font-weight: 500; opacity: 0.9; }}
          .mono {{ font-family: 'JetBrains Mono', monospace; opacity: 0.6; }}
        </style>
        
        <clipPath id="cp"><rect width="880" height="320" rx="{radius}"/></clipPath>
        <clipPath id="avc"><circle cx="75" cy="75" r="75"/></clipPath>
        
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="60"/></filter>
        <filter id="b"><feGaussianBlur stdDeviation="30"/></filter>
        <filter id="invert"><feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"/></filter>
        <filter id="ds"><feDropShadow dx="0" dy="4" stdDeviation="4" flood-opacity="0.5"/></filter>
        
        <linearGradient id="vig" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stop-color="rgba(0,0,0,0.3)"/>
            <stop offset="1" stop-color="#000" stop-opacity="0.8"/>
        </linearGradient>
        <linearGradient id="shine" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="white" stop-opacity="0.05"/>
            <stop offset="100%" stop-color="white" stop-opacity="0"/>
        </linearGradient>
        <pattern id="noise" width="100" height="100" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="white" opacity="0.04"/></pattern>
      </defs>

      <g clip-path="url(#cp)">
        {bg_svg}
        
        <!-- Subtle Glint -->
        <rect x="-400" y="0" width="150" height="320" fill="white" opacity="0.03" transform="skewX(-20)" class="shiny"/>
        
        <!-- Inner Border -->
        <rect width="876" height="316" x="2" y="2" rx="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="2"/>
      </g>
      
      <!-- TOP LEFT -->
      <g transform="translate(40, 40)">
         <!-- Avatar Ring -->
         <circle cx="75" cy="75" r="79" fill="#18181c"/>
         <circle cx="75" cy="75" r="76" fill="none" stroke="{d['color']}" stroke-width="4" stroke-dasharray="16 10" class="pulsing"/>
         
         <g clip-path="url(#avc)"><image href="{d['avatar']}" width="150" height="150" /></g>
         <!-- Online Dot -->
         <circle cx="125" cy="125" r="18" fill="#121212"/>
         <circle cx="125" cy="125" r="13" fill="{d['status_color']}" class="status-breathe"/>

         <!-- User Data -->
         <g transform="translate(180, 20)">
            <g transform="translate(5, -15)">{badge_group}</g>

            <text x="0" y="55" class="title" font-size="60">{d['name']}</text>
            <text x="10" y="80" class="mono" font-size="12">ID :: {d['sub_id']}</text>
            
            <foreignObject x="5" y="90" width="600" height="60">
               <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'Poppins',sans-serif; font-size:16px; color:#ddd; line-height:1.4; overflow:hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; opacity:0.9;">
                   {d['bio']}
               </div>
            </foreignObject>
         </g>
      </g>

      <!-- BOTTOM: Activity Dock -->
      <g transform="translate(20, 195)" class="slide-in">
          <rect width="840" height="110" rx="20" fill="rgba(20,20,25,0.7)" stroke="{d['color']}" stroke-opacity="0.3" stroke-width="2"/>
          <rect width="840" height="110" rx="20" fill="url(#shine)"/>
          
          {act_viz}
          
          <g transform="translate({txt_pos}, 28)">
              <text x="0" y="0" class="mono" font-size="11" fill="{d['color']}" letter-spacing="2" font-weight="bold">{d['app_name']}</text>
              <text x="0" y="32" class="head" font-size="26" fill="white" filter="url(#ds)">{t_tit}</text>
              <text x="0" y="56" class="sub" font-size="15" fill="#BBB">{d['detail'][:60]}</text>
          </g>
          
          <!-- Connections Right Side -->
          <g transform="translate(680, 45)">
              <g transform="translate(-{len(d.get('connections',[]))*15}, 0)">
                 {conn_group}
              </g>
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
         return Response('<svg xmlns="http://www.w3.org/2000/svg" width="880" height="320"><rect width="100%" height="100%" fill="#111"/><text x="440" y="160" text-anchor="middle" fill="red" font-family="sans-serif" font-size="24">LOAD ERROR</text></svg>', mimetype="image/svg+xml")

    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '111111').replace('#','')
    radius = args.get('borderRadius', '40').replace('px', '') 

    css = get_css(bg_an, fg_an)
    svg = render_mega_profile(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

@app.route('/')
def home(): return "TITAN V43 (NO BANNER)"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
