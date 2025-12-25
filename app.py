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
HEADERS = {'User-Agent': 'HyperBadge/Titan-v54-Platforms'}
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

CACHE = {} 
ICON_CACHE = {}

# Mappings
CONN_MAP = {
    "github": "github", "steam": "steam", "twitch": "twitch", "spotify": "spotify",
    "twitter": "x", "reddit": "reddit", "youtube": "youtube", "xbox": "xbox", 
    "playstation": "playstation", "tiktok": "tiktok", "instagram": "instagram"
}
CONN_URLS = {
    "github": "https://github.com/{}", "twitter": "https://x.com/{}",
    "reddit": "https://reddit.com/user/{}", "steam": "https://steamcommunity.com/profiles/{}",
    "twitch": "https://twitch.tv/{}", "youtube": "https://youtube.com/@{}",
    "spotify": "https://open.spotify.com/user/{}", "tiktok": "https://tiktok.com/@{}"
}
SIMPLE_ICONS_BASE = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/"

# Platform SVG Paths (Material Symbols)
PLAT_ICONS = {
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
    text = re.sub(r'<a?:.+?:\d+>', '', text)
    return html.escape(text, quote=True)

def get_base64(url, is_svg=False):
    """Caching Image Fetcher"""
    if not url: return EMPTY
    if url in ICON_CACHE: return ICON_CACHE[url]
    try:
        if url.startswith("mp:"): url = f"https://media.discordapp.net/{url[3:]}"
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            mime = "image/svg+xml" if (is_svg or url.endswith(".svg")) else "image/png"
            val = f"data:{mime};base64,{base64.b64encode(r.content).decode('utf-8')}"
            if len(ICON_CACHE) > 200: ICON_CACHE.clear()
            ICON_CACHE[url] = val
            return val
    except: pass
    return EMPTY

def get_css(bg_anim, fg_anim):
    css = "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&amp;family=Outfit:wght@400;500;800;900&amp;family=Pacifico&amp;family=Poppins:wght@400;500;600&amp;display=swap');"
    keyframes = """
    @keyframes d { from{transform:scale(1.02) rotate(0deg)} to{transform:scale(1.05) rotate(0.5deg)} }
    @keyframes slide { 0%{transform:translateX(-15px);opacity:0} 100%{transform:translateX(0);opacity:1} }
    @keyframes pop { 0%{transform:scale(0); opacity:0} 100%{transform:scale(1); opacity:1} }
    @keyframes glint { 0% {transform:translateX(-200%)} 100% {transform:translateX(200%)} }
    @keyframes breathe { 0%{r:12px} 50%{r:16px} 100%{r:12px} }
    @keyframes eq { 0%{height:4px} 50%{height:14px} 100%{height:4px} }
    """
    
    classes = ""
    if str(bg_anim).lower() != 'false': classes += ".bg-drift{animation:d 40s linear infinite alternate} .shiny{animation:glint 6s infinite cubic-bezier(0.4, 0, 0.2, 1)}"
    if str(fg_anim).lower() != 'false': classes += ".slide-in{animation:slide 0.8s ease-out} .badge-pop{animation:pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) backwards} .status-breathe{animation:breathe 3s infinite} .eq-bar{animation:eq 0.8s ease-in-out infinite}"
    return css + keyframes + classes

# ===========================
#      DATA LOGIC
# ===========================

def fetch_data(key, type_mode, args, for_html=False):
    try:
        force_name = args.get('name')

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

        else:
            # Init Data
            dcdn_user, badges_list, conn_list, banner_url = {}, [], [], None
            
            # 1. Profile Assets (DCDN)
            try:
                r_prof = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=3)
                if r_prof.status_code == 200:
                    prof_json = r_prof.json()
                    dcdn_user = prof_json.get('user', {})
                    banner_url = dcdn_user.get('banner')
                    for b in prof_json.get('badges', []):
                        u = f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png"
                        badges_list.append(u if for_html else get_base64(u))
                    
                    seen = set()
                    for c in prof_json.get('connected_accounts', []):
                        if c['type'] in CONN_MAP and c['type'] not in seen:
                            c_url = f"{SIMPLE_ICONS_BASE}{CONN_MAP[c['type']]}.svg"
                            val = c_url if for_html else get_base64(c_url, is_svg=True)
                            
                            link = "#"
                            if c['type'] in CONN_URLS: 
                                ident = c['id'] if c['type']=='steam' else c['name']
                                link = CONN_URLS[c['type']].format(ident)
                            
                            conn_list.append({'type': c['type'], 'src': val, 'link': link})
                            seen.add(c['type'])
            except: pass

            # 2. Lanyard Status
            r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            if r_lan.status_code != 200: return None
            lan_json = r_lan.json()
            if not lan_json.get('success'): return None
            d = lan_json['data']
            u = d['discord_user']
            status = d['discord_status']
            
            # --- Platform Check ---
            platforms = []
            if d.get('active_on_discord_desktop'): platforms.append("desktop")
            if d.get('active_on_discord_mobile'): platforms.append("mobile")
            if d.get('active_on_discord_web'): platforms.append("web")

            # --- Activity Logic ---
            cols = {"online": "#00FF99", "idle": "#FFBB00", "dnd": "#ed4245", "offline": "#80848e", "spotify": "#1DB954"}
            main_act = None

            if d.get('spotify'):
                s = d['spotify']
                main_act = {
                    "header": "LISTENING TO SPOTIFY", "title": s['song'], "detail": s['artist'],
                    "image": s.get('album_art_url'), "color": cols['spotify'],
                    "start": s['timestamps']['start'], "end": s['timestamps']['end'], "is_music": True
                }
            elif d.get('activities'):
                for act in d['activities']:
                    if act['type'] == 4: continue
                    img_url = None
                    if 'assets' in act and 'large_image' in act['assets']:
                        aid, imid = act['application_id'], act['assets']['large_image']
                        if imid.startswith("mp:"): img_url = f"https://media.discordapp.net/{imid[3:]}"
                        else: img_url = f"https://cdn.discordapp.com/app-assets/{aid}/{imid}.png"
                    
                    header = f"PLAYING {act['name'].upper()}" if act['type']==0 else "ACTIVITY"
                    main_act = {
                        "header": header, "title": act.get('details', act['name']),
                        "detail": act.get('state', ''), "image": img_url,
                        "color": cols.get(status, "#5865F2"),
                        "start": act.get('timestamps', {}).get('start', 0), "end": act.get('timestamps', {}).get('end', 0),
                        "is_music": False
                    }
                    break
            
            if not main_act:
                msg = args.get('idleMessage', 'Chilling')
                for act in d.get('activities', []):
                    if act['type'] == 4: msg = act.get('state', msg); break
                
                main_act = {
                    "header": "CURRENT STATUS", "title": msg, "detail": "Online" if status!='offline' else "Offline",
                    "image": None, "color": cols.get(status, "#555"), "is_music": False, "start":0, "end":0
                }

            # Naming & Banner
            final_name = force_name if force_name else (dcdn_user.get('global_name') or u['global_name'] or u['username'])
            u_avatar = f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"
            final_bg = banner_url if banner_url else u_avatar
            bio_raw = dcdn_user.get('bio', 'No Bio Set.')
            
            status_c = cols.get(status, "#80848e")

            # --- RESPONSE FORMATTING ---
            if for_html:
                return {
                    "name": final_name, "uid": u['id'], "avatar": u_avatar, "banner": final_bg,
                    "status_color": status_c, "bio": bio_raw,
                    "badges": badges_list, "connections": conn_list, 
                    "platforms": platforms, "activity": main_act
                }
            else:
                return {
                    "type": "user",
                    "name": sanitize_xml(final_name),
                    "title": sanitize_xml(main_act['title']),
                    "detail": sanitize_xml(main_act['detail']),
                    "app_name": sanitize_xml(main_act['header']),
                    "color": main_act['color'],
                    "status_color": status_c,
                    "avatar": get_base64(u_avatar),
                    "banner_image": get_base64(final_bg),
                    "act_image": get_base64(main_act['image']) if main_act['image'] else None,
                    "bio": sanitize_xml(bio_raw),
                    "badges": badges_list, 
                    "connections": [c['src'] for c in conn_list], 
                    "platforms": platforms, 
                    "sub_id": u['id'], 
                    "is_music": main_act['is_music']
                }

    except Exception as e: return None

# ===========================
#      RENDER ENGINES (SVG)
# ===========================

def render_mega_svg(d, css, radius, bg_col):
    """SVG Engine (Standard GitHub Image)"""
    bg_svg = f"""<rect width="100%" height="100%" fill="#{bg_col}" /><image href="{d['banner_image']}" width="100%" height="150%" y="-15%" preserveAspectRatio="xMidYMid slice" opacity="0.4" filter="url(#heavyBlur)" class="bg-drift"/><rect width="100%" height="100%" fill="url(#vig)"/>"""
    
    if d['act_image']:
        act_viz = f"""<image href="{d['act_image']}" x="25" y="195" width="80" height="80" rx="14" /><rect x="25" y="195" width="80" height="80" rx="14" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>"""
        txt_pos = 135
        eq_viz = f'<g transform="translate(130, -5)"><rect class="eq-bar" x="0" y="4" width="3" height="8" rx="1" fill="#0f0"/><rect class="eq-bar" x="5" y="1" width="3" height="14" rx="1" fill="#0f0" style="animation-delay:0.1s"/><rect class="eq-bar" x="10" y="5" width="3" height="6" rx="1" fill="#0f0" style="animation-delay:0.2s"/></g>' if d['is_music'] else ""
    else:
        act_viz = f"""<rect x="25" y="195" width="80" height="80" rx="14" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.1)"/><text x="65" y="245" text-anchor="middle" font-family="Outfit" font-size="28" fill="{d['color']}">⚡</text>"""
        txt_pos = 135
        eq_viz = ""

    badge_group = "".join([f'<image href="{b}" x="{i*28}" y="0" width="22" height="22" class="badge-pop" style="animation-delay:{i*0.05}s"/>' for i,b in enumerate(d.get('badges', []))])
    conn_group = "".join([f'<image href="{c}" x="{i*34}" y="0" width="22" height="22" filter="url(#invert)" opacity="0.7"/>' for i,c in enumerate(d.get('connections', [])[:6])])
    
    # 5. Platforms (SVG Implementation) - TOP RIGHT
    plat_svg = ""
    px = 840
    for p in d.get('platforms', []):
        if p in PLAT_ICONS:
            # We scale the paths
            plat_svg += f'<g transform="translate({px},0) scale(1)"><path d="{PLAT_ICONS[p]}" fill="{d["status_color"]}" filter="drop-shadow(0 0 5px black)" /></g>'
            px -= 30
    plat_group = f'<g transform="translate(0, 30)">{plat_svg}</g>'
    
    t_tit = d['title'][:32] + (".." if len(d['title'])>32 else "")

    return f"""<svg width="880" height="320" viewBox="0 0 880 320" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <defs><style>{css} .title{{font-family:'Pacifico',cursive;fill:white;text-shadow:0 4px 10px rgba(0,0,0,0.5);}} .head{{font-family:'Outfit',sans-serif;font-weight:800;text-transform:uppercase;}} .sub{{font-family:'Poppins',sans-serif;opacity:0.9;}} .mono{{font-family:'JetBrains Mono',monospace;opacity:0.6;}}</style>
        <clipPath id="cp"><rect width="880" height="320" rx="{radius}"/></clipPath><clipPath id="avc"><circle cx="75" cy="75" r="75"/></clipPath>
        <filter id="heavyBlur"><feGaussianBlur stdDeviation="60"/></filter><filter id="ds"><feDropShadow dx="0" dy="4" stdDeviation="4" flood-opacity="0.6"/></filter><filter id="invert"><feColorMatrix type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0"/></filter>
        <linearGradient id="vig" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="rgba(0,0,0,0.3)"/><stop offset="1" stop-color="#000" stop-opacity="0.95"/></linearGradient>
        <linearGradient id="shine" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="white" stop-opacity="0.04"/><stop offset="1" stop-color="white" stop-opacity="0"/></linearGradient>
      </defs>
      <g clip-path="url(#cp)">{bg_svg}<rect x="-400" width="200" height="320" fill="white" opacity="0.03" transform="skewX(-20)" class="shiny"/><rect width="876" height="316" x="2" y="2" rx="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="2"/></g>
      <g transform="translate(40,40)">
         <circle cx="75" cy="75" r="79" fill="#18181c"/><circle cx="75" cy="75" r="76" fill="none" stroke="{d['color']}" stroke-width="4" stroke-dasharray="16 10" class="pulsing"/><g clip-path="url(#avc)"><image href="{d['avatar']}" width="150" height="150" /></g><circle cx="125" cy="125" r="18" fill="#121212"/><circle cx="125" cy="125" r="13" fill="{d['status_color']}" class="status-breathe"/>
         <g transform="translate(180, 20)"><g transform="translate(0, -15)">{badge_group}</g><text x="0" y="55" class="title" font-size="60" filter="url(#ds)">{d['name']}</text><text x="10" y="80" class="mono" font-size="12">ID :: {d['sub_id']}</text><foreignObject x="5" y="90" width="550" height="60"><div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'Poppins';font-size:16px;color:#ddd;line-height:1.4;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;opacity:0.9;">{d['bio']}</div></foreignObject></g></g>{plat_group}
      <g transform="translate(20, 195)" class="slide-in"><rect width="840" height="110" rx="20" fill="rgba(30,30,35,0.6)" stroke="{d['color']}" stroke-opacity="0.3" stroke-width="2"/>{act_viz}<g transform="translate({txt_pos}, 28)"><g><text x="0" y="0" class="mono" font-size="11" fill="{d['color']}" letter-spacing="1.5" font-weight="bold">{d['app_name']}</text>{eq_viz}</g><text x="0" y="32" class="head" font-size="28" fill="white" filter="url(#ds)">{t_tit}</text><text x="0" y="56" class="sub" font-size="16" fill="#BBB">{d['detail'][:60]}</text></g><g transform="translate(630, 45)">{conn_group}</g></g>
    </svg>"""

# ===========================
#      HTML RENDERER (LIVE)
# ===========================

def render_live_html(d):
    """HTML Mode with Live Updates & Interactive Elements"""
    return f"""
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>{d['name']} - Live</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&family=Pacifico&family=JetBrains+Mono:wght@400;500&family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root {{ --acc: {d['activity']['color']}; --stat: {d['status_color']}; }}
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ background:#050508; color:white; font-family:'Outfit'; display:flex; justify-content:center; align-items:center; height:100vh; overflow:hidden; }}
        
        /* 1. ANIMATED BACKGROUND */
        .ambient {{ position:fixed; inset:-20%; background:url('{d['banner']}') center/cover; filter:blur(100px) opacity(0.3); z-index:-1; animation: d 60s infinite alternate; }}
        @keyframes d {{ from {{transform:scale(1)}} to {{transform:scale(1.2)}} }}

        /* 2. CARD */
        .card {{ position:relative; width:880px; height:320px; background:rgba(15,15,20,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:35px; backdrop-filter:blur(40px); box-shadow:0 30px 100px black; overflow:hidden; }}
        .header {{ position:absolute; top:40px; left:40px; display:flex; gap:30px; z-index:2; }}

        /* 3. AVATAR & STATUS */
        .av-wrap {{ position:relative; width:150px; height:150px; flex-shrink:0; }}
        .av-img {{ width:100%; height:100%; border-radius:50%; object-fit:cover; border:6px solid rgba(255,255,255,0.08); }}
        .ring {{ position:absolute; inset:-12px; border-radius:50%; border:5px dashed var(--acc); animation: spin 25s linear infinite; opacity:0.6; }}
        @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
        
        .stat-dot {{ position:absolute; bottom:12px; right:12px; width:40px; height:40px; background:#121212; border-radius:50%; display:grid; place-items:center; }}
        .fill {{ width:24px; height:24px; border-radius:50%; background:var(--stat); box-shadow:0 0 15px var(--stat); animation: p 2s infinite; }} @keyframes p{{50%{{opacity:0.6}}}}

        /* 4. PLATFORMS (Top Right) */
        .plat-box {{ position:absolute; top:35px; right:35px; display:flex; gap:12px; opacity:0.9; z-index:5; }}
        .p-icon svg {{ width:28px; fill:var(--stat); filter:drop-shadow(0 0 8px rgba(0,0,0,0.6)); transition:fill 0.5s; }}

        /* 5. TEXT */
        .meta {{ padding-top:5px; }} .badges {{ display:flex; gap:10px; margin-bottom:5px; height:30px; }} .badge {{ height:28px; filter:drop-shadow(0 2px 4px black); }}
        h1 {{ font-family:'Pacifico'; font-size:62px; line-height:1; margin:0; text-shadow:0 5px 15px rgba(0,0,0,0.5); }}
        .bio {{ margin-top:10px; font-size:17px; color:#ddd; opacity:0.9; line-height:1.4; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}

        /* 6. ACTIVITY DOCK */
        .dock {{ position:absolute; bottom:25px; left:25px; width:830px; height:110px; background:rgba(30,30,35,0.7); border:1px solid rgba(255,255,255,0.1); border-radius:24px; display:flex; align-items:center; padding:20px; transition:border-color 0.4s; border-color:var(--acc); z-index:5; }}
        
        .art {{ width:85px; height:85px; border-radius:14px; margin-right:25px; box-shadow:0 5px 25px black; object-fit:cover; background:#222; flex-shrink:0; }}
        
        .info {{ flex:1; overflow:hidden; min-width:0; }}
        .lbl {{ font-family:'JetBrains Mono'; font-size:11px; color:var(--acc); font-weight:800; letter-spacing:2px; margin-bottom:2px; text-transform:uppercase; }}
        .tit {{ font-size:26px; font-weight:800; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
        .det {{ color:#aaa; font-size:15px; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}

        .conns {{ display:flex; gap:15px; margin-right:15px; }}
        .ci {{ width:26px; filter:invert(1); opacity:0.7; transition:0.2s; }} .ci:hover{{ transform:translateY(-3px); opacity:1; }}

        .bar-bg {{ position:absolute; bottom:0; left:0; width:100%; height:5px; background:rgba(255,255,255,0.05); overflow:hidden; border-radius:0 0 24px 24px; }}
        .bar-fg {{ height:100%; width:0%; background:var(--acc); transition:width 0.2s linear; box-shadow:0 0 10px var(--acc); }}
    </style>
    </head>
    <body>
        <div class="ambient" id="bg"></div>
        <div class="card">
            <div class="plat-box" id="pbox"></div>
            
            <div class="header">
                <div class="av-wrap">
                    <div class="ring"></div>
                    <img id="av" class="av-img" src="{d['avatar']}">
                    <div class="stat-dot"><div class="fill"></div></div>
                </div>
                <div class="meta">
                    <div class="badges" id="bb"></div>
                    <h1 id="nm">{d['name']}</h1>
                    <div class="bio" id="bio">{d['bio']}</div>
                </div>
            </div>

            <div class="dock" id="dock">
                <img id="art" class="art">
                <div class="info">
                    <div class="lbl" id="lbl"></div>
                    <div class="tit" id="tit"></div>
                    <div class="det" id="det"></div>
                </div>
                <div class="conns" id="cc"></div>
                <div class="bar-bg"><div class="bar-fg" id="pg"></div></div>
            </div>
        </div>
        
        <script>
            const UID = "{d['uid']}";
            // Inlined Platform Icons for JS access
            const ICONS = {{
                desktop: '<svg viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v9c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zm0 2v9h16V6H4zm8 14c-.55 0-1-.45-1-1v-1h2v1c0 .55-.45 1-1 1z" fill="currentColor"/></svg>',
                mobile: '<svg viewBox="0 0 24 24"><path d="M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z" fill="currentColor"/></svg>',
                web: '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" fill="currentColor"/></svg>'
            }};

            async function loop() {{
                try {{
                    let r = await fetch(`/api/data/${{UID}}` + window.location.search);
                    let d = await r.json(); if(!d) return;

                    // Color Updates
                    document.documentElement.style.setProperty('--acc', d.activity.color);
                    document.documentElement.style.setProperty('--stat', d.status_color);
                    document.getElementById('dock').style.borderColor = d.activity.color;

                    // Content
                    document.getElementById('bg').style.backgroundImage = `url(${{d.banner || d.avatar}})`;
                    document.getElementById('av').src = d.avatar;
                    document.getElementById('nm').textContent = d.name;
                    document.getElementById('bio').textContent = d.bio;
                    
                    document.getElementById('bb').innerHTML = d.badges.map(u => `<img src="${{u}}" class="badge">`).join('');
                    
                    // Platform Logic
                    let phtml = '';
                    d.platforms.forEach(k => {{ if(ICONS[k]) phtml += `<div class="p-icon">${{ICONS[k]}}</div>`; }});
                    document.getElementById('pbox').innerHTML = phtml;

                    const a = d.activity;
                    document.getElementById('lbl').textContent = a.header;
                    document.getElementById('tit').textContent = a.title;
                    document.getElementById('det').textContent = a.detail;
                    document.getElementById('art').src = a.image || 'https://cdn.discordapp.com/embed/avatars/0.png';
                    
                    if(a.is_music && a.end) {{
                        let p = ((Date.now()-a.start)/(a.end-a.start))*100;
                        document.getElementById('pg').style.width = Math.min(p,100) + '%';
                    }} else {{ document.getElementById('pg').style.width = "0%"; }}

                    document.getElementById('cc').innerHTML = d.connections.map(c => 
                        `<a href="${{c.link}}" target="_blank"><img src="${{c.src}}" class="ci"></a>`).join('');

                }} catch(e){{}}
            }}
            setInterval(loop, 1000); loop();
        </script>
    </body>
    </html>
    """

# ===========================
#      CONTROLLERS
# ===========================
@app.route('/api/data/<key>')
def api(key): return jsonify(fetch_data(key, 'user', request.args, for_html=True))

@app.route('/superbadge/<key>')
def handler(key):
    args = request.args
    # 1. HTML MODE
    if args.get('mode') == 'html':
        # Need one valid data pull to hydrate template initially
        init_data = fetch_data(key, 'user', args, for_html=True)
        if init_data: return render_live_html(init_data)
        return "USER_NOT_FOUND"

    # 2. SVG MODE
    mode = 'user' if (key.isdigit() and len(str(key))>15) else 'discord'
    data = fetch_data(key, mode, args, for_html=False)
    if not data: return Response('<svg><text>Error</text></svg>', mimetype="image/svg+xml")

    # Configs
    bg_an = args.get('bgAnimations', 'true')
    fg_an = args.get('fgAnimations', 'true')
    bg_col = args.get('bg', '111111').replace('#','')
    radius = args.get('borderRadius', '30').replace('px', '')
    css = get_css(bg_an, fg_an)
    
    if data['type'] == 'discord':
         svg = f'<svg width="400" height="100" xmlns="http://www.w3.org/2000/svg"><defs><style>{css}</style></defs><rect width="100%" height="100%" rx="{radius}" fill="#{bg_col}"/><image href="{data["avatar"]}" width="60" height="60" x="20" y="20"/><text x="100" y="55" fill="white" font-family="sans-serif" font-size="20">{data["name"]}</text><text x="100" y="70" font-family="monospace" fill="#5865F2">{data["title"]}</text></svg>'
    else:
         svg = render_mega_svg(data, css, radius, bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache, max-age=0"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
