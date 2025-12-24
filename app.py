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
HEADERS = {'User-Agent': 'HyperBadge/Titan-v42-Fix'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
CACHE = {}

# SOCIAL ICONS MAP
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
    # Clean standard XML entities
    return html.escape(text, quote=True)

def get_base64(url, is_svg=False):
    """Robust image fetcher"""
    if not url: return EMPTY
    try:
        # Resolve Discord Media Proxy URLs
        if url.startswith("mp:"): url = f"https://media.discordapp.net/{url[3:]}"
        
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            mime = "image/svg+xml" if (is_svg or url.endswith(".svg")) else "image/png"
            return f"data:{mime};base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Outfit:wght@400;500;800;900&amp;family=Pacifico&amp;family=Poppins:wght@400;500;600&amp;display=swap');"
    
    keyframes = """
    @keyframes d { from{transform:scale(1.02) rotate(0deg)} to{transform:scale(1.05) rotate(0.5deg)} }
    @keyframes slide { 0%{transform:translateX(-10px);opacity:0} 100%{transform:translateX(0);opacity:1} }
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
                "detail": f"{d.get('approximate_presence_count',0):,} Online",
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
                r_prof = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=4)
                if r_prof.status_code == 200:
                    d_json = r_prof.json()
                    dcdn_user = d_json.get('user', {})
                    
                    # 1. Badges
                    for b in d_json.get('badges', []):
                        badges_data.append(get_base64(f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png"))
                    
                    # 2. Connections
                    seen = set()
                    for c in d_json.get('connected_accounts', []):
                        ctype = c['type']
                        if ctype in CONN_MAP and ctype not in seen:
                            c_url = f"{SIMPLE_ICONS_BASE}{CONN_MAP[c['type']]}.svg"
                            connections_data.append(get_base64(c_url, is_svg=True))
                            seen.add(ctype)
                    
                    # 3. Banner
                    if dcdn_user.get('banner'):
                        # DCDN Banner logic
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
            bio_clean = sanitize_xml(dcdn_user.get('bio', 'No Bio Set.'))
            
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
                
                header_txt = "OFFLINE" if status == 'offline' else "CURRENTLY"
                
                main_act = {
                    "header": header_stat,
                    "title": custom,
                    "detail": "No active tasks",
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
#      RENDER ENGINE (V42)
# ===========================

def render_mega_profile(d, css, radius, bg_col):
    """
    Titan V42 Fixed Renderer
    """
    
    # 1. Background Logic
    if d.get('banner_image'):
        bg_svg = f"""
        <image href="{d['banner_image']}" width="100%" height="150%" y="-15%" preserveAspectRatio="xMidYMid slice" opacity="0.6" filter="url(#heavyBlur)" class="bg-drift"/>
        <rect width="100%" height="100%" fill="url(#vig)"/>
        """
    else:
        # Fallback Abstract Gradient
        bg_svg = f"""
        <rect width="100%" height="100%" fill="#{bg_col}" />
        <circle cx="500" cy="0" r="300" fill="{d['color']}" opacity="0.2" filter="url(#b)" />
        <rect width="100%" height="100%" fill="url(#vig)"/>
        """

    # 2. Activity Image Logic
    txt_pos = 20 # Default text X (No image)
    
    if d.get('act_image'):
        act_viz = f"""
        <image href="{d['act_image']}" x="25" y="185" width="80" height="80" rx="12" />
        <rect x="25" y="185" width="80" height="80" rx="12" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>
        """
        txt_pos = 120 # Move text right if image exists
    else:
        # Text Icon Placeholder
        act_viz = f"""
        <rect x="25" y="185" width="80" height="80" rx="12" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.1)"/>
        <text x="65" y="235" text-anchor="middle" font-size="28" fill="{d['color']}">⚡</text>
        """
        txt_pos = 120

    # 3. Badges Row
    badge_group = ""
    bx = 0
    if d.get('badges'):
        for i, b in enumerate(d['badges'][:8]):
            badge_group += f'<image href="{b}" x="{bx}" y="0" width="22" height="22" class="badge-pop" style="animation-delay:{i*0.05}s"/>'
            bx += 26
        
    # 4. Connections Row
    conn_group = ""
    cx = 0
    if d.get('connections'):
        for i, c in enumerate(d['connections'][:5]):
            conn_group += f'<image href="{c}" x="{cx}" y="0" width="20" height="20" filter="url(#invert)" opacity="0.7"/>'
            cx += 28

    return f"""<svg width="880" height="320" viewBox="0 0 880 320" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}
          .title {{ font-family: 'Pacifico', cursive; fill: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.6); }}
          .head {{ font-family: 'Outfit', sans-serif; font-weight: 800; }}
          .sub {{ font-family: 'Poppins', sans-serif; font-weight: 500; opacity: 0.9; }}
          .mono {{ font-family: 'JetBrains Mono', monospace; opacity: 0.6; }}
        </style>
        
        <clipPath id="cp"><rect width="880" height="320" rx="{radius}"/></clipPath>
        <clipPath id="avc"><circle cx="75" cy="75" r="75"/></clipPath>
        
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="50"/></filter>
        <filter id="b"><feGaussianBlur stdDeviation="30"/></filter>
        <filter id="invert"><feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"/></filter>
        
        <linearGradient id="vig" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stop-color="black" stop-opacity="0.3"/>
            <stop offset="0.6" stop-color="#0b0b0e" stop-opacity="0.8"/>
            <stop offset="1" stop-color="#000" stop-opacity="1"/>
        </linearGradient>
        
        <linearGradient id="shine" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="white" stop-opacity="0.03"/><stop offset="100%" stop-color="white" stop-opacity="0"/></linearGradient>
        <pattern id="noise" width="100" height="100" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="white" opacity="0.04"/></pattern>
      </defs>

      <g clip-path="url(#cp)">
        {bg_svg}
        
        <!-- Effects Layer -->
        <rect width="880" height="320" fill="url(#noise)"/>
        <rect x="-400" y="0" width="150" height="320" fill="white" opacity="0.04" transform="skewX(-20)" class="shiny"/>
        <rect width="876" height="316" x="2" y="2" rx="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="2"/>
      </g>
      
      <!-- HEADER -->
      <g transform="translate(40, 40)">
         <!-- Avatar Ring -->
         <circle cx="75" cy="75" r="79" fill="#18181c"/>
         <circle cx="75" cy="75" r="76" fill="none" stroke="{d['color']}" stroke-width="4" stroke-dasharray="16 10" class="pulsing"/>
         
         <!-- Avatar Img -->
         <g clip-path="url(#avc)"><image href="{d['avatar']}" width="150" height="150" /></g>
         
         <!-- Status Dot -->
         <circle cx="125" cy="125" r="18" fill="#121212"/>
         <circle cx="125" cy="125" r="14" fill="{d['status_color']}" class="status-breathe"/>

         <!-- User Text -->
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

      <!-- DOCK AREA (Activity) -->
      <g transform="translate(20, 205)" class="slide-in">
          <rect width="840" height="95" rx="20" fill="rgba(20,20,25,0.7)" stroke="{d['color']}" stroke-opacity="0.3" stroke-width="2"/>
          <rect width="840" height="95" rx="20" fill="url(#shine)"/>
          
          {act_viz}
          
          <g transform="translate({txt_pos}, -165)"> 
            <!-- Translate Y trick because we are inside a lower group -->
             <text x="0" y="195" class="mono" font-size="11" fill="{d['color']}" letter-spacing="2" font-weight="bold">{d['app_name']}</text>
             <text x="0" y="222" class="head" font-size="24" fill="white" filter="url(#ds)">{d['title'][:32]}</text>
             <text x="0" y="244" class="sub" font-size="15" fill="#BBB">{d['detail'][:60]}</text>
          </g>
          
          <g transform="translate(680, 38)">{conn_group}</g>
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
         return Response('<svg xmlns="http://www.w3.org/2000/svg" width="880" height="320"><rect width="100%" height="100%" fill="#111"/><text x="40" y="50" fill="red">DATA FAILURE</text></svg>', mimetype="image/svg+xml")

    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '111111').replace('#','')
    radius = args.get('borderRadius', '40').replace('px', '') 

    css = get_css(bg_an, fg_an)
    
    svg = render_mega_profile(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

@app.route('/')
def home(): return "TITAN V42 STABLE"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
