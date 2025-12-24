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
HEADERS = {'User-Agent': 'HyperBadge/InfoDense-v30'}
# Fallback transparent pixel
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text)
    # Strip invisible control chars (0-31) to prevent XML crashes
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return html.escape(text, quote=True)

def get_base64(url):
    """Downloads image -> Base64"""
    if not url: return EMPTY
    try:
        if url.startswith("mp:"): url = f"https://media.discordapp.net/{url[3:]}"
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    # Load fonts: JetBrains (Tech), Pacifico (Script/Handwriting), Outfit (Bold Headers)
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Outfit:wght@500;900&amp;family=Pacifico&amp;display=swap');"
    
    keyframes = """
    @keyframes fade { 0%{opacity:0.4} 50%{opacity:0.8} 100%{opacity:0.4} }
    @keyframes d { from{transform:scale(1.1) rotate(0deg)} to{transform:scale(1.15) rotate(1deg)} }
    @keyframes pulse-ring { 0%{stroke-width:2px; stroke-opacity:0.8} 50%{stroke-width:4px; stroke-opacity:0.4} 100%{stroke-width:2px; stroke-opacity:0.8} }
    @keyframes slide { 0%{transform:translateX(-10px);opacity:0} 100%{transform:translateX(0);opacity:1} }
    """
    
    classes = ""
    if str(bg_anim).lower() != 'false':
        classes += ".bg-drift{animation:d 40s linear infinite alternate}"
    if str(fg_anim).lower() != 'false':
        classes += ".slide-in{animation:slide 0.8s ease-out} .status-pulse{animation:pulse-ring 3s infinite}"

    return css + keyframes + classes

# ===========================
#      LOGIC & FETCHING
# ===========================

def fetch_data(key, type_mode, args):
    try:
        force_name = args.get('name')

        # --- 1. DISCORD SERVER ---
        if type_mode == 'discord':
            r = requests.get(f"https://discord.com/api/v10/invites/{key}?with_counts=true", headers=HEADERS, timeout=4)
            d = r.json()
            g = d.get('guild')
            if not g: return None
            
            return {
                "type": "discord",
                "name": sanitize_xml(force_name or g['name']), 
                "title": f"{d.get('approximate_member_count', 0):,} Members",
                "detail": f"{d.get('approximate_presence_count',0):,} Online",
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY,
                "bg_image": None, "sub_id": g['id']
            }

        # --- 2. USER MODE (LANYARD + DCDN) ---
        else:
            # Step A: Get Real-time Presence (Lanyard)
            r = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            lan_json = r.json()
            if not lan_json.get('success'): 
                return {"type":"error", "avatar": EMPTY, "name":"User Not Found", "title": "Check ID", "detail":"", "color":"#555", "bg_image": None}
            
            d = lan_json['data']
            u = d['discord_user']
            status = d['discord_status']
            
            # Step B: Get Profile Metadata (DCDN - Extra Bio/Colors if available)
            # We try to fetch, but fail gracefully if DCDN is down/slow
            profile_bio = "Member of Chillax"
            try:
                p_r = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=2)
                if p_r.status_code == 200:
                    prof = p_r.json()
                    # Try to extract bio or useful info
                    if 'user' in prof and 'bio' in prof['user']:
                         profile_bio = prof['user']['bio'][:40]
            except: pass # Ignore DCDN errors, Lanyard is primary

            # --- ACTIVITY PARSING ---
            main_act = None
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#ED4245", "offline": "#555", "streaming": "#593695", "spotify": "#1DB954"}

            # A. Spotify Priority
            if d.get('spotify'):
                s = d['spotify']
                main_act = {
                    "app": "LISTENING TO SPOTIFY",
                    "title": s['song'],
                    "detail": s['artist'],
                    "image": s.get('album_art_url'),
                    "color": cols['spotify']
                }
            
            # B. Rich Presence (Game/Watch)
            if not main_act:
                for act in d.get('activities', []):
                    if act['type'] == 4: continue # Skip custom status
                    
                    img_url = None
                    if 'assets' in act and 'large_image' in act['assets']:
                        aid = act['application_id']
                        i_id = act['assets']['large_image']
                        if i_id.startswith("mp:"): img_url = f"https://media.discordapp.net/{i_id[3:]}"
                        else: img_url = f"https://cdn.discordapp.com/app-assets/{aid}/{i_id}.png"
                    
                    # Formatter
                    l1 = act['name']
                    l2 = act.get('details') or act.get('state') or "Active"
                    header = "PLAYING"
                    if act['type'] == 3: header = "WATCHING"
                    
                    main_act = {
                        "app": f"{header} {l1}".upper(),
                        "title": l1,
                        "detail": l2,
                        "image": img_url,
                        "color": cols.get(status, "#5865F2")
                    }
                    break

            # C. Fallback (Online/Offline)
            if not main_act:
                custom = profile_bio # Use bio or custom status
                for act in d.get('activities', []):
                    if act['type'] == 4: custom = act.get('state', profile_bio); break
                
                main_act = {
                    "app": "USER ID",
                    "title": u['username'].capitalize(),
                    "detail": custom,
                    "image": None,
                    "color": cols.get(status, "#555")
                }

            # Naming Logic
            display_name = force_name if force_name else (u['global_name'] or u['username'])
            
            return {
                "type": "user",
                "name": sanitize_xml(display_name),
                "title": sanitize_xml(main_act['title']),
                "detail": sanitize_xml(main_act['detail']),
                "app_name": sanitize_xml(main_act['app']),
                "color": main_act['color'],
                "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"),
                "bg_image": get_base64(main_act['image']) if main_act['image'] else None,
                "sub_id": u['id'] # USER ID LABEL
            }
    except Exception as e:
        print(f"Error: {e}")
        return None

# ===========================
#      RENDER ENGINE (LAYOUT FIX)
# ===========================

def render_info_dense(d, css, radius, bg_col):
    """
    Titan V30 Renderer:
    - Tight layout: Avatar -> Info
    - Custom Script Font for Name
    - High contrast text overlay
    """
    
    # 1. Background (Art or Gradient)
    if d.get('bg_image'):
        # Blurry Album/Game Art
        bg = f"""
        <image href="{d['bg_image']}" width="100%" height="150%" y="-25%" preserveAspectRatio="xMidYMid slice" opacity="0.5" filter="url(#blur)" class="bg-drift"/>
        <rect width="100%" height="100%" fill="url(#vig)"/>
        """
        # Card Thumbnail on Right (Optional visual)
        right_panel = f"""
        <g transform="translate(420, 25)" class="slide-in">
           <image href="{d['bg_image']}" width="60" height="60" rx="8" preserveAspectRatio="xMidYMid slice" />
           <rect width="60" height="60" rx="8" fill="none" stroke="rgba(255,255,255,0.2)" />
        </g>"""
    else:
        # Default Dark Gradient
        bg = f"""
        <rect width="100%" height="100%" fill="#{bg_col}" />
        <circle cx="0" cy="120" r="120" fill="{d['color']}" opacity="0.3" filter="url(#blur)"/>
        <circle cx="480" cy="0" r="140" fill="#5865F2" opacity="0.2" filter="url(#blur)"/>
        <rect width="100%" height="100%" fill="url(#grain)"/>
        """
        right_panel = ""

    # 2. Text Truncation (Safe Slicing)
    t_title = d['title']
    if len(t_title) > 28: t_title = t_title[:26] + ".."
    t_detail = d['detail']
    if len(t_detail) > 40: t_detail = t_detail[:38] + ".."

    return f"""<svg width="500" height="120" viewBox="0 0 500 120" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}
          .name-font {{ font-family: 'Pacifico', cursive; fill: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }}
          .label-font {{ font-family: 'JetBrains Mono', monospace; font-weight: 800; text-transform: uppercase; }}
          .title-font {{ font-family: 'Outfit', sans-serif; font-weight: 900; }}
          .desc-font {{ font-family: 'Outfit', sans-serif; font-weight: 500; opacity: 0.8; }}
        </style>
        
        <clipPath id="cp"><rect width="500" height="120" rx="{radius}"/></clipPath>
        <clipPath id="avClip"><circle cx="50" cy="50" r="40"/></clipPath>
        
        <filter id="blur"><feGaussianBlur stdDeviation="15"/></filter>
        <filter id="drop"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.5"/></filter>
        
        <linearGradient id="vig" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#0a0a0a" stop-opacity="0.5"/>
            <stop offset="100%" stop-color="#000" stop-opacity="0.9"/>
        </linearGradient>
        
        <pattern id="grain" width="50" height="50" patternUnits="userSpaceOnUse"><rect width="2" height="2" fill="white" opacity="0.05"/></pattern>
      </defs>

      <!-- BASE CARD -->
      <g clip-path="url(#cp)">
        {bg}
        <rect width="496" height="116" x="2" y="2" rx="{radius}" fill="none" stroke="white" stroke-opacity="0.1" stroke-width="2"/>
      </g>
      
      {right_panel}

      <!-- CONTENT ALIGNMENT (Fixes from your image) -->
      
      <!-- Avatar Section (Left) -->
      <g transform="translate(10, 10)">
         <!-- Dashed Ring -->
         <circle cx="50" cy="50" r="46" fill="none" stroke="{d['color']}" stroke-width="2" stroke-dasharray="8 6" opacity="0.6" class="status-pulse"/>
         
         <!-- Avatar -->
         <g clip-path="url(#avClip)">
            <image href="{d['avatar']}" width="100" height="100" x="0" y="0"/>
         </g>
         
         <!-- Status Dot (Overlapping bottom right) -->
         <circle cx="82" cy="82" r="14" fill="#18191C"/> <!-- Fake mask border -->
         <circle cx="82" cy="82" r="10" fill="{d['color']}"/>
      </g>

      <!-- Text Section (Center) -->
      <g transform="translate(120, 20)">
         
         <!-- Top: User ID Label + Name -->
         <text x="0" y="10" class="label-font" font-size="9" fill="#999" letter-spacing="1">USER ID: {d['sub_id']}</text>
         <text x="0" y="45" class="name-font" font-size="34">! {d['name']}</text>
         
         <!-- Activity Header (Red in your screenshot example) -->
         <text x="0" y="65" class="label-font" font-size="10" fill="{d['color']}" letter-spacing="2">
             {d.get('app_name', 'STATUS')}
         </text>
         
         <!-- Activity Title (Big White) -->
         <text x="0" y="85" class="title-font" font-size="20" fill="white" filter="url(#drop)">
             {t_title}
         </text>
         
         <!-- Detail (Artist/Bio) -->
         <text x="0" y="102" class="desc-font" font-size="12" fill="#CCC">
             {t_detail}
         </text>
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
         return Response('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100"><rect width="100%" height="100%" fill="#111"/><text x="20" y="60" fill="red" font-family="sans-serif">LOAD ERROR</text></svg>', mimetype="image/svg+xml")

    # Render settings
    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '111111').replace('#','') # Dark default
    radius = args.get('borderRadius', '25').replace('px', '')

    css = get_css(bg_an, fg_an)

    # Use the Info-Dense V30 Renderer
    svg = render_info_dense(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

@app.route('/')
def home(): return "TITAN V30 ONLINE"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
