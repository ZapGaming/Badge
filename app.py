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
HEADERS = {'User-Agent': 'HyperBadge/DCDN-Centric-v34'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
CACHE = {}

# BADGE_URLS: Mapping Discord Connection Types to Icons (DCDN does not give icon URLs for custom connections)
# Note: You can expand this with more social media icons as needed
CONNECTION_ICONS = {
    "twitch": "https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Twitch.svg",
    "youtube": "https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Youtube.svg",
    "github": "https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Github-Dark.svg",
    "twitter": "https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/X.svg",
    "reddit": "https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Reddit.svg",
    "spotify": "https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Spotify-Dark.svg",
}

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text)
    # Remove control chars (0-31)
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
    except: pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Outfit:wght@400;700;900&amp;family=Pacifico&amp;family=Poppins:wght@400;600&amp;display=swap');"
    
    keyframes = """
    @keyframes fade { 0%{opacity:0.4} 50%{opacity:0.8} 100%{opacity:0.4} }
    @keyframes d { from{transform:scale(1.02) rotate(0deg)} to{transform:scale(1.1) rotate(1deg)} }
    @keyframes p { 0%{stroke-width:2px; stroke-opacity:0.8} 50%{stroke-width:6px; stroke-opacity:0.3} 100%{stroke-width:2px; stroke-opacity:0.8} }
    @keyframes slide { 0%{transform:translateX(-10px);opacity:0} 100%{transform:translateX(0);opacity:1} }
    @keyframes pop { 0%{transform:scale(0); opacity:0} 100%{transform:scale(1); opacity:1} }
    """
    
    classes = ""
    if str(bg_anim).lower() != 'false': classes += ".bg-drift{animation:d 40s linear infinite alternate} .pulse-bg{animation:fade 4s infinite}"
    if str(fg_anim).lower() != 'false': classes += ".slide-in{animation:slide 0.8s ease-out} .status-pulse{animation:p 2s infinite} .badge-pop{animation:pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) backwards}"
    return css + keyframes + classes

# ===========================
#      DATA FETCHING (DCDN PRIMARY)
# ===========================

def fetch_data(user_id, args):
    try:
        force_name = args.get('name')
        
        # --- 1. DCDN PROFILE DATA (PRIMARY SOURCE for Banner, Badges, Bio, Avatar, Name) ---
        dcdn_data = {}
        # Fetch, but ignore errors if DCDN is down. We'll fallback.
        try:
            r_dcdn = requests.get(f"https://dcdn.dstn.to/profile/{user_id}", headers=HEADERS, timeout=4)
            if r_dcdn.status_code == 200:
                dcdn_json = r_dcdn.json()
                if dcdn_json.get('user'):
                    dcdn_data = dcdn_json['user']
                    # Badges
                    if dcdn_json.get('badges'):
                        dcdn_data['badges'] = [get_base64(b['icon']) for b in dcdn_json['badges']]
                    # Connections (Grab icons)
                    dcdn_data['connections'] = []
                    if dcdn_json.get('connected_accounts'):
                        for conn in dcdn_json['connected_accounts']:
                            platform = conn.get('type') # e.g., github, twitch
                            if platform and CONNECTION_ICONS.get(platform):
                                dcdn_data['connections'].append(get_base64(CONNECTION_ICONS[platform]))
            
        except Exception as e:
            print(f"DCDN fetch error for {user_id}: {e}")

        # --- 2. LANYARD LIVE PRESENCE (SECONDARY SOURCE for Activities, Real-time Status) ---
        lanyard_data = {}
        try:
            r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{user_id}", headers=HEADERS, timeout=4)
            if r_lan.status_code == 200 and r_lan.json().get('success'):
                lanyard_data = r_lan.json()['data']
        except Exception as e:
            print(f"Lanyard fetch error for {user_id}: {e}")
            
        # --- CONSOLIDATE DATA ---
        u_name = dcdn_data.get('global_name') or dcdn_data.get('username') or "UNKNOWN USER"
        display_name = force_name if force_name else u_name
        
        # Determine Color (from Lanyard or default grey)
        lanyard_status = lanyard_data.get('discord_status', 'offline')
        cols = {"online": "#00FF99", "idle": "#FFBD00", "dnd": "#ED4245", "offline": "#747F8D", "spotify": "#1DB954"}
        activity_color = cols['spotify'] if lanyard_data.get('spotify') else cols.get(lanyard_status, "#5865F2")

        # Avatar
        u_avatar = get_base64(dcdn_data.get('avatar')) if dcdn_data.get('avatar') else EMPTY

        # Banner
        banner_bg = get_base64(dcdn_data.get('banner')) if dcdn_data.get('banner') else u_avatar

        # Bio
        user_bio = clean_discord_text(dcdn_data.get('bio', "No bio available."))[:90]

        # --- ACTIVITY Parsing (from Lanyard) ---
        activity_header = ""
        activity_title = "No Status"
        activity_detail = ""
        activity_image = None
        
        # A. Spotify (Prioritize)
        if lanyard_data.get('spotify'):
            s = lanyard_data['spotify']
            activity_header = "LISTENING TO SPOTIFY"
            activity_title = s['song']
            activity_detail = f"by {s['artist']} ({s['album']})"
            activity_image = get_base64(s.get('album_art_url'))
            
        # B. Rich Presence (Games, Watching)
        elif lanyard_data.get('activities'):
            for act in lanyard_data['activities']:
                if act['type'] == 4: continue # Skip custom status
                
                # Image asset
                if 'assets' in act and 'large_image' in act['assets']:
                    app_id = act['application_id']
                    asset_id = act['assets']['large_image']
                    if asset_id.startswith("mp:"): img = f"https://media.discordapp.net/{asset_id[3:]}"
                    else: img = f"https://cdn.discordapp.com/app-assets/{app_id}/{asset_id}.png"
                    activity_image = get_base64(img)

                # Format activity name nicely
                header = act['name'].upper()
                if act['type'] == 0: header = f"PLAYING {header}"
                if act['type'] == 3: header = f"WATCHING {header}"

                activity_header = header
                activity_title = act.get('details', act['name'])
                activity_detail = act.get('state', '')
                break
        
        # C. Custom Status / Basic Status
        else:
            idle_msg = args.get('idleMessage', 'Zzz...')
            for act in lanyard_data.get('activities', []):
                if act['type'] == 4: activity_title = act.get('state', idle_msg); break

            if activity_title == "No Status": activity_title = idle_msg # Default to idle msg if empty
            activity_header = lanyard_status.upper()
            activity_detail = ""

        # --- FINAL DATA CONSOLIDATION (for Renderer) ---
        return {
            "type": "user",
            "name": clean_discord_text(display_name),
            "user_title": clean_discord_text(activity_title), # e.g., Kaiju No. 8
            "user_detail": clean_discord_text(activity_detail), # e.g., Episode 10
            "app_name": clean_discord_text(activity_header), # e.g., WATCHING CRUNCHYROLL
            "color": activity_color, # Dominant status color
            "avatar": u_avatar,
            "act_image": activity_image, # Small square in Activity pane
            "banner_image": banner_bg, # Large BG blur
            "bio": user_bio,
            "badges": dcdn_data.get('badges', []),
            "connections": dcdn_data.get('connections', []),
            "sub_id": user_id
        }
    except Exception as e:
        print(f"Fatal Fetch Error: {e}")
        return None

# ===========================
#      RENDER ENGINE (MEGA)
# ===========================

def render_mega_profile(d, css, radius):
    """
    Titan v34 Mega Renderer (600x290) - DCDN Centric
    """
    
    # Background Logic: Use Banner from DCDN, heavily blurred
    bg_svg = f"""
    <rect width="100%" height="100%" fill="#121212" rx="{radius}" />
    <image href="{d['banner_image']}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.4" filter="url(#heavyBlur)" class="bg-drift"/>
    <!-- Gradient Overlay for text contrast -->
    <rect width="100%" height="100%" fill="url(#vig)"/>
    """

    # Badges Row (Public Flags, Nitro etc.)
    badges_svg = ""
    offset = 0
    # Show up to 6 badges. Badges from DCDN are already base64
    for i, b_b64 in enumerate(d['badges'][:6]): 
        badges_svg += f'<image href="{b_b64}" x="{offset}" y="0" width="22" height="22" class="badge-pop" style="animation-delay:{i*0.1}s"/>'
        offset += 26 # Spacing

    # Connections (Twitch, Github, etc.)
    connections_svg = ""
    c_offset = 0
    for i, c_b64 in enumerate(d['connections'][:3]): # Limit to 3 for space
        connections_svg += f'<image href="{c_b64}" x="{c_offset}" y="0" width="22" height="22" class="badge-pop" style="animation-delay:{0.2 + i*0.1}s"/>'
        c_offset += 26

    # Activity Panel
    if d['act_image']:
        act_thumb = f"""
        <g transform="translate(18, 12)">
           <image href="{d['act_image']}" width="60" height="60" rx="8" preserveAspectRatio="xMidYMid slice" />
           <rect width="60" height="60" rx="8" fill="none" stroke="rgba(255,255,255,0.15)"/>
        </g>
        """
        act_text_start = 90
    else:
        act_thumb = f"""
        <g transform="translate(18, 12)"><rect width="60" height="60" rx="8" fill="rgba(0,0,0,0.4)"/><text x="30" y="38" text-anchor="middle" font-family="Outfit" font-size="28" fill="{d['color']}">⚡</text></g>
        """
        act_text_start = 90
        
    return f"""<svg width="600" height="290" viewBox="0 0 600 290" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}
          .b {{ font-family: 'Outfit', sans-serif; font-weight: 800; }}
          .m {{ font-family: 'JetBrains Mono', monospace; font-weight: 500; }}
          .script {{ font-family: 'Pacifico', cursive; }}
          .poppins {{ font-family: 'Poppins', sans-serif; font-weight: 400; }}
          .txt-main {{ fill: white; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }}
        </style>
        
        <clipPath id="cp"><rect width="600" height="290" rx="{radius}"/></clipPath>
        <clipPath id="avClip"><circle cx="60" cy="60" r="60"/></clipPath>
        <clipPath id="actClip"><rect width="60" height="60" rx="8"/></clipPath>
        
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="25"/></filter>
        
        <linearGradient id="vig" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stop-color="#000" stop-opacity="0.5"/>
            <stop offset="100%" stop-color="#000" stop-opacity="0.9"/>
        </linearGradient>
        <linearGradient id="shineTop" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="white" stop-opacity="0.1"/>
            <stop offset="100%" stop-color="white" stop-opacity="0"/>
        </linearGradient>
      </defs>

      <!-- BASE CARD -->
      <g clip-path="url(#cp)">
        {bg_svg}
        <rect width="596" height="286" x="2" y="2" rx="{radius}" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="2"/>
      </g>
      
      <!-- HEADER CONTENT (Avatar + Name) -->
      <g transform="translate(30, 30)">
         <!-- Status Ring -->
         <circle cx="60" cy="60" r="66" fill="none" stroke="{d['color']}" stroke-width="3" stroke-dasharray="15 8" opacity="0.6" class="bg-drift"/>
         
         <g clip-path="url(#avClip)">
             <image href="{d['avatar']}" width="120" height="120"/>
         </g>
         <!-- Status Dot -->
         <circle cx="105" cy="105" r="14" fill="{d['color']}" stroke="#121212" stroke-width="4"/>
         
         <!-- Discord Badges Row -->
         <g transform="translate(0, 140)">
            {badges_svg}
         </g>
      </g>

      <!-- USER INFO: Name, ID, Bio -->
      <g transform="translate(180, 45)">
         <text x="0" y="0" class="script" font-size="44" fill="white" filter="url(#textShad)">
            {d['name']}
         </text>
         
         <text x="5" y="25" class="m" font-size="10" fill="#999" letter-spacing="1">ID: {d['sub_id']}</text>
         
         <g transform="translate(0, 55)">
             <rect width="400" height="1" fill="#444"/>
             <text x="5" y="20" class="poppins" font-size="14" fill="#DDD">{d['bio'][:45]}</text>
             <text x="5" y="38" class="poppins" font-size="14" fill="#DDD">{d['bio'][45:90]}</text>
         </g>
      </g>
      
      <!-- BOTTOM: Activity Island -->
      <g transform="translate(30, 190)" class="slide-in">
          <!-- Glass Panel -->
          <rect width="540" height="85" rx="16" fill="rgba(20, 20, 25, 0.7)" stroke="{d['color']}" stroke-opacity="0.3" stroke-width="1.5"/>
          
          {act_thumb}
          
          <g transform="translate({act_text_start}, 20)">
             <!-- Activity Header -->
             <text x="0" y="0" class="m" font-size="10" fill="{d['color']}" letter-spacing="2" font-weight="bold">
                 {d['app_name']}
             </text>
             <!-- Title -->
             <text x="0" y="24" class="b txt-main" font-size="20" >
                 {d['user_title'][:30] + '...' if len(d['user_title'])>30 else d['user_title']}
             </text>
             <!-- Detail -->
             <text x="0" y="42" class="b" font-size="13" fill="#AAA">
                 {d['user_detail'][:45]}
             </text>
             
             <!-- Connections Row -->
             <g transform="translate(0, 50)">{connections_svg}</g>
          </g>
      </g>

    </svg>"""

# ===========================
#        CONTROLLER
# ===========================

@app.route('/superbadge/<key>')
def handler(key):
    args = request.args
    # User only mode (this API version does not support servers/github yet for this layout)
    
    data = fetch_data(key, args)
    
    if not data or data.get('type') == 'error': 
         return Response('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="290"><rect width="100%" height="100%" fill="#111"/><text x="50%" y="50%" text-anchor="middle" fill="red" font-family="sans-serif">PROFILE ERROR: USER NOT FOUND</text></svg>', mimetype="image/svg+xml")

    # Render settings
    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '111111').replace('#','')
    radius = args.get('borderRadius', '30').replace('px', '') # Default large for profile

    css = get_css(bg_an, fg_an)
    svg = render_mega_profile(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

@app.route('/')
def home(): return "TITAN MEGA PROFILE V34 ONLINE (USER MODE ONLY)"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
