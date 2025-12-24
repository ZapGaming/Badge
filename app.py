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
HEADERS = {'User-Agent': 'HyperBadge/Activity-Split-v26'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
CACHE = {}

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return html.escape(text, quote=True)

def get_base64(url):
    """Downloads image -> Base64"""
    if not url: return EMPTY
    try:
        # Filter mp: URLs which Lanyard sometimes sends (external proxies)
        if url.startswith("mp:"):
            url = f"https://media.discordapp.net/{url[3:]}"
            
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(r.content).decode('utf-8')}"
    except:
        pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    # Modern Fonts
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Rajdhani:wght@600;800&amp;family=Outfit:wght@500;900&amp;family=Pacifico&amp;display=swap');"
    
    keyframes = """
    @keyframes f { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
    @keyframes f2 { 0%,100%{transform:translateY(0)} 50%{transform:translateY(4px)} }
    @keyframes p { 50%{opacity:0.6} }
    @keyframes spin { 100% {transform:rotate(360deg)} }
    @keyframes grain { 0%, 100% {transform:translate(0,0)} 10% {transform:translate(-5%,-10%)} 30% {transform:translate(3%,-15%)} 50% {transform:translate(12%,9%)} 70% {transform:translate(9%,4%)} 90% {transform:translate(-1%,7%)} }
    @keyframes aurora { 0%{filter:hue-rotate(0deg)} 100%{filter:hue-rotate(40deg)} }
    """
    
    classes = ""
    if str(fg_anim).lower() == 'true':
        classes += ".float{animation:f 6s ease-in-out infinite} .float-rev{animation:f2 7s ease-in-out infinite} .pulse{animation:p 2s infinite}"
    if str(bg_anim).lower() == 'true':
        classes += ".aurora-bg{animation:aurora 20s infinite alternate}"

    return css + keyframes + classes

# ===========================
#       DATA HARVESTERS
# ===========================

def fetch_data(key, type_mode, args):
    try:
        force_name = args.get('name')

        # --- DISCORD SERVER ---
        if type_mode == 'discord':
            r = requests.get(f"https://discord.com/api/v10/invites/{key}?with_counts=true", headers=HEADERS, timeout=4)
            d = r.json()
            g = d.get('guild')
            if not g: return None
            
            return {
                "type": "discord",
                "name": sanitize_xml(force_name or "MEMBERS"), 
                "l1": f"{d['approximate_member_count']:,}", 
                "l2": f"{d.get('approximate_presence_count',0):,} ONLINE",
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY,
                "act_img": None
            }

        # --- LANYARD USER (Rich Activity) ---
        else:
            r = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            d = r.json().get('data', {})
            if not d: return None
            
            u = d['discord_user']
            status = d['discord_status']
            
            dname = u['global_name'] if (args.get('showDisplayName','true').lower()=='true' and u.get('global_name')) else u['username']
            final_name = sanitize_xml(force_name if force_name else dname)
            
            l1, l2, col = "IDLE", "NO ACTIVITY", "#555"
            act_img = None
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#FF4444", "offline": "#555", "spotify": "#1DB954"}

            # 1. SPOTIFY
            if d.get('spotify'):
                s = d['spotify']
                l1 = f"Listening"; l2 = f"{s['song']} - {s['artist']}"
                col = cols['spotify']
                act_img = get_base64(s.get('album_art_url'))
            
            # 2. RICH PRESENCE (Crunchyroll, Games)
            else:
                col = cols.get(status, "#555")
                custom_idle = args.get('idleMessage', 'Chillaxing')
                found = False
                
                # Prioritize activities with assets
                for act in d.get('activities', []):
                    # Filter custom status
                    if act['type'] == 4: continue 

                    l1 = act['name']
                    # Try to get detailed state (e.g. "Episode 24")
                    l2 = act.get('details') or act.get('state') or "Active"
                    
                    # Fetch Image Asset
                    if 'assets' in act and 'large_image' in act['assets']:
                        aid = act['application_id']
                        img_id = act['assets']['large_image']
                        if img_id.startswith("mp:"):
                            act_img = get_base64(f"https://media.discordapp.net/{img_id[3:]}")
                        else:
                            act_img = get_base64(f"https://cdn.discordapp.com/app-assets/{aid}/{img_id}.png")
                    
                    found = True
                    break
                
                if not found:
                    # Check Custom Status
                    for act in d.get('activities', []):
                        if act['type'] == 4:
                             l1 = "STATUS"; l2 = act.get('state', custom_idle)
                             found = True
                             break
                    if not found:
                         l1 = "STATUS"; l2 = "ONLINE" if status=="online" else "OFFLINE"

            return {
                "type": "user",
                "name": final_name,
                "l1": sanitize_xml(l1)[:20], 
                "l2": sanitize_xml(l2)[:35],
                "color": col, 
                "avatar": get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"),
                "act_img": act_img, # Cover Art
                "id": u['id']
            }
    except Exception as e:
        print(e)
        return None

# ===========================
#      RENDERERS
# ===========================

def render_split_glass(d, css, radius, bg_col):
    """
    Split Glass Aesthetic:
    - Island 1: Identity (Left)
    - Island 2: Stats/Status (Right Top)
    - Island 3: Activity Large (Right Bottom)
    """
    
    # Activity Section Logic
    if d['act_img'] and d['act_img'] != EMPTY:
        # SHOW BIG ACTIVITY
        act_panel = f"""
        <g transform="translate(130, 85)" class="float-rev">
            <!-- Glass container -->
            <rect width="350" height="110" rx="16" fill="rgba(0,0,0,0.4)" stroke="{d['color']}" stroke-width="2" stroke-opacity="0.5"/>
            <!-- Blur BG for Art -->
            <clipPath id="cp2"><rect width="350" height="110" rx="16"/></clipPath>
            <g clip-path="url(#cp2)">
                <image href="{d['act_img']}" width="100%" height="300%" y="-50" opacity="0.3" preserveAspectRatio="xMidYMid slice" filter="url(#bl)"/>
            </g>
            <!-- Art Square -->
            <g transform="translate(15, 15)">
                <image href="{d['act_img']}" width="80" height="80" rx="10" />
                <rect width="80" height="80" rx="10" fill="none" stroke="rgba(255,255,255,0.2)"/>
            </g>
            <!-- Text Info -->
            <text x="110" y="45" font-family="Rajdhani" font-weight="800" font-size="20" fill="white">{d['l1'].upper()}</text>
            <text x="110" y="70" font-family="Outfit" font-size="14" fill="#CCC">{d['l2']}</text>
        </g>
        """
    else:
        # NO ACTIVITY (Compact filler)
        act_panel = f"""
        <g transform="translate(130, 85)" class="float-rev">
            <rect width="350" height="60" rx="16" fill="rgba(255,255,255,0.05)" stroke="{d['color']}" stroke-width="1" stroke-dasharray="10 5"/>
            <text x="175" y="35" text-anchor="middle" font-family="Rajdhani" font-size="16" fill="#888" letter-spacing="2">NO SIGNAL // {d['l2']}</text>
        </g>
        """

    # Background Blob Logic
    bg = f"""<rect width="100%" height="100%" fill="#{bg_col}" />
    <circle r="150" fill="{d['color']}" class="drift" opacity="0.25" filter="url(#bl)" />
    <circle cx="400" cy="180" r="180" fill="#5865F2" class="drift" opacity="0.2" filter="url(#bl)" />"""

    return f"""<svg width="500" height="220" viewBox="0 0 500 220" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css}</style>
      <clipPath id="cp"><rect width="500" height="220" rx="{radius}"/></clipPath>
      <clipPath id="av"><rect width="90" height="90" rx="20"/></clipPath>
      <filter id="bl"><feGaussianBlur stdDeviation="30"/></filter>
      </defs>
      
      <!-- BG -->
      <g clip-path="url(#cp)">{bg}<rect width="100%" height="100%" fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.1)" stroke-width="2" rx="{radius}"/></g>
      
      <!-- 1. IDENTITY ISLAND (Top Left) -->
      <g transform="translate(20, 20)" class="float">
         <rect width="100" height="175" rx="20" fill="rgba(0,0,0,0.3)" stroke="rgba(255,255,255,0.1)"/>
         <g transform="translate(5,5)">
            <g clip-path="url(#av)"><image href="{d['avatar']}" width="90" height="90"/></g>
         </g>
         <!-- Online Dot -->
         <circle cx="85" cy="85" r="12" fill="{d['color']}" stroke="#111" stroke-width="3"/>
         
         <text x="50" y="125" text-anchor="middle" font-family="Outfit" font-weight="900" font-size="18" fill="white">{d['name'][:8]}</text>
         <text x="50" y="145" text-anchor="middle" font-family="Rajdhani" font-size="10" fill="#AAA" letter-spacing="1">ID:{d['id'][:4]}</text>
      </g>

      <!-- 2. STATUS ISLAND (Top Right) -->
      <g transform="translate(130, 20)" class="float">
          <rect width="350" height="50" rx="12" fill="rgba(0,0,0,0.3)" stroke="rgba(255,255,255,0.1)"/>
          <text x="20" y="32" font-family="Rajdhani" font-weight="700" font-size="24" fill="{d['color']}">ACTIVE STATUS</text>
          <line x1="330" y1="10" x2="330" y2="40" stroke="rgba(255,255,255,0.2)" stroke-width="2"/>
          <!-- Blink -->
          <circle cx="310" cy="25" r="5" fill="#00FF99" class="pulse"/>
      </g>
      
      <!-- 3. ACTIVITY ISLAND (Bottom Right) -->
      {act_panel}

    </svg>"""

# ===========================
#        MAIN HANDLER
# ===========================

@app.route('/superbadge/<key>')
@app.route('/badge/<mode>/<key>')
def handler(key, mode="auto"):
    args = request.args
    target_mode = mode
    if mode == "auto":
        target_mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
        
    data = fetch_data(key, target_mode, args)
    if not data: return Response('<svg xmlns="http://www.w3.org/2000/svg" width="500" height="100"><rect width="100%" height="100%" fill="#111"/><text x="20" y="60" fill="red" font-family="sans-serif">FETCH_ERROR</text></svg>', mimetype="image/svg+xml")

    # Parsing Settings
    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    
    bg_col = args.get('bg', '09090b').replace('#','')
    radius = args.get('borderRadius', '25').replace('px', '') # Tighter default for split view

    css = get_css(bg_an, fg_an)
    
    # We default to the new "Split Glass" renderer which handles activity auto-resizing
    svg = render_split_glass(data, css, radius, bg_col)

    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
