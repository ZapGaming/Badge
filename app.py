import base64
import requests
import os
import html
import re
import time
from flask import Flask, Response, request, jsonify

app = Flask(__name__)

# ===========================
#        CONFIGURATION
# ===========================
HEADERS = {'User-Agent': 'HyperBadge/Titan-v50-Stable'}
# 1x1 Transparent Pixel
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
CACHE = {}

CONN_MAP = {
    "github": "github", "steam": "steam", "twitch": "twitch", "spotify": "spotify",
    "twitter": "x", "reddit": "reddit", "youtube": "youtube", "xbox": "xbox", 
    "playstation": "playstation", "tiktok": "tiktok", "instagram": "instagram"
}
SIMPLE_ICONS_BASE = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/"

# Platform SVG Paths
PLAT_ICONS = {
    "mobile": "M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z",
    "desktop": "M21 2H3c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h7v2H8v2h8v-2h-2v-2h7c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H3V4h18v12z",
    "web": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"
}

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text).replace('\n', ' ')
    # Remove ASCII control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    # Remove custom discord emojis
    text = re.sub(r'<a?:.+?:\d+>', '', text)
    return html.escape(text, quote=True)

def get_base64(url, is_svg=False):
    """Robust image fetcher"""
    if not url: return EMPTY
    # Cache key
    if url in CACHE: return CACHE[url]
    
    try:
        # Convert Discord MP Urls
        if url.startswith("mp:"): url = f"https://media.discordapp.net/{url[3:]}"
        
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            mime = "image/svg+xml" if (is_svg or url.endswith(".svg")) else "image/png"
            b64 = f"data:{mime};base64,{base64.b64encode(r.content).decode('utf-8')}"
            
            # Simple in-memory LRU cache
            if len(CACHE) > 50: CACHE.clear()
            CACHE[url] = b64
            return b64
    except: pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    # XML Safe Font Import
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

def fetch_data(key, type_mode, args, for_html=False):
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
                "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY
            }

        # 2. USER MODE
        else:
            # --- FETCH ---
            dcdn_user, badges_list, conn_list, banner_url = {}, [], [], None
            
            # A. DCDN Profile
            try:
                r_prof = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=3)
                if r_prof.status_code == 200:
                    prof_json = r_prof.json()
                    if 'user' in prof_json:
                        dcdn_user = prof_json['user']
                        banner_url = dcdn_user.get('banner')
                        for b in prof_json.get('badges', []):
                            u = f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png"
                            badges_list.append(u if for_html else get_base64(u))
                        
                        seen = set()
                        for c in prof_json.get('connected_accounts', []):
                            if c['type'] in CONN_MAP and c['type'] not in seen:
                                url = f"{SIMPLE_ICONS_BASE}{CONN_MAP[c['type']]}.svg"
                                val = url if for_html else get_base64(url, is_svg=True)
                                conn_list.append({'type': c['type'], 'src': val})
                                seen.add(c['type'])
            except: pass

            # B. Lanyard Presence
            r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            lan_json = r_lan.json()
            if not lan_json.get('success'): return None
            
            d = lan_json['data']
            u = d['discord_user']
            status = d['discord_status']
            
            platforms = []
            if d.get('active_on_discord_desktop'): platforms.append("desktop")
            if d.get('active_on_discord_mobile'): platforms.append("mobile")
            if d.get('active_on_discord_web'): platforms.append("web")

            # --- ACTIVITY ---
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#ed4245", "offline": "#80848e", "spotify": "#1DB954"}
            main_act = None

            # 1. Spotify Priority
            if d.get('spotify'):
                s = d['spotify']
                main_act = {
                    "header": "LISTENING TO SPOTIFY", "title": s['song'], "detail": s['artist'],
                    "image": s.get('album_art_url'), "color": cols['spotify'], 
                    "start": s['timestamps']['start'], "end": s['timestamps']['end'], "is_music": True
                }
            # 2. Rich Presence
            elif d.get('activities'):
                for act in d['activities']:
                    if act['type'] == 4: continue
                    img_url = None
                    if 'assets' in act and 'large_image' in act['assets']:
                        aid = act['application_id']; imid = act['assets']['large_image']
                        if imid.startswith("mp:"): img_url = f"https://media.discordapp.net/{imid[3:]}"
                        else: img_url = f"https://cdn.discordapp.com/app-assets/{aid}/{imid}.png"
                    
                    header = f"PLAYING {act['name'].upper()}" if act['type']==0 else "ACTIVITY"
                    main_act = {
                        "header": header, "title": act.get('details', act['name']),
                        "detail": act.get('state', ''), "image": img_url,
                        "color": cols.get(status, "#5865F2"), "start":0, "end":0, "is_music": False
                    }
                    break
            
            if not main_act:
                msg = args.get('idleMessage', 'Chilling')
                for act in d.get('activities', []):
                    if act['type'] == 4: msg = act.get('state', msg); break
                
                main_act = {
                    "header": "CURRENT STATUS", "title": msg, 
                    "detail": "Online" if status!='offline' else "Offline",
                    "image": None, "color": cols.get(status, "#555"), "is_music": False, "start":0, "end":0
                }

            # Naming
            final_name = force_name if force_name else (dcdn_user.get('global_name') or u['global_name'] or u['username'])
            u_avatar = f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"
            
            # --- FINAL OBJECT ---
            if for_html:
                return {
                    "name": final_name, "uid": u['id'], "avatar": u_avatar, 
                    "banner": banner_url, "status_color": cols.get(status, "#888"), 
                    "bio": dcdn_user.get('bio', ''),
                    "badges": badges_list, "connections": conn_list, 
                    "activity": main_act, "platforms": platforms
                }
            else:
                # Determine SVG Background Logic
                if main_act['image']: # Activity Art takes priority if exists
                    bg_final = get_base64(main_act['image'])
                elif banner_url: # Then Banner
                    bg_final = get_base64(banner_url)
                else: # Fallback to Avatar
                    bg_final = get_base64(u_avatar)

                return {
                    "type": "user",
                    "name": sanitize_xml(final_name),
                    "title": sanitize_xml(main_act['title']),
                    "detail": sanitize_xml(main_act['detail']),
                    "app_name": sanitize_xml(main_act['header']),
                    "color": main_act['color'],
                    "status_color": cols.get(status, "#80848e"),
                    "avatar": get_base64(u_avatar),
                    "banner_image": bg_final, # Correctly set
                    "act_image": get_base64(main_act['image']) if main_act['image'] else None,
                    "bio": sanitize_xml(dcdn_user.get('bio', 'No Bio Set.')),
                    "badges": badges_list,
                    "connections": [c['src'] for c in conn_list], 
                    "platforms": platforms,
                    "sub_id": u['id'],
                    "is_music": main_act['is_music'],
                    "progress": 0 # Not calculated for static SVG
                }

    except: return None

# ===========================
#      SVG RENDERER
# ===========================

def render_svg(d, css, radius, bg_col):
    """
    Fixed Layout Titan Renderer
    """
    # 1. Backgrounds
    bg_svg = f"""<rect width="100%" height="100%" fill="#{bg_col}" /><image href="{d['banner_image']}" width="100%" height="150%" y="-15%" preserveAspectRatio="xMidYMid slice" opacity="0.5" filter="url(#heavyBlur)" class="bg-drift"/><rect width="100%" height="100%" fill="url(#vig)"/>"""
    
    # 2. Activity Dock Logic
    if d['act_image']:
        act_viz = f"""<image href="{d['act_image']}" x="25" y="195" width="85" height="85" rx="14" preserveAspectRatio="xMidYMid slice" /><rect x="25" y="195" width="85" height="85" rx="14" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>"""
        txt_pos = 135
        # Music Bars
        eq = f'<g transform="translate(145, -5)"><rect class="eq-bar" x="0" y="4" width="3" height="8" rx="1" fill="#0f0"/><rect class="eq-bar" x="5" y="1" width="3" height="14" rx="1" fill="#0f0" style="animation-delay:0.1s"/><rect class="eq-bar" x="10" y="5" width="3" height="6" rx="1" fill="#0f0" style="animation-delay:0.2s"/></g>' if d['is_music'] else ""
    else:
        act_viz = f"""<rect x="25" y="195" width="85" height="85" rx="14" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.1)"/><text x="68" y="248" text-anchor="middle" font-family="Outfit" font-size="32" fill="{d['color']}">⚡</text>"""
        txt_pos = 135
        eq = ""

    # 3. Icons
    badge_group = "".join([f'<image href="{b}" x="{i*28}" y="0" width="22" height="22" class="badge-pop" style="animation-delay:{i*0.05}s"/>' for i,b in enumerate(d.get('badges', []))])
    
    conn_group = "".join([f'<image href="{c}" x="{i*34}" y="0" width="22" height="22" filter="url(#invert)" opacity="0.7"/>' for i,c in enumerate(d.get('connections', [])[:6])])

    # 4. Platforms
    plat_svg = ""
    px = 840
    for p in d.get('platforms', []):
        icon = PLAT_ICONS.get(p)
        if icon:
             plat_svg += f'<path transform="translate({px}, 0) scale(1.1)" d="{icon}" fill="{d["status_color"]}" opacity="0.9" />'
             px -= 26
    plat_group = f'<g transform="translate(0, 30)">{plat_svg}</g>'

    # Text truncate
    t_tit = d['title'][:32] + (".." if len(d['title'])>32 else "")

    return f"""<svg width="880" height="320" viewBox="0 0 880 320" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css} 
        .title{{font-family:'Pacifico',cursive;fill:white;text-shadow:0 4px 8px rgba(0,0,0,0.6);}}
        .head{{font-family:'Outfit',sans-serif;font-weight:800;text-transform:uppercase;}} .sub{{font-family:'Poppins',sans-serif;opacity:0.9;}} 
        .mono{{font-family:'JetBrains Mono',monospace;opacity:0.6;}}</style>
        <clipPath id="cp"><rect width="880" height="320" rx="{radius}"/></clipPath><clipPath id="avc"><circle cx="75" cy="75" r="75"/></clipPath>
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="50"/></filter><filter id="ds"><feDropShadow dx="0" dy="4" flood-opacity="0.6"/></filter>
        <filter id="invert"><feColorMatrix type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0"/></filter>
        <linearGradient id="vig" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="rgba(0,0,0,0.3)"/><stop offset="1" stop-color="#000" stop-opacity="0.95"/></linearGradient>
        <linearGradient id="shine" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="white" stop-opacity="0.04"/><stop offset="1" stop-color="white" stop-opacity="0"/></linearGradient>
      </defs>
      
      <g clip-path="url(#cp)">
        {bg_svg}
        <rect width="876" height="316" x="2" y="2" rx="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="2"/>
        <rect x="-400" width="200" height="320" fill="white" opacity="0.03" transform="skewX(-20)" class="shiny"/>
      </g>
      
      <!-- Top Section -->
      <g transform="translate(40,40)">
         <circle cx="75" cy="75" r="79" fill="#18181c"/><circle cx="75" cy="75" r="76" fill="none" stroke="{d['color']}" stroke-width="4" stroke-dasharray="16 10" class="pulsing"/><g clip-path="url(#avc)"><image href="{d['avatar']}" width="150" height="150"/></g><circle cx="125" cy="125" r="18" fill="#121212"/><circle cx="125" cy="125" r="13" fill="{d['status_color']}" class="status-breathe"/>
         
         <g transform="translate(180, 20)">
            <g transform="translate(5, -15)">{badge_group}</g>
            <text x="0" y="55" class="title" font-size="60">{d['name']}</text>
            <text x="10" y="80" class="mono" font-size="12">ID :: {d['sub_id']}</text>
            <!-- Proper Bio Wrap -->
            <foreignObject x="5" y="90" width="550" height="60">
                <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'Poppins';font-size:16px;color:#ccc;line-height:1.4;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;opacity:0.9;">
                  {d['bio']}
                </div>
            </foreignObject>
         </g>
      </g>
      
      {plat_group}

      <!-- Bottom Section -->
      <g transform="translate(20, 195)" class="slide-in">
          <rect width="840" height="110" rx="20" fill="rgba(30,30,35,0.6)" stroke="{d['color']}" stroke-opacity="0.3" stroke-width="2"/>
          <rect width="840" height="110" rx="20" fill="url(#shine)"/>
          
          {act_viz}
          
          <g transform="translate({txt_pos}, 28)">
              <g><text x="0" y="0" class="mono" font-size="11" fill="{d['color']}" letter-spacing="1.5" font-weight="bold">{d['app_name']}</text>{eq}</g>
              <text x="0" y="32" class="head" font-size="28" fill="white" filter="url(#ds)">{t_tit}</text>
              <text x="0" y="56" class="sub" font-size="15" fill="#BBB">{d['detail'][:60]}</text>
          </g>
          
          <!-- Connections Bottom Right -->
          <g transform="translate(630, 42)">{conn_group}</g>
      </g>

    </svg>"""

# ===========================
#      CONTROLLER
# ===========================

@app.route('/superbadge/<key>')
def handler(key):
    args = request.args
    # HTML mode redirects/renders logic if needed, but omitted for SVG focus
    
    # 1. Fetch
    mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    data = fetch_data(key, mode, args, for_html=False)
    
    if not data:
         return Response('<svg xmlns="http://www.w3.org/2000/svg" width="880" height="320"><rect width="100%" height="100%" fill="#111"/><text x="50%" y="50%" fill="red" text-anchor="middle">FETCH ERROR</text></svg>', mimetype="image/svg+xml")

    # 2. Config
    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '111111').replace('#','')
    radius = args.get('borderRadius', '30').replace('px', '')
    
    css = get_css(bg_an, fg_an)

    # 3. Render
    if data['type'] == 'discord':
         svg = f'<svg width="400" height="100" xmlns="http://www.w3.org/2000/svg"><defs><style>{css}</style></defs><rect width="100%" height="100%" rx="{radius}" fill="#{bg_col}"/><image href="{data["avatar"]}" width="60" height="60" x="20" y="20"/><text x="100" y="45" font-family="Outfit" fill="white" font-size="22">{data["name"]}</text><text x="100" y="70" font-family="JetBrains Mono" fill="#5865F2">{data["title"]}</text></svg>'
    else:
         svg = render_mega_profile(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

@app.route('/')
def home(): return "TITAN V50 ONLINE"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
