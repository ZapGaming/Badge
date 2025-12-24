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
# Generic user agent to avoid blocking
HEADERS = {'User-Agent': 'HyperBadge/Fixed-v28'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
CACHE = {}

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    """Clean text for XML"""
    if not text: return ""
    text = str(text)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return html.escape(text, quote=True)

def get_base64(url):
    """Download image -> Base64"""
    if not url: return EMPTY
    try:
        if url.startswith("mp:"):
            url = f"https://media.discordapp.net/{url[3:]}"
            
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    # Imports
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Rajdhani:wght@600;800&amp;family=Outfit:wght@500;900&amp;display=swap');"
    
    # Keyframes
    keyframes = """
    @keyframes fade { 0%{opacity:0.3} 50%{opacity:0.6} 100%{opacity:0.3} }
    @keyframes d { from{transform:scale(1.1) rotate(0deg)} to{transform:scale(1.2) rotate(2deg)} }
    @keyframes p { 0%{box-shadow: 0 0 0 0 rgba(88, 101, 242, 0.4);} 70%{box-shadow: 0 0 0 10px rgba(88, 101, 242, 0);} 100%{box-shadow: 0 0 0 0 rgba(88, 101, 242, 0);} }
    @keyframes slide { 0%{transform:translateX(-10px);opacity:0} 100%{transform:translateX(0);opacity:1} }
    """
    
    classes = ""
    # Only add animations if 'false' is NOT passed
    if str(bg_anim).lower() != 'false':
        classes += ".bg-drift{animation:d 40s linear infinite alternate} .pulse-bg{animation:fade 4s infinite}"
    if str(fg_anim).lower() != 'false':
        classes += ".slide-in{animation:slide 1s ease-out} .status-pulse{animation:p 2s infinite}"

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
            
            # Error handling for invalid invites
            if not g: 
                return {
                    "type": "error", "name": "INVALID INVITE", 
                    "title": "Error", "detail": "Server Not Found", "color": "#FF0000",
                    "avatar": EMPTY, "bg_image": None
                }
            
            return {
                "type": "discord",
                "name": sanitize_xml(force_name or "SERVER"), 
                "title": f"{d.get('approximate_member_count', 0):,} Members",
                "detail": f"{d.get('approximate_presence_count',0):,} Online",
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY,
                "bg_image": None
            }

        # --- 2. LANYARD USER ---
        else:
            r = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            response_json = r.json()
            
            # Safely check success before diving into data
            if not response_json.get('success'):
                 return {
                    "type": "error", "name": "USER NOT FOUND", 
                    "title": "Monitor Active", "detail": "Join discord.gg/lanyard", "color": "#555",
                    "avatar": EMPTY, "bg_image": None
                }
            
            d = response_json['data']
            u = d['discord_user']
            status = d['discord_status']
            
            # --- ACTIVITY PARSING ---
            main_activity = None
            
            # A. Spotify Priority
            if d.get('spotify'):
                s = d['spotify']
                main_activity = {
                    "app": "Spotify",
                    "title": s['song'],
                    "detail": s['artist'],
                    "image": s.get('album_art_url'),
                    "is_spotify": True
                }
            
            # B. Rich Presence Scan
            if not main_activity:
                for act in d.get('activities', []):
                    # Skip custom status (Type 4) initially to prioritize games
                    if act['type'] == 4: continue
                    
                    img_url = None
                    # Attempt to get large asset image
                    if 'assets' in act and 'large_image' in act['assets']:
                        aid = act['application_id']
                        i_id = act['assets']['large_image']
                        if i_id.startswith("mp:"): img_url = f"https://media.discordapp.net/{i_id[3:]}"
                        else: img_url = f"https://cdn.discordapp.com/app-assets/{aid}/{i_id}.png"
                    
                    main_activity = {
                        "app": act['name'],
                        "title": act.get('details', act['name']),
                        "detail": act.get('state', ''),
                        "image": img_url,
                        "is_spotify": False
                    }
                    break
            
            # C. Fallback / Custom Status
            if not main_activity:
                custom = "VIBING"
                for act in d.get('activities', []):
                    if act['type'] == 4: custom = act.get('state', 'Vibing'); break
                
                status_text = "ONLINE" if status=="online" else args.get('idleMessage', 'IDLE').upper()
                main_activity = {
                    "app": status_text,
                    "title": custom,
                    "detail": "",
                    "image": None,
                    "is_spotify": False
                }

            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#FF4444", "offline": "#555", "spotify": "#1DB954"}
            acc = cols['spotify'] if main_activity.get('is_spotify') else cols.get(status, "#5865F2")
            
            # Name Priority: Force > Global > Username
            display_name = u['username']
            if args.get('showDisplayName', 'true').lower() == 'true' and u.get('global_name'):
                display_name = u['global_name']
            if force_name:
                display_name = force_name

            return {
                "type": "user",
                "name": sanitize_xml(display_name),
                "title": sanitize_xml(main_activity['title']),
                "detail": sanitize_xml(main_activity['detail']),
                "app_name": sanitize_xml(main_activity['app']).upper(),
                "color": acc,
                "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"),
                "bg_image": get_base64(main_activity['image']) if main_activity['image'] else None,
            }
    except Exception as e:
        print(f"FETCH ERROR: {e}")
        return None

# ===========================
#      RENDER ENGINE
# ===========================

def render_cinematic(d, css, radius, bg_col):
    """
    Fixed Variable Names:
    d['avatar'] is now used correctly.
    d['bg_image'] checks handles missing backgrounds.
    """
    
    # 1. Background Logic
    if d.get('bg_image'):
        # Blurred Activity Background
        bg = f"""
        <image href="{d['bg_image']}" width="120%" height="120%" x="-10%" y="-10%" preserveAspectRatio="xMidYMid slice" opacity="0.6" filter="url(#blur)" class="bg-drift"/>
        <rect width="100%" height="100%" fill="url(#vig)"/>
        """
    else:
        # Default Dark Gradient
        bg = f"""
        <rect width="100%" height="100%" fill="#{bg_col}" />
        <circle cx="0" cy="200" r="150" fill="{d['color']}" opacity="0.3" filter="url(#blur)"/>
        <circle cx="500" cy="0" r="150" fill="#5865F2" opacity="0.3" filter="url(#blur)"/>
        <rect width="100%" height="100%" fill="url(#grain)"/>
        """

    # 2. Thumbnail Logic (If Rich Presence)
    thumb_grp = ""
    text_width = 460 # Default wide text
    
    if d.get('bg_image'):
        text_width = 340
        thumb_grp = f"""
        <g transform="translate(380, 20)" class="slide-in">
            <rect width="100" height="160" rx="10" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.2)"/>
            <image href="{d['bg_image']}" width="100" height="160" rx="10" preserveAspectRatio="xMidYMid slice" />
            <rect width="100" height="160" rx="10" fill="none" stroke="{d['color']}" stroke-width="2" opacity="0.5"/>
        </g>
        """

    return f"""<svg width="500" height="200" viewBox="0 0 500 200" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}
          .b {{ font-family: 'Outfit', sans-serif; font-weight: 900; }}
          .m {{ font-family: 'JetBrains Mono', monospace; font-weight: 500; }}
          .h {{ font-family: 'Rajdhani', sans-serif; font-weight: 700; letter-spacing: 2px; }}
        </style>
        
        <clipPath id="cp"><rect width="500" height="200" rx="{radius}"/></clipPath>
        <clipPath id="av"><circle cx="45" cy="45" r="45"/></clipPath>
        <filter id="blur"><feGaussianBlur stdDeviation="15"/></filter>
        <linearGradient id="vig" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stop-color="#09090b" stop-opacity="0.4"/>
            <stop offset="100%" stop-color="#09090b" stop-opacity="0.9"/>
        </linearGradient>
        <pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="white" opacity="0.03"/></pattern>
      </defs>

      <!-- BASE -->
      <g clip-path="url(#cp)">
        {bg}
        <rect width="496" height="196" x="2" y="2" rx="{radius}" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="2"/>
      </g>
      
      {thumb_grp}

      <!-- CONTENT -->
      <g transform="translate(30, 40)">
         <!-- Avatar -->
         <g>
            <circle cx="45" cy="45" r="48" fill="none" stroke="{d['color']}" stroke-width="3" stroke-dasharray="20 10" class="pulse-bg"/>
            <g clip-path="url(#av)"><image href="{d['avatar']}" width="90" height="90"/></g>
            <circle cx="80" cy="80" r="12" fill="{d['color']}" stroke="#111" stroke-width="3"/>
         </g>
         
         <!-- Text Data -->
         <g transform="translate(0, 115)">
            <text x="0" y="0" class="h" font-size="12" fill="{d['color']}">{d.get('app_name', 'STATUS')}</text>
            <text x="0" y="28" class="b slide-in" font-size="26" fill="white" style="text-shadow: 0 4px 10px rgba(0,0,0,0.5)">{d['title'][:22]}</text>
            <text x="0" y="46" class="m" font-size="13" fill="#CCC">{d['detail'][:35]}</text>
         </g>
      </g>

      <!-- Watermark -->
      <g transform="translate(470, 30)" text-anchor="end">
          <text x="0" y="0" class="b" font-size="16" fill="white" opacity="0.5">{d['name'].upper()}</text>
      </g>
    </svg>"""

# ===========================
#        CONTROLLER
# ===========================

@app.route('/superbadge/<key>')
def handler(key):
    args = request.args
    # Auto-Detect User vs Server
    mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    
    data = fetch_data(key, mode, args)
    if not data:
        # Fallback for catastrophic API failure
        return Response('<svg xmlns="http://www.w3.org/2000/svg" width="500" height="200"><rect width="100%" height="100%" fill="#111"/><text x="250" y="100" text-anchor="middle" fill="red" font-family="sans-serif">SYSTEM FAILURE</text></svg>', mimetype="image/svg+xml")

    # Styling settings
    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '09090b').replace('#','')
    radius = args.get('borderRadius', '25').replace('px', '')

    css = get_css(bg_an, fg_an)

    # Render
    svg = render_cinematic(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

@app.route('/')
def home(): return "TITAN ACTIVITY ENGINE ONLINE (V28 FIX)"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
