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
HEADERS = {'User-Agent': 'HyperBadge/LayoutFix-v29'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text)
    # Remove control chars (ASCII 0-31) except tab/newline
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return html.escape(text, quote=True)

def get_base64(url):
    """Download image -> Base64"""
    if not url: return EMPTY
    try:
        # Lanyard proxies sometimes return mp: links
        if url.startswith("mp:"):
            url = f"https://media.discordapp.net/{url[3:]}"
            
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    # CSS: Modern Fonts
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Rajdhani:wght@600;800&amp;family=Outfit:wght@500;800&amp;display=swap');"
    
    # CSS: Keyframes
    keyframes = """
    @keyframes fade { 0%{opacity:0.4} 50%{opacity:0.8} 100%{opacity:0.4} }
    @keyframes d { from{transform:scale(1.1) rotate(0deg)} to{transform:scale(1.15) rotate(1deg)} }
    @keyframes p { 0%{stroke-width:2px; opacity:0.8} 50%{stroke-width:4px; opacity:1} 100%{stroke-width:2px; opacity:0.8} }
    @keyframes slide { 0%{transform:translateX(-15px);opacity:0} 100%{transform:translateX(0);opacity:1} }
    @keyframes hover { 0%{transform:translateY(0)} 50%{transform:translateY(-4px)} 100%{transform:translateY(0)} }
    """
    
    classes = ""
    # Animations Config
    if str(bg_anim).lower() != 'false':
        classes += ".bg-drift{animation:d 40s linear infinite alternate} .pulse-bg{animation:fade 4s infinite}"
    if str(fg_anim).lower() != 'false':
        classes += ".slide-in{animation:slide 0.8s ease-out} .status-pulse{animation:p 2s infinite} .float{animation:hover 6s ease-in-out infinite}"

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
            
            if not g: 
                return None
            
            return {
                "type": "discord",
                "name": sanitize_xml(force_name or "SERVER"), 
                "title": f"{d.get('approximate_member_count', 0):,} Members",
                "detail": f"{d.get('approximate_presence_count',0):,} Online",
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY,
                "bg_image": None,
                "app_name": "INVITE"
            }

        # --- 2. LANYARD USER ---
        else:
            r = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            response_json = r.json()
            
            if not response_json.get('success'):
                 return {
                    "type": "error", "name": "User Not Found", "title": "Check ID", 
                    "detail": "Join Lanyard Server", "color": "#555",
                    "avatar": EMPTY, "bg_image": None, "app_name": "ERROR"
                }
            
            d = response_json['data']
            u = d['discord_user']
            status = d['discord_status']
            
            # ACTIVITY PARSING
            main_activity = None
            
            # A. Spotify Priority
            if d.get('spotify'):
                s = d['spotify']
                main_activity = {
                    "app": "LISTENING TO SPOTIFY",
                    "title": s['song'],
                    "detail": s['artist'],
                    "image": s.get('album_art_url'),
                    "is_spotify": True
                }
            
            # B. Rich Presence (Images)
            if not main_activity:
                for act in d.get('activities', []):
                    if act['type'] == 4: continue # Skip status message
                    
                    img_url = None
                    if 'assets' in act and 'large_image' in act['assets']:
                        aid = act['application_id']
                        i_id = act['assets']['large_image']
                        if i_id.startswith("mp:"): img_url = f"https://media.discordapp.net/{i_id[3:]}"
                        else: img_url = f"https://cdn.discordapp.com/app-assets/{aid}/{i_id}.png"
                    
                    # Make nicer App names
                    app_label = act['name'].upper()
                    if act['type'] == 0: app_label = f"PLAYING {app_label}"
                    if act['type'] == 2: app_label = f"LISTENING TO {app_label}"
                    if act['type'] == 3: app_label = f"WATCHING {app_label}"

                    main_activity = {
                        "app": app_label,
                        "title": act.get('details', act['name']),
                        "detail": act.get('state', ''),
                        "image": img_url,
                        "is_spotify": False
                    }
                    break
            
            # C. Fallback / Custom Status
            if not main_activity:
                custom = "Vibing"
                for act in d.get('activities', []):
                    if act['type'] == 4: custom = act.get('state', 'Vibing'); break
                
                status_label = "ONLINE" if status=="online" else args.get('idleMessage', 'IDLE').upper()
                main_activity = {
                    "app": status_label,
                    "title": custom,
                    "detail": "",
                    "image": None,
                    "is_spotify": False
                }

            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#FF4444", "offline": "#555", "spotify": "#1DB954"}
            acc = cols['spotify'] if main_activity.get('is_spotify') else cols.get(status, "#5865F2")
            
            d_name = u['username']
            if args.get('showDisplayName', 'true').lower() == 'true' and u.get('global_name'):
                d_name = u['global_name']
            
            return {
                "type": "user",
                "name": sanitize_xml(force_name if force_name else d_name),
                "title": sanitize_xml(main_activity['title']),
                "detail": sanitize_xml(main_activity['detail']),
                "app_name": sanitize_xml(main_activity['app']),
                "color": acc,
                "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"),
                "bg_image": get_base64(main_activity['image']) if main_activity['image'] else None,
            }
    except Exception as e:
        print(f"Error: {e}")
        return None

# ===========================
#      RENDER ENGINE
# ===========================

def render_cinematic(d, css, radius, bg_col):
    """
    Fixed Layout Version (v29)
    - Adjusted Transforms: Text is higher, Image is wider.
    - Improved ClipPaths: Circles and Rects align mathematically.
    """
    
    # 1. BG Image or Gradient
    if d.get('bg_image'):
        bg = f"""
        <image href="{d['bg_image']}" width="120%" height="120%" x="-10%" y="-10%" preserveAspectRatio="xMidYMid slice" opacity="0.5" filter="url(#blur)" class="bg-drift"/>
        <rect width="100%" height="100%" fill="url(#vignette)"/>
        """
        # Shadow overlay to make text pop against bright art
        text_overlay = '<rect x="0" y="80" width="100%" height="120" fill="url(#bottomShade)"/>'
    else:
        bg = f"""
        <rect width="100%" height="100%" fill="#{bg_col}" />
        <circle cx="0" cy="200" r="160" fill="{d['color']}" opacity="0.3" filter="url(#blur)"/>
        <circle cx="500" cy="0" r="180" fill="#5865F2" opacity="0.3" filter="url(#blur)"/>
        <rect width="100%" height="100%" fill="url(#grain)"/>
        """
        text_overlay = ""

    # 2. Activity Card (Right Side)
    # Widened container, added aspect ratio stroke
    card_group = ""
    text_max_chars = 35 # Truncate long text so it doesn't hit image
    
    if d.get('bg_image'):
        text_max_chars = 22 # Shorten text if image present
        card_group = f"""
        <g transform="translate(365, 20)" class="slide-in float">
            <!-- Shadow -->
            <rect x="0" y="5" width="115" height="160" rx="10" fill="black" opacity="0.4" filter="url(#shadow)"/>
            
            <!-- Art Container -->
            <g clip-path="url(#artClip)">
               <image href="{d['bg_image']}" width="115" height="160" preserveAspectRatio="xMidYMid slice" />
            </g>
            
            <!-- Glass Stroke Border -->
            <rect width="115" height="160" rx="10" fill="none" stroke="{d['color']}" stroke-width="2" stroke-opacity="0.8" />
        </g>
        """

    # 3. Truncate Text safely
    title_display = d['title']
    if len(title_display) > text_max_chars: title_display = title_display[:text_max_chars] + ".."
    
    detail_display = d['detail']
    if len(detail_display) > 40: detail_display = detail_display[:38] + ".."


    return f"""<svg width="500" height="200" viewBox="0 0 500 200" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}
          .b {{ font-family: 'Outfit', sans-serif; font-weight: 800; }}
          .m {{ font-family: 'JetBrains Mono', monospace; font-weight: 500; }}
          .h {{ font-family: 'Rajdhani', sans-serif; font-weight: 700; letter-spacing: 1px; }}
        </style>
        
        <clipPath id="cp"><rect width="500" height="200" rx="{radius}"/></clipPath>
        <clipPath id="avClip"><circle cx="40" cy="40" r="40"/></clipPath>
        <clipPath id="artClip"><rect width="115" height="160" rx="10"/></clipPath>
        
        <filter id="blur"><feGaussianBlur stdDeviation="20"/></filter>
        <filter id="shadow"><feDropShadow dx="0" dy="4" stdDeviation="4" flood-opacity="0.5"/></filter>
        
        <!-- Ambient Vignette for readability -->
        <linearGradient id="vignette" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#000" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="#000" stop-opacity="0.8"/>
        </linearGradient>
        
        <!-- Text Contrast Backing -->
        <linearGradient id="bottomShade" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#000" stop-opacity="0"/>
            <stop offset="100%" stop-color="#000" stop-opacity="0.8"/>
        </linearGradient>
        
        <pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="white" opacity="0.05"/></pattern>
      </defs>

      <!-- CARD BACKGROUND -->
      <g clip-path="url(#cp)">
        {bg}
        {text_overlay}
        <!-- Inner Border Rim -->
        <rect width="496" height="196" x="2" y="2" rx="{radius}" fill="none" stroke="white" stroke-opacity="0.1" stroke-width="2"/>
      </g>
      
      <!-- CARD THUMBNAIL (RIGHT) -->
      {card_group}

      <!-- CONTENT (LEFT ALIGNED) -->
      
      <!-- Avatar Cluster: Top Left (Moved for better spacing) -->
      <g transform="translate(30, 30)">
         <!-- Pulse Ring -->
         <circle cx="40" cy="40" r="43" fill="none" stroke="{d['color']}" stroke-width="2" stroke-dasharray="15 5" opacity="0.6" class="status-pulse"/>
         
         <!-- Avatar Image -->
         <g clip-path="url(#avClip)"><image href="{d['avatar']}" width="80" height="80"/></g>
         
         <!-- Online/Status Indicator Dot -->
         <circle cx="70" cy="70" r="12" fill="{d['color']}" stroke="#111" stroke-width="3" filter="url(#shadow)"/>
         
         <!-- Display Name Next to Avatar (Header Style) -->
         <text x="100" y="25" class="b" font-size="14" fill="#AAA">USER ID</text>
         <text x="100" y="55" class="b" font-size="28" fill="white" style="text-shadow: 0 2px 5px rgba(0,0,0,0.5)">{d['name']}</text>
      </g>
      
      <!-- Activity Text Cluster: Bottom Left (Raised y coord to fit) -->
      <g transform="translate(30, 145)" class="slide-in">
         <!-- Small Label -->
         <text x="0" y="-30" class="h" font-size="11" fill="{d['color']}" letter-spacing="2">
            {d['app_name']}
         </text>
         
         <!-- Main Title (e.g. Song Name) -->
         <text x="0" y="0" class="b" font-size="24" fill="white" style="text-shadow: 0 2px 4px rgba(0,0,0,0.8)">
            {title_display}
         </text>
         
         <!-- Detail (e.g. Artist/Chapter) -->
         <text x="0" y="22" class="m" font-size="12" fill="#CCC">
            {detail_display}
         </text>
      </g>

    </svg>"""

# ===========================
#        CONTROLLER
# ===========================

@app.route('/superbadge/<key>')
def handler(key):
    args = request.args
    # Detect Mode (Simple numeric check for User ID)
    mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    
    data = fetch_data(key, mode, args)
    
    if not data or data.get('type') == 'error':
         return Response('<svg xmlns="http://www.w3.org/2000/svg" width="500" height="200"><rect width="100%" height="100%" fill="#111"/><text x="50%" y="50%" fill="red" text-anchor="middle" font-family="sans-serif">LOAD ERROR - CHECK ID</text></svg>', mimetype="image/svg+xml")

    # Render settings
    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '09090b').replace('#','')
    # Use standard 200px height now, radius default 20
    radius = args.get('borderRadius', '20').replace('px', '') 

    css = get_css(bg_an, fg_an)

    svg = render_cinematic(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

@app.route('/')
def home(): return "TITAN ACTIVITY DISPLAY V29 (FIXED LAYOUT)"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
