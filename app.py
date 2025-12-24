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
HEADERS = {'User-Agent': 'HyperBadge/MegaProfile-v32'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
CACHE = {}

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text)
    # Remove control chars (0-31) except newline
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    # Escape entities
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
    # Expanded Font Stack
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Outfit:wght@400;700;900&amp;family=Pacifico&amp;family=Poppins:wght@400;600&amp;display=swap');"
    
    keyframes = """
    @keyframes fade { 0%{opacity:0.6} 50%{opacity:1} 100%{opacity:0.6} }
    @keyframes d { from{transform:scale(1.05) rotate(0deg)} to{transform:scale(1.15) rotate(1deg)} }
    @keyframes p { 0%{stroke-width:2px; stroke-opacity:0.8} 50%{stroke-width:6px; stroke-opacity:0.3} 100%{stroke-width:2px; stroke-opacity:0.8} }
    @keyframes slide { 0%{transform:translateX(-15px);opacity:0} 100%{transform:translateX(0);opacity:1} }
    @keyframes badgePop { 0%{transform:scale(0); opacity:0} 100%{transform:scale(1); opacity:1} }
    """
    
    classes = ""
    if str(bg_anim).lower() != 'false':
        classes += ".bg-drift{animation:d 40s linear infinite alternate}"
    if str(fg_anim).lower() != 'false':
        classes += ".slide-in{animation:slide 0.8s ease-out} .status-pulse{animation:p 2s infinite} .badge-pop{animation:badgePop 0.5s ease-out backwards}"

    return css + keyframes + classes

# ===========================
#      DATA LOGIC (DUAL-SOURCE)
# ===========================

def fetch_data(key, type_mode, args):
    try:
        force_name = args.get('name')

        # --- 1. DISCORD SERVER ---
        if type_mode == 'discord':
            # ... (Standard Server Logic kept for compatibility) ...
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
                "bg_image": None, "sub_id": g['id'], "badges": [], "bio": ""
            }

        # --- 2. USER MODE (LANYARD + DCDN) ---
        else:
            # --- FETCH 1: PROFILE DATA (DCDN) ---
            # Used for Badges, Banner, Bio
            dcdn_data = {}
            badges_list = []
            bio_text = ""
            banner_img = None
            try:
                r_prof = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=4)
                if r_prof.status_code == 200:
                    prof = r_prof.json()
                    
                    # 1. Bio
                    bio_text = prof['user'].get('bio', '') or "No bio available."
                    
                    # 2. Badges (Icons)
                    if 'badges' in prof:
                        for b in prof['badges']:
                            # Get the icon url (hosted on dstn.to)
                            badges_list.append(get_base64(b['icon']))
                    
                    # 3. Banner
                    banner_url = prof['user'].get('banner') # DCDN provides full URL usually
                    if banner_url: banner_img = get_base64(banner_url)
            except Exception as e:
                print(f"DCDN Error: {e}")

            # --- FETCH 2: LIVE STATUS (LANYARD) ---
            # Used for Spotify, Games, Status
            r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            lan_resp = r_lan.json()
            
            # Data Structs
            u_name = "User"
            status = "offline"
            d_avatar = EMPTY
            main_act = None
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#ED4245", "offline": "#747F8D", "spotify": "#1DB954"}

            if lan_resp.get('success'):
                data = lan_resp['data']
                user_obj = data['discord_user']
                u_name = force_name if force_name else (user_obj.get('global_name') or user_obj['username'])
                status = data['discord_status']
                d_avatar = get_base64(f"https://cdn.discordapp.com/avatars/{user_obj['id']}/{user_obj['avatar']}.png")
                
                # Activity Parser
                # 1. Spotify
                if data.get('spotify'):
                    s = data['spotify']
                    main_act = {
                        "header": "LISTENING TO SPOTIFY",
                        "title": s['song'],
                        "detail": f"by {s['artist']}",
                        "image": s.get('album_art_url'),
                        "color": cols['spotify']
                    }
                # 2. Rich Presence
                elif data.get('activities'):
                    for act in data['activities']:
                        if act['type'] == 4: continue # Skip custom status
                        
                        img_url = None
                        if 'assets' in act and 'large_image' in act['assets']:
                            aid = act['application_id']
                            img_id = act['assets']['large_image']
                            if img_id.startswith("mp:"): img_url = f"https://media.discordapp.net/{img_id[3:]}"
                            else: img_url = f"https://cdn.discordapp.com/app-assets/{aid}/{img_id}.png"
                        
                        main_act = {
                            "header": f"PLAYING {act['name'].upper()}",
                            "title": act.get('details', act['name']),
                            "detail": act.get('state', ''),
                            "image": img_url,
                            "color": cols.get(status, "#5865F2")
                        }
                        break

            # Fallback if Lanyard fails or idle
            if not main_act:
                main_act = {
                    "header": "CURRENTLY IDLE",
                    "title": args.get('idleMessage', 'Relaxing').title(),
                    "detail": "No active status",
                    "image": None,
                    "color": cols.get(status, "#555")
                }
            
            # Use Avatar if no Album art
            bg_final = get_base64(main_act['image']) if main_act['image'] else d_avatar
            
            return {
                "type": "user",
                "name": sanitize_xml(u_name),
                "title": sanitize_xml(main_act['title']),
                "detail": sanitize_xml(main_act['detail']),
                "app_name": sanitize_xml(main_act['header']),
                "color": main_act['color'],
                "avatar": d_avatar,
                "act_image": get_base64(main_act['image']), # Activity specific image
                "banner_image": banner_img if banner_img else bg_final, # Banner or fallback to avatar
                "bio": sanitize_xml(bio_text.replace('\n', ' ')),
                "badges": badges_list,
                "sub_id": key
            }

    except Exception as e:
        print(f"Logic Error: {e}")
        return None

# ===========================
#      RENDER ENGINE (MEGA)
# ===========================

def render_mega_profile(d, css, radius, bg_col):
    """
    Titan V32 Mega Renderer (600x290)
    1. Top Banner area with Blur.
    2. Left Column: Big Avatar + User Badges Row.
    3. Right Column: Name + Bio.
    4. Bottom Area: Floating Glass Panel for Activity.
    """
    
    # 1. Background (Banner or Gradient)
    bg = f"""
    <rect width="100%" height="100%" fill="#{bg_col}" />
    <image href="{d['banner_image']}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.3" filter="url(#heavyBlur)" class="bg-drift"/>
    <rect width="100%" height="100%" fill="url(#vig)"/>
    """

    # 2. User Badges Construction
    badges_svg = ""
    bx = 0
    # Limit to 6 badges to fit
    for idx, b_b64 in enumerate(d['badges'][:6]): 
        badges_svg += f'<image href="{b_b64}" x="{bx}" y="0" width="22" height="22" class="badge-pop" style="animation-delay: {idx*0.1}s"/>'
        bx += 28 # spacing

    # 3. Activity Section (Bottom)
    act_thumb = ""
    if d['act_image']:
        act_thumb = f"""
        <image href="{d['act_image']}" x="20" y="15" width="60" height="60" rx="8" preserveAspectRatio="xMidYMid slice" />
        <rect x="20" y="15" width="60" height="60" rx="8" fill="none" stroke="rgba(255,255,255,0.1)" />
        """
        act_text_x = 95
    else:
        act_text_x = 20
        
    return f"""<svg width="600" height="290" viewBox="0 0 600 290" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}
          .b {{ font-family: 'Outfit', sans-serif; font-weight: 800; }}
          .m {{ font-family: 'JetBrains Mono', monospace; font-weight: 500; }}
          .bio {{ font-family: 'Poppins', sans-serif; font-weight: 400; opacity: 0.8; line-height: 1.2; }}
          .script {{ font-family: 'Pacifico', cursive; }}
        </style>
        
        <clipPath id="cp"><rect width="600" height="290" rx="{radius}"/></clipPath>
        <clipPath id="avClip"><circle cx="60" cy="60" r="60"/></clipPath>
        
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="30"/></filter>
        <filter id="textShad"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.8"/></filter>
        
        <linearGradient id="vig" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stop-color="#050505" stop-opacity="0.4"/>
            <stop offset="100%" stop-color="#000" stop-opacity="0.95"/>
        </linearGradient>
      </defs>

      <!-- BASE CARD -->
      <g clip-path="url(#cp)">
        {bg}
        <rect width="596" height="286" x="2" y="2" rx="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="2"/>
      </g>
      
      <!-- TOP LEFT: Identity Cluster -->
      <g transform="translate(30, 30)">
         <!-- Pulse Ring -->
         <circle cx="60" cy="60" r="64" fill="none" stroke="{d['color']}" stroke-width="3" stroke-dasharray="12 6" opacity="0.6" class="bg-drift"/>
         
         <!-- Big Avatar (120px) -->
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

      <!-- TOP RIGHT: Name & Bio -->
      <g transform="translate(180, 45)">
         <!-- Script Name -->
         <text x="0" y="0" class="script" font-size="42" fill="white" filter="url(#textShad)">
            {d['name']}
         </text>
         
         <!-- User ID -->
         <text x="5" y="25" class="m" font-size="10" fill="#999" letter-spacing="1">UID: {d['sub_id']}</text>
         
         <!-- Bio Block (Max 65 chars approx per line logic or truncate) -->
         <text x="5" y="60" class="bio" font-size="14" fill="#DDD">
            {d['bio'][:45]}
         </text>
         <text x="5" y="80" class="bio" font-size="14" fill="#DDD">
            {d['bio'][45:90]}
         </text>
      </g>
      
      <!-- BOTTOM: Activity Island (Floating Glass) -->
      <g transform="translate(30, 190)" class="slide-in">
          <!-- Glass Panel -->
          <rect width="540" height="85" rx="16" fill="rgba(0,0,0,0.4)" stroke="{d['color']}" stroke-opacity="0.3" stroke-width="1"/>
          
          <!-- Activity Info -->
          {act_thumb}
          
          <g transform="translate({act_text_x}, 20)">
             <!-- Header -->
             <text x="0" y="10" class="m" font-size="10" fill="{d['color']}" letter-spacing="2">
                 {d['app_name']}
             </text>
             
             <!-- Song/Game Name -->
             <text x="0" y="32" class="b" font-size="20" fill="white">
                 {d['title'][:32]}
             </text>
             
             <!-- Details -->
             <text x="0" y="50" class="bio" font-size="12" fill="#AAA">
                 {d['detail'][:40]}
             </text>
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
         return Response('<svg xmlns="http://www.w3.org/2000/svg" width="500" height="100"><text x="20" y="50">LOAD ERROR</text></svg>', mimetype="image/svg+xml")

    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '111111').replace('#','')
    radius = args.get('borderRadius', '30').replace('px', '') 

    css = get_css(bg_an, fg_an)

    # Use the new MEGA Renderer
    svg = render_mega_profile(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

@app.route('/')
def home(): return "TITAN MEGA PROFILE V32 ONLINE"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
