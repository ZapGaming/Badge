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
HEADERS = {'User-Agent': 'HyperBadge/Titan-v45-FinalLayout'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
CACHE = {}

# Mappings
CONN_MAP = {
    "github": "github", "steam": "steam", "twitch": "twitch", "spotify": "spotify",
    "twitter": "x", "reddit": "reddit", "youtube": "youtube", "xbox": "xbox", "playstation": "playstation",
    "tiktok": "tiktok", "instagram": "instagram"
}
SIMPLE_ICONS_BASE = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/"

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text)
    # Remove control chars (0-31) except newline/tab
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    # Strip Discord Emojis to keep text aligned/clean
    text = re.sub(r'<a?:.+?:\d+>', '', text)
    return html.escape(text, quote=True)

def get_base64(url, is_svg=False):
    """Robust image fetcher"""
    if not url: return EMPTY
    try:
        # Convert Discord MP Urls
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
    @keyframes bar { 0%{height:4px} 50%{height:14px} 100%{height:4px} }
    """
    classes = ""
    if str(bg_anim).lower() != 'false': 
        classes += ".bg-drift{animation:d 40s linear infinite alternate} .pulsing{animation:pulse 3s infinite} .shiny{animation:glint 6s infinite cubic-bezier(0.4, 0, 0.2, 1)}"
    if str(fg_anim).lower() != 'false': 
        classes += ".slide-in{animation:slide 0.8s ease-out} .badge-pop{animation:pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) backwards} .status-breathe{animation:breathe 3s infinite} .eq-bar{animation:bar 0.8s ease-in-out infinite}"
    return css + keyframes + classes

# ===========================
#      DATA LOGIC
# ===========================

def fetch_data(key, type_mode, args):
    try:
        force_name = args.get('name')

        # 1. SERVER
        if type_mode == 'discord':
            r = requests.get(f"https://discord.com/api/v10/invites/{key}?with_counts=true", headers=HEADERS, timeout=4)
            d = r.json(); g = d.get('guild')
            if not g: return None
            return {
                "type": "discord", "name": sanitize_xml(force_name or g['name']), 
                "title": f"{d.get('approximate_member_count', 0):,} Members",
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY
            }

        # 2. USER
        else:
            # A. Fetch Profile (DCDN)
            dcdn_user, badges_data, connections_data = {}, [], []
            banner_bg = None
            try:
                r_prof = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=3)
                if r_prof.status_code == 200:
                    prof_json = r_prof.json()
                    if 'user' in prof_json:
                        dcdn_user = prof_json['user']
                        # Badges
                        for b in prof_json.get('badges', []):
                            badges_data.append(get_base64(f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png"))
                        # Banner
                        if dcdn_user.get('banner'): 
                            banner_bg = get_base64(dcdn_user['banner'])
                        # Connections (Unique Only)
                        seen_types = set()
                        for c in prof_json.get('connected_accounts', []):
                            ctype = c['type']
                            if ctype in CONN_MAP and ctype not in seen_types:
                                c_url = f"{SIMPLE_ICONS_BASE}{CONN_MAP[ctype]}.svg"
                                connections_data.append(get_base64(c_url, is_svg=True))
                                seen_types.add(ctype)
            except: pass

            # B. Fetch Live Status (Lanyard)
            r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            lan_json = r_lan.json()
            if not lan_json.get('success'): return None
            d, u = lan_json['data'], lan_json['data']['discord_user']
            status = d['discord_status']
            
            # Platforms
            platforms = []
            if d.get('active_on_discord_desktop'): platforms.append("desktop")
            if d.get('active_on_discord_mobile'): platforms.append("mobile")

            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#ed4245", "offline": "#80848e", "spotify": "#1DB954"}
            
            # --- ACTIVITY PARSING ---
            main_act = None

            # 1. Aggressive Spotify Check (Type 2 listening + explicit field)
            is_music = False
            if d.get('spotify'):
                s = d['spotify']
                main_act = {"header": "LISTENING TO SPOTIFY", "title": s['song'], "detail": s['artist'], "image": s.get('album_art_url'), "color": cols['spotify']}
                is_music = True
            
            # 2. Rich Presence
            if not main_act:
                for act in d.get('activities', []):
                    # Spotify sometimes appears as activity, check name or id
                    if act.get('id') == "spotify:1" or act.get('name') == "Spotify":
                        main_act = {
                            "header": "LISTENING TO SPOTIFY", "title": act.get('details','Spotify'), "detail": act.get('state','Music'),
                            "image": f"https://i.scdn.co/image/{act['assets']['large_image'].replace('spotify:','')}" if 'assets' in act else None,
                            "color": cols['spotify']
                        }
                        is_music = True
                        break
                    
                    if act['type'] == 4: continue

                    img_url = None
                    if 'assets' in act and 'large_image' in act['assets']:
                        aid, imid = act['application_id'], act['assets']['large_image']
                        if imid.startswith("mp:"): img_url = f"https://media.discordapp.net/{imid[3:]}"
                        else: img_url = f"https://cdn.discordapp.com/app-assets/{aid}/{imid}.png"
                    
                    h = "WATCHING" if act['type'] == 3 else "PLAYING"
                    main_act = {"header": f"{h} {act['name'].upper()}", "title": act.get('details') or act['name'], "detail": act.get('state') or "", "image": img_url, "color": cols.get(status, "#5865F2")}
                    break
            
            # 3. Fallback
            if not main_act:
                msg = args.get('idleMessage', 'Chilling')
                for act in d.get('activities', []):
                    if act['type'] == 4: msg = act.get('state', msg); break
                
                h_stat = "OFFLINE" if status == 'offline' else "CURRENTLY"
                main_act = {"header": h_stat, "title": msg, "detail": "Online" if status!='offline' else "Offline", "image": None, "color": cols.get(status, "#555")}

            final_name = force_name if force_name else (dcdn_user.get('global_name') or u['global_name'] or u['username'])
            u_avatar = get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png")
            
            # Background Choice: Album Art > Banner > Avatar
            # BUT request says: "when no song... set bg to banner"
            if main_act['image']:
                final_bg = get_base64(main_act['image'])
            elif banner_bg:
                final_bg = banner_bg
            else:
                final_bg = u_avatar

            bio_clean = sanitize_xml(dcdn_user.get('bio', '') or "No bio available.")
            
            return {
                "type": "user",
                "name": sanitize_xml(final_name),
                "title": sanitize_xml(main_act['title']),
                "detail": sanitize_xml(main_act['detail']),
                "app_name": sanitize_xml(main_act['header']),
                "color": main_act['color'],
                "status_color": cols.get(status, "#80848e"),
                "avatar": u_avatar,
                "bg_image": final_bg,
                "act_image": get_base64(main_act['image']) if main_act['image'] else None,
                "bio": bio_clean,
                "badges": badges_data,
                "connections": connections_data,
                "is_music": is_music
            }
    except Exception as e:
        print(e)
        return None

# ===========================
#      RENDER ENGINE (V45)
# ===========================

def render_mega_profile(d, css, radius, bg_col):
    """Layout fixes applied for non-overlapping elements."""
    
    # 1. Background System
    # Added blur, noise, and darkened for legibility
    bg_svg = f"""
    <rect width="100%" height="100%" fill="#{bg_col}" />
    <image href="{d['bg_image']}" width="100%" height="150%" y="-15%" preserveAspectRatio="xMidYMid slice" opacity="0.4" filter="url(#heavyBlur)" class="bg-drift"/>
    <rect width="100%" height="100%" fill="url(#vig)"/>
    """

    # 2. Activity Image (Dock Left)
    if d['act_image']:
        act_viz = f"""
        <image href="{d['act_image']}" x="25" y="195" width="80" height="80" rx="14" />
        <rect x="25" y="195" width="80" height="80" rx="14" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>
        """
        txt_pos = 125
        # Music Equalizer
        eq = ""
        if d['is_music']:
             eq = f"""<g transform="translate(70, -10)">
             <rect class="eq-bar" x="0" y="5" width="3" height="10" rx="1" fill="#0f0" style="animation-delay:0s"/>
             <rect class="eq-bar" x="5" y="2" width="3" height="16" rx="1" fill="#0f0" style="animation-delay:0.1s"/>
             <rect class="eq-bar" x="10" y="7" width="3" height="8" rx="1" fill="#0f0" style="animation-delay:0.2s"/>
             </g>"""
        else: eq = ""
    else:
        # Fallback Icon
        act_viz = f"""
        <rect x="25" y="195" width="80" height="80" rx="14" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.1)"/>
        <text x="65" y="245" text-anchor="middle" font-family="Outfit" font-size="28" fill="{d['color']}">⚡</text>
        """
        txt_pos = 125
        eq = ""

    # 3. Connections Row (De-Duplicated in logic)
    # Right Side of Dock
    conn_group = ""
    cx = 0
    if d.get('connections'):
        for i, c in enumerate(d['connections'][:6]): # Limit 6 icons
            # Use 'invert' to make them white on dark background
            conn_group += f'<image href="{c}" x="{cx}" y="0" width="22" height="22" filter="url(#invert)" opacity="0.6"/>'
            cx += 32
    conn_pos = f'<g transform="translate({800 - cx}, 40)">{conn_group}</g>' # Right Align Logic

    # 4. Badges (Under Avatar now to clear up top-right area)
    badge_group = ""
    if d.get('badges'):
        bx = 0
        b_svg = ""
        for i, b in enumerate(d['badges'][:8]):
             b_svg += f'<image href="{b}" x="{bx}" y="0" width="22" height="22" class="badge-pop" style="animation-delay:{i*0.05}s"/>'
             bx += 28
        # Placing badges above name
        badge_group = f'<g transform="translate(0, -35)">{b_svg}</g>'

    # 5. Text Truncation Logic for Rendering
    title_short = d['title'][:25] + ".." if len(d['title']) > 28 else d['title']

    return f"""<svg width="880" height="320" viewBox="0 0 880 320" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs>
        <style>{css}
          .title {{ font-family: 'Pacifico', cursive; fill: white; text-shadow: 0 4px 8px rgba(0,0,0,0.8); }}
          .head {{ font-family: 'Outfit', sans-serif; font-weight: 800; }}
          .sub {{ font-family: 'Poppins', sans-serif; font-weight: 500; opacity: 0.8; }}
          .mono {{ font-family: 'JetBrains Mono', monospace; opacity: 0.6; }}
        </style>
        
        <clipPath id="cp"><rect width="880" height="320" rx="{radius}"/></clipPath>
        <clipPath id="avc"><circle cx="75" cy="75" r="75"/></clipPath>
        
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="60"/></filter>
        <filter id="invert"><feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"/></filter>
        <filter id="ds"><feDropShadow dx="0" dy="4" stdDeviation="4" flood-opacity="0.6"/></filter>
        
        <linearGradient id="vig" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="rgba(0,0,0,0.2)"/><stop offset="1" stop-color="#000" stop-opacity="0.9"/></linearGradient>
        <linearGradient id="shine" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="white" stop-opacity="0.04"/><stop offset="1" stop-color="white" stop-opacity="0"/></linearGradient>
        <pattern id="noise" width="100" height="100" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="white" opacity="0.03"/></pattern>
      </defs>

      <!-- BASE -->
      <g clip-path="url(#cp)">
        {bg_svg}
        <rect x="-400" width="200" height="320" fill="white" opacity="0.03" transform="skewX(-20)" class="shiny"/>
        <rect width="876" height="316" x="2" y="2" rx="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="2"/>
        <rect width="100%" height="100%" fill="url(#noise)"/>
      </g>
      
      <!-- TOP LEFT PROFILE -->
      <g transform="translate(40, 40)">
         <!-- Avatar Ring -->
         <circle cx="75" cy="75" r="79" fill="#18181c"/>
         <circle cx="75" cy="75" r="76" fill="none" stroke="{d['color']}" stroke-width="4" stroke-dasharray="20 12" class="pulsing"/>
         
         <g clip-path="url(#avc)"><image href="{d['avatar']}" width="150" height="150" /></g>
         <!-- Online Dot -->
         <circle cx="125" cy="125" r="18" fill="#121212"/>
         <circle cx="125" cy="125" r="13" fill="{d['status_color']}" class="status-breathe"/>

         <!-- User Details Stack -->
         <g transform="translate(180, 50)">
            
            {badge_group} <!-- Now above name -->

            <text x="0" y="0" class="title" font-size="60">{d['name']}</text>
            
            <text x="10" y="25" class="mono" font-size="12">UID: {d.get('sub_id','?')}</text>
            
            <!-- Safe Bio Container (Shifted Up and constrained) -->
            <foreignObject x="5" y="40" width="600" height="40">
               <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'Poppins',sans-serif; font-size:14px; color:#ddd; line-height:1.4; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; opacity:0.85;">
                   {d['bio']}
               </div>
            </foreignObject>
         </g>
      </g>

      <!-- BOTTOM DOCK (Activity) -->
      <g transform="translate(20, 200)" class="slide-in">
          <!-- Dock Glass -->
          <rect width="840" height="100" rx="18" fill="rgba(10,10,12,0.6)" stroke="{d['color']}" stroke-opacity="0.3" stroke-width="1.5"/>
          <rect width="840" height="100" rx="18" fill="url(#shine)"/>
          
          {act_viz}
          
          <!-- Text Info -->
          <g transform="translate({txt_pos}, 22)">
              <g>{eq}<text x="0" y="6" class="mono" font-size="10" fill="{d['color']}" letter-spacing="2" font-weight="bold">{d['app_name']}</text></g>
              <text x="0" y="38" class="head" font-size="24" fill="white" filter="url(#ds)">{title_short}</text>
              <text x="0" y="60" class="sub" font-size="14" fill="#AAA">{d['detail'][:55]}</text>
          </g>
          
          {conn_pos}
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
    if not data: return Response('<svg xmlns="http://www.w3.org/2000/svg" width="880" height="320"><rect width="100%" height="100%" fill="#111"/><text x="50%" y="50%" fill="red" text-anchor="middle">ERROR</text></svg>', mimetype="image/svg+xml")

    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '111111').replace('#','')
    radius = args.get('borderRadius', '40').replace('px', '')
    
    css = get_css(bg_an, fg_an)
    svg = render_mega_profile(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
