import base64
import requests
import os
import html
import re
import time
from flask import Flask, Response, request, render_template_string

app = Flask(__name__)

# ===========================
#        CONFIGURATION
# ===========================
HEADERS = {'User-Agent': 'HyperBadge/Titan-v46'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# URL Maps for interactions in HTML mode
CONN_URLS = {
    "github": "https://github.com/{}", "twitch": "https://twitch.tv/{}",
    "steam": "https://steamcommunity.com/id/{}", "spotify": "https://open.spotify.com/user/{}",
    "twitter": "https://twitter.com/{}", "youtube": "https://youtube.com/@{}",
    "reddit": "https://reddit.com/user/{}", "tiktok": "https://tiktok.com/@{}"
}

SIMPLE_ICONS_BASE = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/"
CONN_MAP = {
    "github": "github", "steam": "steam", "twitch": "twitch", "spotify": "spotify",
    "twitter": "x", "reddit": "reddit", "youtube": "youtube",
    "xbox": "xbox", "playstation": "playstation", "tiktok": "tiktok", "instagram": "instagram"
}

# 24x24 Icon Paths (Material Design)
PLATFORM_PATHS = {
    "desktop": "M4 4h16c1.1 0 2 .9 2 2v9c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zm0 2v9h16V6H4zm8 14c-.55 0-1-.45-1-1v-1h2v1c0 .55-.45 1-1 1z",
    "mobile": "M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z",
    "web": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"
}

# ===========================
#      HELPER FUNCTIONS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text).replace('\n', ' ')
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    # Remove Raw Discord Emoji codes <a:name:id>
    text = re.sub(r'<a?:.+?:\d+>', '', text)
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
    @keyframes pan { 0% {background-position: 0% 50%} 100% {background-position: 100% 50%} }
    @keyframes floatY { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-3px); } }
    """
    
    classes = ""
    if str(bg_anim).lower() != 'false': 
        classes += ".bg-drift{animation:d 40s linear infinite alternate} .pulsing{animation:pulse 3s infinite} .shiny{animation:glint 6s infinite cubic-bezier(0.4, 0, 0.2, 1)}"
    if str(fg_anim).lower() != 'false': 
        classes += ".slide-in{animation:slide 0.8s ease-out} .badge-pop{animation:pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) backwards} .status-breathe{animation:breathe 3s infinite} .float{animation:floatY 4s ease-in-out infinite}"
    return css + keyframes + classes

# ===========================
#      DATA LOGIC
# ===========================

def fetch_data(key, type_mode, args):
    try:
        force_name = args.get('name')

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

        else:
            # DCDN (Profile Assets)
            dcdn_user, badges_data, connections_data, banner_bg = {}, [], [], None
            raw_connections = [] 

            try:
                r_prof = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=3)
                if r_prof.status_code == 200:
                    d_json = r_prof.json()
                    dcdn_user = d_json.get('user', {})
                    if dcdn_user.get('banner'): banner_bg = get_base64(dcdn_user['banner'])
                    for b in d_json.get('badges', []):
                        badges_data.append(get_base64(f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png"))
                    
                    # Store Raw Connections for HTML mode & B64 for SVG
                    raw_connections = d_json.get('connected_accounts', [])
                    for c in raw_connections:
                        if c['type'] in CONN_MAP:
                            icon_b64 = get_base64(f"{SIMPLE_ICONS_BASE}{CONN_MAP[c['type']]}.svg", is_svg=True)
                            connections_data.append(icon_b64)
                            c['icon_b64'] = icon_b64
            except: pass

            # Lanyard (Presence)
            r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            lan_json = r_lan.json()
            if not lan_json.get('success'): return None
            
            d = lan_json['data']
            u = d['discord_user']
            status = d['discord_status']

            # Platform Detection
            platforms = []
            if d.get('active_on_discord_desktop'): platforms.append("desktop")
            if d.get('active_on_discord_mobile'): platforms.append("mobile")
            if d.get('active_on_discord_web'): platforms.append("web")

            # Logic
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#ed4245", "offline": "#80848e", "spotify": "#1DB954"}
            status_col = cols.get(status, "#80848e")
            main_act = None

            if d.get('spotify'):
                s = d['spotify']
                main_act = {
                    "header": "LISTENING TO SPOTIFY", "title": s['song'], "detail": s['artist'],
                    "image": s.get('album_art_url'), "color": cols['spotify'], "is_music": True
                }
            elif d.get('activities'):
                for act in d['activities']:
                    if act['type'] == 4: continue
                    img_url = None
                    if 'assets' in act and 'large_image' in act['assets']:
                        aid = act['application_id']; imid = act['assets']['large_image']
                        img_url = f"https://media.discordapp.net/{imid[3:]}" if imid.startswith("mp:") else f"https://cdn.discordapp.com/app-assets/{aid}/{imid}.png"
                    main_act = {
                        "header": (f"WATCHING {act['name']}" if act['type']==3 else f"PLAYING {act['name']}").upper(),
                        "title": act.get('details', act['name']), "detail": act.get('state', ''),
                        "image": img_url, "color": cols.get(status, "#5865F2"), "is_music": False
                    }
                    break
            
            if not main_act:
                msg = args.get('idleMessage', 'Chilling')
                for act in d.get('activities', []):
                    if act['type'] == 4: msg = act.get('state', msg); break
                main_act = {
                    "header": "CURRENTLY", "title": msg, "detail": "Online" if status!='offline' else "Offline",
                    "image": None, "color": cols.get(status, "#555"), "is_music": False
                }

            u_avatar = get_base64(f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png")
            final_bg = banner_bg if banner_bg else u_avatar 

            return {
                "type": "user",
                "name": sanitize_xml(force_name if force_name else (dcdn_user.get('global_name') or u['global_name'] or u['username'])),
                "title": sanitize_xml(main_act['title']),
                "detail": sanitize_xml(main_act['detail']),
                "app_name": sanitize_xml(main_act['header']),
                "color": main_act['color'],
                "status_color": status_col,
                "avatar": u_avatar,
                "banner_image": final_bg,
                "act_image": get_base64(main_act['image']) if main_act['image'] else None,
                "act_image_url": main_act['image'],
                "bio": sanitize_xml(dcdn_user.get('bio', '')),
                "badges": badges_data,
                "connections": connections_data,
                "raw_connections": raw_connections,
                "sub_id": u['id'],
                "platforms": platforms
            }
    except: return None

# ===========================
#      RENDER ENGINES
# ===========================

def render_svg(d, css, radius, bg_col):
    """Titan V45 Hybrid SVG (Added Platform Icons to Top Right)"""
    
    # 1. Backgrounds
    bg_svg = f"""<rect width="100%" height="100%" fill="#{bg_col}" /><image href="{d['banner_image']}" width="100%" height="150%" y="-25%" preserveAspectRatio="xMidYMid slice" opacity="0.4" filter="url(#heavyBlur)" class="bg-drift"/><rect width="100%" height="100%" fill="url(#vig)"/>"""
    
    # 2. Dock Image
    if d['act_image']:
        act_viz = f"""
        <g clip-path="url(#dockClip)">
            <image href="{d['act_image']}" width="840" height="840" x="0" y="-300" opacity="0.4" preserveAspectRatio="xMidYMid slice" filter="url(#blur)"/>
            <rect width="840" height="110" fill="rgba(0,0,0,0.6)"/>
            <image href="{d['act_image']}" x="15" y="15" width="80" height="80" rx="10"/>
        </g>
        """
        txt_x = 110
    else:
        act_viz = f"""<rect width="840" height="110" rx="20" fill="rgba(30,30,35,0.7)"/><rect x="15" y="15" width="80" height="80" rx="10" fill="rgba(255,255,255,0.05)"/><text x="55" y="65" text-anchor="middle" font-size="30" fill="{d['color']}">⚡</text>"""
        txt_x = 110

    # 3. Badges (Bg Pill)
    badge_group = ""
    if d.get('badges'):
        bx = 0; b_svgs = ""
        for i, b in enumerate(d['badges'][:8]):
            b_svgs += f'<image href="{b}" x="{bx+8}" y="4" width="22" height="22" class="badge-pop" style="animation-delay:{i*0.05}s"/>'
            bx += 28
        badge_group = f"""<g transform="translate(180, 20)"><rect width="{bx+8}" height="30" rx="15" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.1)"/><g>{b_svgs}</g></g>"""

    # 4. Connections (Bg Pill)
    conn_group = ""
    if d.get('connections'):
        cx = 0; c_svgs = ""
        for c in d['connections'][:6]:
            c_svgs += f'<image href="{c}" x="{cx+8}" y="4" width="20" height="20" filter="url(#invert)" opacity="0.8"/>'
            cx += 30
        conn_group = f"""<g transform="translate(620, 70)"><rect x="-10" y="0" width="{cx+10}" height="28" rx="14" fill="rgba(0,0,0,0.5)"/><g>{c_svgs}</g></g>"""

    # 5. Platforms Icons (SVG) - Top Right
    plat_svg = ""
    px = 0
    if d.get('platforms'):
        for p in d['platforms']:
            if p in PLATFORM_PATHS:
                plat_svg += f'<g transform="translate({px},0)"><path d="{PLATFORM_PATHS[p]}" fill="{d["status_color"]}" transform="scale(0.8)" opacity="0.8"/></g>'
                px -= 24
        plat_group = f'<g transform="translate(850, 25)">{plat_svg}</g>'
    else:
        plat_group = ""

    return f"""<svg width="880" height="320" viewBox="0 0 880 320" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css} .title {{ font-family: 'Pacifico', cursive; }} .head {{ font-family: 'Outfit', sans-serif; font-weight: 800; text-transform:uppercase; }} .sub {{ font-family: 'Poppins', sans-serif; opacity: 0.9; }} .mono {{ font-family: 'JetBrains Mono', monospace; opacity: 0.6; }}</style>
        <clipPath id="cp"><rect width="880" height="320" rx="{radius}"/></clipPath><clipPath id="avc"><circle cx="75" cy="75" r="75"/></clipPath><clipPath id="dockClip"><rect width="840" height="110" rx="20"/></clipPath>
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="60"/></filter><filter id="blur"><feGaussianBlur stdDeviation="20"/></filter><filter id="invert"><feColorMatrix type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0"/></filter>
        <linearGradient id="vig" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="rgba(0,0,0,0.3)"/><stop offset="1" stop-color="#000" stop-opacity="0.95"/></linearGradient>
        <linearGradient id="shine" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="white" stop-opacity="0.04"/><stop offset="1" stop-color="white" stop-opacity="0"/></linearGradient>
      </defs>
      <g clip-path="url(#cp)">{bg_svg}<rect x="-400" width="200" height="320" fill="white" opacity="0.03" transform="skewX(-20)" class="shiny"/><rect width="876" height="316" x="2" y="2" rx="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="2"/></g>
      <g transform="translate(40, 40)"><circle cx="75" cy="75" r="79" fill="#18181c"/><circle cx="75" cy="75" r="76" fill="none" stroke="{d['color']}" stroke-width="4" stroke-dasharray="16 10" class="pulsing"/><g clip-path="url(#avc)"><image href="{d['avatar']}" width="150" height="150" /></g><circle cx="125" cy="125" r="18" fill="#121212"/><circle cx="125" cy="125" r="13" fill="{d['status_color']}" class="status-pulse"/>
      <g transform="translate(180, 20)">{badge_group}<text x="0" y="85" class="title" font-size="60" fill="white" style="text-shadow:0 4px 8px rgba(0,0,0,0.5)">{d['name']}</text><text x="10" y="110" class="mono" font-size="12" fill="#AAA">ID :: {d['sub_id']}</text><foreignObject x="5" y="120" width="600" height="60"><div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'Poppins';font-size:16px;color:#ddd;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;opacity:0.85;">{d['bio']}</div></foreignObject></g></g>
      <!-- Platforms Rendered Top Right -->
      {plat_group}
      <g transform="translate(20, 195)" class="slide-in">{act_viz}<g transform="translate({txt_x}, 28)"><text x="0" y="0" class="mono" font-size="11" fill="{d['color']}" letter-spacing="2" font-weight="bold">{d['app_name']}</text><text x="0" y="34" class="head" font-size="28" fill="white">{d['title'][:35]}</text><text x="0" y="58" class="sub" font-size="16" fill="#DDD">{d['detail'][:60]}</text>{conn_group}</g></g>
    </svg>"""

# ===========================
#      HTML RENDERER
# ===========================

def render_html_page(d):
    """Hybrid HTML: Adds Platforms Section and proper links."""
    
    conn_html = ""
    for c in d.get('raw_connections', []):
        ctype, cid = c['type'], c['name']
        url = CONN_URLS.get(ctype, "#").format(cid)
        conn_html += f'<a href="{url}" target="_blank" class="conn-icon"><img src="{c.get("icon_b64", "")}" style="filter:invert(1)"></a>'

    # Platform Icons
    plat_html = ""
    for p in d.get('platforms', []):
        if p in PLATFORM_PATHS:
            plat_html += f'<svg viewBox="0 0 24 24" width="20" height="20" fill="{d["status_color"]}"><path d="{PLATFORM_PATHS[p]}"/></svg>'

    bg_style = f"background-image: url('{d['banner_image']}');"
    
    return render_template_string(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8"><title>{d['name']} | Status</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono:wght@400;700&family=Outfit:wght@400;700;900&family=Pacifico&display=swap" rel="stylesheet">
        <style>
            :root {{ --acc: {d['color']}; --stat: {d['status_color']}; }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ background: #050508; font-family: 'Outfit'; color: white; display: flex; align-items: center; justify-content: center; height: 100vh; }}
            .ambient-bg {{ position: fixed; inset: -50%; {bg_style} background-size: cover; filter: blur(80px) opacity(0.3); z-index: -1; animation: drift 60s infinite linear; }}
            @keyframes drift {{ 0%{{transform:rotate(0deg) scale(1)}} 50%{{transform:rotate(10deg) scale(1.1)}} 100%{{transform:rotate(0deg) scale(1)}} }}
            .card {{ width: 880px; height: 320px; background: rgba(10,10,15,0.4); border: 1px solid rgba(255,255,255,0.1); border-radius: 30px; backdrop-filter: blur(50px); box-shadow: 0 30px 90px rgba(0,0,0,0.5); overflow: hidden; position: relative; }}
            
            .header {{ position: absolute; top: 40px; left: 40px; display: flex; }}
            .avatar-area {{ position: relative; margin-right: 30px; }}
            .av-img {{ width: 150px; height: 150px; border-radius: 50%; object-fit: cover; box-shadow: 0 0 0 4px #18181c; }}
            .ring {{ position: absolute; inset: -10px; border: 4px dashed var(--acc); border-radius: 50%; animation: spin 20s linear infinite; opacity: 0.6; }}
            @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
            
            .stat-dot {{ position: absolute; bottom: 5px; right: 5px; width: 35px; height: 35px; background: #121212; border-radius: 50%; display: grid; place-items: center; }}
            .stat-fill {{ width: 20px; height: 20px; background: var(--stat); border-radius: 50%; box-shadow: 0 0 10px var(--stat); animation: pulse 2s infinite; }}
            @keyframes pulse {{ 50% {{ opacity: 0.5; }} }}

            .meta {{ padding-top: 10px; }}
            .badges {{ display: flex; gap: 10px; margin-bottom: 5px; }}
            .badge {{ width: 28px; height: 28px; transition: transform 0.2s; }} .badge:hover {{ transform: scale(1.2); }}
            h1 {{ font-family: 'Pacifico'; font-size: 60px; font-weight: 400; text-shadow: 0 5px 20px rgba(0,0,0,0.5); display: flex; align-items: center; gap: 15px; }}
            .bio {{ font-family: 'Inter'; font-size: 16px; color: #ccc; max-width: 550px; line-height: 1.4; opacity: 0.9; margin-top: 5px; }}
            .id-row {{ font-family: 'JetBrains Mono'; font-size: 11px; color: #777; letter-spacing: 1px; margin-top: 5px; display: flex; align-items: center; gap: 10px; }}
            .platforms {{ display: flex; gap: 8px; margin-left: 10px; opacity: 0.8; }}

            .dock {{ position: absolute; bottom: 20px; left: 20px; width: 840px; height: 110px; background: rgba(20,20,25,0.7); border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; display: flex; align-items: center; padding: 20px; }}
            .dock:before {{ content: ''; position: absolute; top:0; left:0; width: 100%; height: 100%; border-radius: 20px; background: url('{d.get('act_image_url', '')}') center/cover; opacity: 0.3; filter: blur(20px); z-index: 0; }}
            .art-wrap {{ width: 80px; height: 80px; border-radius: 12px; background: rgba(255,255,255,0.05); overflow: hidden; position: relative; z-index: 2; margin-right: 20px; flex-shrink: 0; border: 1px solid rgba(255,255,255,0.1); }}
            .art-wrap img {{ width: 100%; height: 100%; object-fit: cover; }}
            .no-art {{ width: 100%; height: 100%; display: grid; place-items: center; font-size: 30px; }}
            
            .activity {{ z-index: 2; flex: 1; min-width: 0; }}
            .label {{ font-family: 'JetBrains Mono'; font-size: 10px; color: var(--acc); letter-spacing: 2px; font-weight: 800; }}
            .track {{ font-size: 26px; font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin: 2px 0; }}
            .details {{ color: #aaa; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

            .conns {{ z-index: 2; display: flex; gap: 15px; margin-left: 20px; }}
            .conn-icon img {{ width: 24px; height: 24px; opacity: 0.6; transition: 0.2s; }}
            .conn-icon:hover img {{ opacity: 1; transform: translateY(-3px); }}
        </style>
    </head>
    <body>
        <div class="ambient-bg"></div>
        <div class="card">
            <div class="header">
                <div class="avatar-area">
                    <div class="ring"></div>
                    <img src="{d['avatar']}" class="av-img">
                    <div class="stat-dot"><div class="stat-fill"></div></div>
                </div>
                <div class="meta">
                    <div class="badges">{''.join([f'<img src="{b}" class="badge">' for b in d['badges']])}</div>
                    <h1>{d['name']}</h1>
                    <div class="id-row">
                        ID: {d['sub_id']}
                        <div class="platforms">{plat_html}</div>
                    </div>
                    <div class="bio">{d['bio']}</div>
                </div>
            </div>

            <div class="dock">
                <div class="art-wrap">
                    {f'<img src="{d["act_image_url"]}">' if d.get('act_image_url') else f'<div class="no-art" style="color:{d["color"]}">⚡</div>'}
                </div>
                <div class="activity">
                    <div class="label">{d['app_name']}</div>
                    <div class="track">{d['title']}</div>
                    <div class="details">{d['detail']}</div>
                </div>
                <div class="conns">
                    {conn_html}
                </div>
            </div>
        </div>
    </body>
    </html>""")

# ===========================
#        CONTROLLER
# ===========================

@app.route('/superbadge/<key>')
def handler(key):
    args = request.args
    mode = args.get('mode', 'svg')
    
    # 1. FETCH
    type_mode = 'user' if (key.isdigit() and len(str(key)) > 15) else 'discord'
    data = fetch_data(key, type_mode, args)
    
    if not data:
         return Response('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="200"><rect width="100%" height="100%" fill="#111"/><text x="20" y="100" fill="red" font-family="sans-serif">ERR: LOAD FAIL</text></svg>', mimetype="image/svg+xml")

    # 2. HTML RENDER
    if mode == 'html':
        return render_html_page(data)

    # 3. SVG RENDER
    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '111111').replace('#','')
    radius = args.get('borderRadius', '30').replace('px', '') 

    css = get_css(bg_an, fg_an)
    
    # User Profile (Mega) or Discord Server (Standard)
    svg = render_svg(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

@app.route('/')
def home(): return "TITAN V46 ONLINE (HTML+SVG)"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
