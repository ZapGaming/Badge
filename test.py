import base64
import requests
import os
import html
import re
from flask import Flask, Response, request, jsonify

app = Flask(__name__)

# ===========================
#        CONFIGURATION
# ===========================
# Cache Settings to respect rate limits
CACHE = {}
ICON_CACHE = {} 
HEADERS = {'User-Agent': 'Titan-v56-PrecisionLayout'}

# Fallback 1x1 Pixel
EMPTY = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# Links & Icons Maps
CONN_URLS = {
    "github": "https://github.com/{}", "twitter": "https://x.com/{}", "x": "https://x.com/{}",
    "reddit": "https://reddit.com/user/{}", "steam": "https://steamcommunity.com/profiles/{}",
    "twitch": "https://twitch.tv/{}", "youtube": "https://youtube.com/@{}",
    "spotify": "https://open.spotify.com/user/{}", "tiktok": "https://tiktok.com/@{}"
}
SIMPLE_ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/"
CONN_MAP = {
    "github": "github", "steam": "steam", "twitch": "twitch", "spotify": "spotify",
    "twitter": "x", "x": "x", "reddit": "reddit", "youtube": "youtube", "xbox": "xbox", 
    "playstation": "playstation", "tiktok": "tiktok", "instagram": "instagram"
}

# SVG Paths for Platforms
PLAT_SVG = {
    "mobile": "M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z",
    "desktop": "M21 2H3c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h7v2H8v2h8v-2h-2v-2h7c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H3V4h18v12z",
    "web": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"
}

# ===========================
#      HELPERS
# ===========================

def sanitize_xml(text):
    if not text: return ""
    text = str(text).replace('\n', ' ')
    # Clean Invisible/Control Chars
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    # Strip Discord custom emoji <a:id>
    text = re.sub(r'<a?:.+?:\d+>', '', text)
    return html.escape(text, quote=True)

def get_base64(url, is_svg=False):
    """Caching image downloader"""
    if not url: return EMPTY
    if url in ICON_CACHE: return ICON_CACHE[url]
    
    try:
        # Resolve Media Proxy
        if url.startswith("mp:"): url = f"https://media.discordapp.net/{url[3:]}"
        
        r = requests.get(url, headers=HEADERS, timeout=4)
        if r.status_code == 200:
            mime = "image/svg+xml" if (is_svg or url.endswith(".svg")) else "image/png"
            b64 = f"data:{mime};base64,{base64.b64encode(r.content).decode('utf-8')}"
            
            # Simple LRU-ish limits
            if len(ICON_CACHE) > 250: ICON_CACHE.clear()
            ICON_CACHE[url] = b64
            return b64
    except: pass
    return EMPTY

def get_common_css():
    """Shared CSS styles for font consistency"""
    return "@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800&family=Outfit:wght@400;500;800;900&family=Pacifico&family=Poppins:wght@400;500;600&display=swap');"

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
            
            name = sanitize_xml(force_name or g['name'])
            count = f"{d.get('approximate_member_count', 0):,}"
            
            return {
                "type": "discord", "name": name, "l1": count, "color": "#5865F2", 
                "avatar": get_base64(f"https://cdn.discordapp.com/icons/{g['id']}/{g['icon']}.png") if g.get('icon') else EMPTY
            }

        # 2. USER MODE
        else:
            dcdn_user, badges, connections = {}, [], []
            
            # A. Fetch DCDN (Static Data)
            try:
                r_p = requests.get(f"https://dcdn.dstn.to/profile/{key}", headers=HEADERS, timeout=3)
                if r_p.status_code == 200:
                    prof = r_p.json()
                    dcdn_user = prof.get('user', {})
                    # Badges
                    for b in prof.get('badges', []):
                        icon = f"https://cdn.discordapp.com/badge-icons/{b['icon']}.png"
                        badges.append(icon if for_html else get_base64(icon))
                    # Connections
                    seen = set()
                    for c in prof.get('connected_accounts', []):
                        if c['type'] in CONN_MAP and c['type'] not in seen:
                            c_url = f"{SIMPLE_ICONS_BASE}{CONN_MAP[c['type']]}.svg"
                            val = c_url if for_html else get_base64(c_url, is_svg=True)
                            lnk = "#"
                            if c['type'] in CONN_URLS: 
                                lnk = CONN_URLS[c['type']].format(c['id'] if c['type']=='steam' else c['name'])
                            connections.append({'type': c['type'], 'src': val, 'link': lnk})
                            seen.add(c['type'])
            except: pass

            # B. Fetch Lanyard (Live)
            r_lan = requests.get(f"https://api.lanyard.rest/v1/users/{key}", headers=HEADERS, timeout=4)
            lan = r_lan.json()
            if not lan.get('success'): return None
            
            d = lan['data']; u = d['discord_user']; status = d['discord_status']
            
            # --- Platform ---
            plats = []
            if d.get('active_on_discord_desktop'): plats.append("desktop")
            if d.get('active_on_discord_mobile'): plats.append("mobile")
            if d.get('active_on_discord_web'): plats.append("web")

            # --- Activity & Colors ---
            cols = {"online":"#00FF99", "idle":"#FFBB00", "dnd":"#ed4245", "offline":"#80848e", "spotify":"#1DB954"}
            
            main_act = None
            is_music = False
            
            # 1. Spotify
            if d.get('spotify'):
                s = d['spotify']
                main_act = {
                    "h": "LISTENING TO SPOTIFY", "t": s['song'], "d": s['artist'], "img": s.get('album_art_url'),
                    "c": cols['spotify'], "start": s['timestamps']['start'], "end": s['timestamps']['end']
                }
                is_music = True
            
            # 2. Rich Presence
            elif d.get('activities'):
                for act in d['activities']:
                    if act['type'] == 4: continue
                    img_url = None
                    if 'assets' in act and 'large_image' in act['assets']:
                        if act['assets']['large_image'].startswith("mp:"): img_url = f"https://media.discordapp.net/{act['assets']['large_image'][3:]}"
                        else: img_url = f"https://cdn.discordapp.com/app-assets/{act['application_id']}/{act['assets']['large_image']}.png"
                    
                    head = "PLAYING" if act['type'] == 0 else "WATCHING"
                    main_act = {
                        "h": f"{head} {act['name'].upper()}", "t": act.get('details', act['name']),
                        "d": act.get('state', ''), "img": img_url, 
                        "c": cols.get(status, "#5865F2"), "start": act.get('timestamps', {}).get('start', 0), "end": act.get('timestamps', {}).get('end', 0)
                    }
                    break
            
            # 3. Fallback
            if not main_act:
                msg = args.get('idleMessage', 'Chilling')
                for act in d.get('activities', []):
                    if act['type']==4: msg = act.get('state', msg); break
                main_act = {"h": "CURRENTLY", "t": msg, "d": "Online" if status!='offline' else "Offline", "img": None, "c": cols.get(status, "#555"), "start":0, "end":0}

            # --- Formatting ---
            name = force_name if force_name else (dcdn_user.get('global_name') or u['global_name'] or u['username'])
            av_url = f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png"
            bg_url = dcdn_user.get('banner') if dcdn_user.get('banner') else av_url
            bio = dcdn_user.get('bio', 'No Bio Set.')

            if for_html:
                # Return Raw Strings/Objects
                return {
                    "name": name, "uid": u['id'], "avatar": av_url, "banner": bg_url,
                    "status_color": cols.get(status, "#888"), "bio": bio,
                    "badges": badges, "connections": connections,
                    "platforms": plats, 
                    "activity": {
                        "header": main_act['h'], "title": main_act['t'], "detail": main_act['d'],
                        "image": main_act['img'], "color": main_act['c'], 
                        "is_music": is_music, "start": main_act['start'], "end": main_act['end']
                    }
                }
            else:
                # Return Pre-Computed SVG data
                return {
                    "type": "user",
                    "name": sanitize_xml(name),
                    "title": sanitize_xml(main_act['t']),
                    "detail": sanitize_xml(main_act['d']),
                    "app": sanitize_xml(main_act['h']),
                    "color": main_act['c'],
                    "stat_color": cols.get(status, "#888"),
                    "avatar": get_base64(av_url),
                    "banner": get_base64(bg_url),
                    "act_img": get_base64(main_act['img']) if main_act['img'] else None,
                    "bio": sanitize_xml(bio),
                    "badges": badges, # b64 list
                    "connections": [c['src'] for c in connections], 
                    "link_map": [c['link'] for c in connections],
                    "platforms": plats,
                    "uid": u['id'], "music": is_music
                }
    except Exception as e:
        print(f"Data Err: {e}")
        return None


# ===========================
#      SVG RENDERER
# ===========================

def render_svg(d, width=960, height=360, radius=30):
    """
    LAYOUT: 960x360
    Collision Fixed by moving Activity dock to Y=230+
    """
    css = get_css(True, True) + """
    .t{font-family:'Pacifico';fill:white;text-shadow:0 5px 15px rgba(0,0,0,0.5)}
    .h{font-family:'Outfit';font-weight:900;text-transform:uppercase}
    .s{font-family:'Poppins';opacity:0.9}
    .m{font-family:'JetBrains Mono';opacity:0.6}
    .drift{animation:d 40s infinite linear alternate} 
    @keyframes d{from{transform:scale(1)}to{transform:scale(1.2)}}
    """
    
    # 1. Background
    bg_svg = f"""<rect width="100%" height="100%" fill="#111"/><image href="{d['banner']}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" opacity="0.3" filter="url(#bl)" class="drift"/><rect width="100%" height="100%" fill="url(#g)"/>"""

    # 2. Badges Row
    badge_g = "".join([f'<image href="{b}" x="{i*32}" y="0" width="28" height="28" style="filter:drop-shadow(0 2px 5px black)"/>' for i,b in enumerate(d.get('badges', []))])
    
    # 3. Connection Row (Clean White)
    conn_g = "".join([f'<image href="{c}" x="{i*35}" y="0" width="24" height="24" style="filter:invert(1);opacity:0.7"/>' for i,c in enumerate(d.get('connections', [])[:8])])
    
    # 4. Platforms (Top Right)
    plat_g = ""
    px = width - 40
    for p in d.get('platforms', []):
        if p in PLAT_ICONS:
            plat_g += f'<path transform="translate({px}, 40)" d="{PLAT_ICONS[p]}" fill="{d["stat_color"]}" style="filter:drop-shadow(0 0 8px {d["stat_color"]})" />'
            px -= 35

    # 5. Activity Art vs Placeholder
    if d['act_img']:
        aviz = f"""<image href="{d['act_img']}" x="25" y="235" width="85" height="85" rx="14"/><rect x="25" y="235" width="85" height="85" rx="14" fill="none" stroke="white" stroke-opacity="0.1"/>"""
        tx = 135
        # Music Bars SVG
        eq = f'<g transform="translate(180, 0)"><rect x="0" y="4" width="4" height="12" fill="{d["color"]}" rx="1"><animate attributeName="height" values="8;16;6;12;8" dur="1s" repeatCount="indefinite"/></rect><rect x="6" y="0" width="4" height="12" fill="{d["color"]}" rx="1"><animate attributeName="height" values="16;6;12;8;16" dur="0.8s" repeatCount="indefinite"/></rect></g>' if d['music'] else ""
    else:
        aviz = f"""<rect x="25" y="235" width="85" height="85" rx="14" fill="#222"/><text x="67" y="290" text-anchor="middle" font-family="Outfit" font-size="32" fill="{d['color']}">⚡</text>"""
        tx = 135
        eq = ""

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
      <defs><style>{css}</style>
      <clipPath id="cp"><rect width="{width}" height="{height}" rx="{radius}"/></clipPath>
      <clipPath id="ac"><circle cx="80" cy="80" r="80"/></clipPath>
      <filter id="bl"><feGaussianBlur stdDeviation="40"/></filter>
      <linearGradient id="g" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="rgba(0,0,0,0.3)"/><stop offset="1" stop-color="black"/></linearGradient>
      </defs>
      <g clip-path="url(#cp)">{bg_svg}
        <rect width="{width-4}" height="{height-4}" x="2" y="2" rx="{radius}" fill="none" stroke="white" stroke-opacity="0.1" stroke-width="2"/>
      </g>
      
      {plat_g}

      <!-- PROFILE -->
      <g transform="translate(40,40)">
        <circle cx="80" cy="80" r="84" fill="#121212" />
        <circle cx="80" cy="80" r="80" fill="none" stroke="{d['color']}" stroke-width="4" stroke-dasharray="20 15" opacity="0.6"><animateTransform attributeName="transform" type="rotate" from="0 80 80" to="360 80 80" dur="25s" repeatCount="indefinite"/></circle>
        <g clip-path="url(#ac)"><image href="{d['avatar']}" width="160" height="160"/></g>
        
        <circle cx="135" cy="135" r="18" fill="#121212"/>
        <circle cx="135" cy="135" r="14" fill="{d['stat_color']}" />

        <g transform="translate(200, 20)">
           <g>{badge_group}</g>
           <text x="0" y="65" class="t" font-size="70">{d['name']}</text>
           <text x="5" y="90" class="m" font-size="12">UID :: {d['uid']}</text>
           <foreignObject x="5" y="105" width="600" height="60"><div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'Poppins';font-size:16px;color:#ccc;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;">{d['bio']}</div></foreignObject>
        </g>
      </g>

      <!-- DOCK -->
      <g transform="translate(20, 220)">
         <rect width="{width-40}" height="115" rx="20" fill="rgba(30,30,35,0.7)" stroke="{d['color']}" stroke-opacity="0.5"/>
         <g transform="translate(0, -15)">{act_viz}</g>
         <g transform="translate({tx}, 18)">
            <g><text y="10" class="m" font-size="11" fill="{d['color']}" letter-spacing="1.5" font-weight="bold">{d['app']}</text>{eq}</g>
            <text y="42" class="h" font-size="28" fill="white">{d['title'][:32]}</text>
            <text y="68" class="s" font-size="16" fill="#aaa">{d['detail'][:40]}</text>
         </g>
         <g transform="translate({width-260}, 55)">{conn_group}</g>
      </g>
    </svg>"""

# ===========================
#      HTML RENDERER
# ===========================

def render_html_page(d):
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>{d['name']}</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;900&family=Pacifico&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {{ --c: {d['activity']['color']}; --s: {d['status_color']}; }}
        body {{ margin:0; background:#000; font-family:'Outfit'; color:white; display:flex; justify-content:center; align-items:center; height:100vh; }}
        .bg {{ position:fixed; inset:-10%; background:url('{d['banner']}') center/cover; filter:blur(90px) opacity(0.3); z-index:-1; animation: d 60s infinite alternate; }}
        @keyframes d {{ from{{transform:scale(1)}} to{{transform:scale(1.2)}} }}
        .card {{ position:relative; width:960px; height:420px; background:rgba(20,20,25,0.5); border:1px solid rgba(255,255,255,0.1); border-radius:40px; backdrop-filter:blur(50px); box-shadow:0 30px 100px black; overflow:hidden; }}
        
        .av-row {{ position:absolute; top:40px; left:40px; display:flex; }}
        .av-con {{ position:relative; width:180px; height:180px; }}
        .av {{ width:100%; height:100%; border-radius:50%; object-fit:cover; }}
        .ring {{ position:absolute; inset:-15px; border-radius:50%; border:5px dashed var(--c); animation:spin 25s linear infinite; opacity:0.6; }} @keyframes spin {{ to{{transform:rotate(360deg)}} }}
        .dot {{ position:absolute; bottom:10px; right:10px; width:40px; height:40px; background:#121212; border-radius:50%; display:grid; place-items:center; }}
        .fil {{ width:24px; height:24px; background:var(--s); border-radius:50%; box-shadow:0 0 20px var(--s); }}
        
        .info {{ margin-left:40px; display:flex; flex-direction:column; justify-content:center; }}
        .badg {{ display:flex; gap:10px; height:32px; }} .bi {{ height:30px; transition:0.2s; filter:drop-shadow(0 2px 4px black); }} .bi:hover{{transform:translateY(-5px);}}
        h1 {{ font-family:'Pacifico'; font-size:75px; line-height:1; margin:5px 0 0 0; text-shadow:0 5px 20px rgba(0,0,0,0.5); }}
        .bio {{ color:#ccc; max-width:600px; font-size:18px; margin-top:10px; }}
        
        .dock {{ position:absolute; bottom:30px; left:30px; width:900px; height:130px; background:rgba(30,30,35,0.8); border-radius:24px; border:1px solid rgba(255,255,255,0.15); display:flex; align-items:center; padding:25px; transition:border-color 0.4s; border-color:var(--c); }}
        .art {{ width:90px; height:90px; border-radius:15px; margin-right:30px; object-fit:cover; background:#222; flex-shrink:0; }}
        .spin-art {{ border-radius:50%; animation:spin 5s linear infinite; }}
        .ad {{ flex:1; min-width:0; overflow:hidden; }}
        .lbl {{ font-family:'JetBrains Mono'; font-size:12px; color:var(--c); font-weight:800; letter-spacing:2px; }}
        .tit {{ font-size:32px; font-weight:900; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
        .dt {{ font-size:18px; color:#bbb; }}
        
        .icons {{ display:flex; gap:20px; margin-left:20px; }} .ii {{ width:28px; filter:invert(1); opacity:0.6; transition:0.2s; cursor:pointer; }} .ii:hover{{ opacity:1; transform:translateY(-3px); }}
        
        .p-bg {{ position:absolute; bottom:0; left:0; width:100%; height:6px; background:rgba(255,255,255,0.1); border-radius:0 0 24px 24px; }}
        .p-fg {{ height:100%; background:var(--c); width:0%; transition:width 1s linear; }}
        
        .plts {{ position:absolute; top:40px; right:40px; display:flex; gap:12px; }} .psvg svg {{ width:26px; fill:var(--s); filter:drop-shadow(0 0 5px black); }}
    </style></head>
    <body>
        <div class="bg"></div><div class="card">
            <div class="plts" id="pl"></div>
            <div class="av-row">
                <div class="av-con"><div class="ring"></div><img id="av" class="av"><div class="dot"><div class="fil"></div></div></div>
                <div class="info"><div class="badg" id="bl"></div><h1 id="nm">...</h1><div class="bio" id="bio">...</div></div>
            </div>
            <div class="dock">
                <img id="art" class="art"><div class="ad"><div class="lbl" id="lb"></div><div class="tit" id="tr"></div><div class="dt" id="de"></div></div>
                <div class="icons" id="cl"></div><div class="p-bg"><div class="p-fg" id="pb"></div></div>
            </div>
        </div>
        <script>
            const U="{d['uid']}", M={CONN_MAP}, B="{d['bio']}", I={{desktop:'...',mobile:'...',web:'...'}};
            // Need to insert SVG Paths for ICONS constant manually here for brevity or fetch in loop
            const IS={{ desktop: '<svg viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v9c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zm0 2v9h16V6H4zm8 14c-.55 0-1-.45-1-1v-1h2v1c0 .55-.45 1-1 1z" fill="currentColor"/></svg>', mobile:'<svg viewBox="0 0 24 24"><path d="M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z" fill="currentColor"/></svg>', web:'<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" fill="currentColor"/></svg>' }};
            
            async function r(){{
                try {{
                    let f=await fetch('/api/data/'+U+location.search), d=await f.json(); if(!d)return;
                    document.documentElement.style.setProperty('--c', d.activity.color);
                    document.documentElement.style.setProperty('--s', d.status_color);
                    document.querySelector('.bg').style.backgroundImage = `url(${{d.banner||d.avatar}})`;
                    
                    document.getElementById('av').src = d.avatar;
                    document.getElementById('nm').innerText = d.name;
                    document.getElementById('bio').innerText = d.bio;
                    document.getElementById('bl').innerHTML = d.badges.map(s=>`<img src="${{s}}" class="bi">`).join('');
                    document.getElementById('pl').innerHTML = d.platforms.map(k=>`<div class="psvg">${{IS[k]||''}}</div>`).join('');
                    
                    const a=d.activity;
                    document.getElementById('lb').innerText = a.header;
                    document.getElementById('tr').innerText = a.title;
                    document.getElementById('de').innerText = a.detail;
                    document.getElementById('art').src = a.image||'https://cdn.discordapp.com/embed/avatars/0.png';
                    document.getElementById('art').className = a.is_music ? 'art spin-art' : 'art';
                    
                    if(a.is_music&&a.end){{ 
                        let p = ((Date.now()-a.start)/(a.end-a.start))*100;
                        document.getElementById('pb').style.width = Math.min(Math.max(p,0),100)+'%';
                    }} else {{ document.getElementById('pb').style.width='0%'; }}

                    document.getElementById('cl').innerHTML = d.connections.map(c=>`<a href="${{c.link}}" target="_blank"><img src="${{c.src}}" class="ii"></a>`).join('');
                }} catch(e){{}}
            }}
            setInterval(r,1000); r();
        </script>
    </body></html>"""

# ===========================
#      CONTROLLERS
# ===========================
@app.route('/api/data/<key>')
def api(key): return jsonify(fetch_data(key, 'user', request.args, for_html=True))

@app.route('/superbadge/<key>')
def handler(key):
    args = request.args
    # 1. HTML
    if args.get('mode') == 'html': 
        d = fetch_data(key, 'user', args, for_html=True)
        return render_live_html(d)
        
    # 2. SVG
    mode = 'user' if (key.isdigit() and len(str(key))>15) else 'discord'
    data = fetch_data(key, mode, args, for_html=False)
    if not data: return Response('<svg><text>Error</text></svg>', mimetype="image/svg+xml")

    # Render
    bg_col = args.get('bg', '111111').replace('#','')
    svg = render_mega_svg(data, "", "40", bg_col)
    
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
